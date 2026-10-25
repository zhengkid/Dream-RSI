#!/usr/bin/env python3
import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "compliance" / "repo-risk-map.json"
OUT_JSON = ROOT / "artifacts" / "doj-nsd-repo-map.json"
OUT_MD = ROOT / "artifacts" / "doj-nsd-repo-map.md"
OWNER = os.getenv("SONOXO_GITHUB_OWNER", "sonoxo")
TOKEN = os.getenv("GITHUB_TOKEN", "")

# Only action/news listings are allowed to produce repository review events.
# Policy/organization pages are retained as authoritative evidence/context, but
# their navigation links are deliberately excluded from the event stream.
DOJ_SOURCES = {
    "export_controls": {
        "url": "https://www.justice.gov/nsd/export-control-news",
        "extract_actions": True,
    },
    "data_security": {
        "url": "https://www.justice.gov/nsd/public-actions-0",
        "extract_actions": True,
    },
    "fara_foreign_influence": {
        "url": "https://www.justice.gov/nsd-fara",
        "extract_actions": False,
    },
    "nsd_structure": {
        "url": "https://www.justice.gov/nsd/national-security-division-organization-chart",
        "extract_actions": False,
    },
}

USER_AGENT = "SonoxoDOJNSDMapper/1.1 (+compliance evidence; contact repository owner)"
ACTION_PATH_RE = re.compile(r"/(?:opa|usao-[^/]+|nsd)/(?:pr|press-release)/", re.I)
ACTION_TITLE_TERMS = (
    "charged", "pleads", "pleaded", "pleads guilty", "sentenced", "convicted",
    "indict", "arrest", "settlement", "resolution", "declination", "enforcement",
    "penalty", "fine", "seizure", "forfeiture", "export", "sanction", "data security",
    "prohibited transaction", "covered transaction", "compliance order",
)


def request(url: str, accept: str = "text/html") -> tuple[bytes, str, int]:
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    if TOKEN and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {TOKEN}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read(), resp.geturl(), resp.status


def clean_text(raw: str) -> str:
    raw = re.sub(r"<script\b[^>]*>.*?</script>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<style\b[^>]*>.*?</style>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def is_action_record(absolute: str, title: str) -> bool:
    parsed = urllib.parse.urlparse(absolute)
    if parsed.netloc not in {"www.justice.gov", "justice.gov"}:
        return False
    # Exclude listing filters, search/navigation and the source index itself.
    if parsed.query or parsed.fragment:
        return False
    path = parsed.path.rstrip("/")
    if ACTION_PATH_RE.search(path + "/"):
        return True
    # DOJ Drupal press releases can occasionally live in component-specific paths.
    # Require both a meaningful enforcement/action term and a sufficiently deep path.
    title_l = title.lower()
    depth = len([segment for segment in path.split("/") if segment])
    return depth >= 3 and any(term in title_l for term in ACTION_TITLE_TERMS)


def extract_doj_items(source_name: str, url: str, body: bytes) -> list[dict]:
    text = body.decode("utf-8", errors="replace")
    items: list[dict] = []
    seen: set[str] = set()
    for href, label in re.findall(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text, flags=re.I | re.S):
        title = clean_text(label)
        if len(title) < 18:
            continue
        absolute = urllib.parse.urljoin(url, html.unescape(href))
        if not is_action_record(absolute, title):
            continue
        key = absolute.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        items.append({"source": source_name, "title": title[:500], "url": absolute})
    return items[:100]


def fetch_doj() -> tuple[list[dict], dict]:
    all_items: list[dict] = []
    evidence: dict = {}
    for name, spec in DOJ_SOURCES.items():
        url = spec["url"]
        try:
            body, final_url, status = request(url)
            digest = hashlib.sha256(body).hexdigest()
            extracted = extract_doj_items(name, final_url, body) if spec["extract_actions"] else []
            all_items.extend(extracted)
            evidence[name] = {
                "ok": 200 <= status < 400,
                "status": status,
                "source": url,
                "final_url": final_url,
                "sha256": digest,
                "bytes": len(body),
                "extract_actions": spec["extract_actions"],
                "items_extracted": len(extracted),
            }
        except Exception as exc:
            evidence[name] = {
                "ok": False,
                "source": url,
                "extract_actions": spec["extract_actions"],
                "error": str(exc),
            }
    dedup: dict[str, dict] = {}
    for item in all_items:
        dedup[item["url"].rstrip("/")] = item
    return list(dedup.values()), evidence


def list_repositories() -> list[dict]:
    repos: list[dict] = []
    page = 1
    while page <= 10:
        url = f"https://api.github.com/users/{urllib.parse.quote(OWNER)}/repos?per_page=100&page={page}&sort=updated"
        body, _, status = request(url, "application/vnd.github+json")
        if not (200 <= status < 300):
            raise RuntimeError(f"GitHub repo listing failed: HTTP {status}")
        chunk = json.loads(body.decode("utf-8"))
        if not isinstance(chunk, list):
            raise RuntimeError("Unexpected GitHub repository response")
        repos.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    return repos


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def classify_item(item: dict, config: dict) -> list[str]:
    haystack = f"{item.get('title','')} {item.get('url','')}".lower()
    matches = []
    for domain, rule in config["domains"].items():
        if any(term.lower() in haystack for term in rule.get("announcement_terms", [])):
            matches.append(domain)
    return matches


def repo_domains(repo: dict, config: dict) -> list[str]:
    haystack = " ".join([
        repo.get("name") or "",
        repo.get("description") or "",
        " ".join(repo.get("topics") or []),
    ]).lower()
    matched = []
    for domain, rule in config["domains"].items():
        if any(pattern.lower() in haystack for pattern in rule.get("repo_patterns", [])):
            matched.append(domain)
    return matched


def assess(repos: list[dict], items: list[dict], config: dict) -> list[dict]:
    classified_items = []
    for item in items:
        domains = classify_item(item, config)
        if domains:
            classified_items.append(item | {"domains": domains})

    results = []
    for repo in repos:
        domains = repo_domains(repo, config)
        relevant = []
        for item in classified_items:
            overlap = sorted(set(domains).intersection(item["domains"]))
            if overlap:
                relevant.append({
                    "title": item["title"],
                    "url": item["url"],
                    "source": item["source"],
                    "domains": overlap,
                })
        decision = config.get("matched_decision", "REVIEW") if relevant else config.get("default_decision", "PASS")
        severity = "high" if any("export_controls" in x["domains"] or "sanctions" in x["domains"] for x in relevant) else ("medium" if relevant else "none")
        results.append({
            "repository": repo.get("full_name", f"{OWNER}/{repo.get('name')}") ,
            "visibility": "private" if repo.get("private") else "public",
            "archived": bool(repo.get("archived")),
            "repo_domains": domains,
            "decision": decision,
            "severity": severity,
            "relevant_doj_items": relevant[:20],
            "note": (
                "Repository metadata intersects a verified DOJ public-action domain. Review actual transactions, users, counterparties, data, exports, and contracts before deciding legal applicability."
                if relevant else
                "No verified DOJ public-action domain intersection detected from current repository metadata."
            ),
        })
    return sorted(results, key=lambda x: ({"high": 0, "medium": 1, "none": 2}.get(x["severity"], 3), x["repository"].lower()))


def render_markdown(payload: dict) -> str:
    lines = [
        "# Sonoxo DOJ NSD Repository Compliance Map",
        "",
        f"Generated: {payload['checked_at']}",
        "",
        "This is a compliance triage map, not a legal certification. REVIEW means repository metadata intersects a verified DOJ public-action domain; HOLD/BLOCK require transaction-specific or verified-prohibition evidence.",
        "",
        "| Repository | Decision | Severity | Domains | DOJ actions |",
        "|---|---|---|---|---:|",
    ]
    for row in payload["repositories"]:
        domains = ", ".join(row["repo_domains"]) or "-"
        lines.append(f"| `{row['repository']}` | **{row['decision']}** | {row['severity']} | {domains} | {len(row['relevant_doj_items'])} |")
    lines.extend(["", "## Verified DOJ source evidence", ""])
    for name, ev in payload["source_evidence"].items():
        lines.append(f"- **{name}**: {'OK' if ev.get('ok') else 'FAILED'} — {ev.get('source')} — sha256 `{ev.get('sha256','n/a')}` — actions `{ev.get('items_extracted',0)}`")
    lines.extend([
        "", "## Decision semantics", "",
        "- **PASS** — no mapped intersection from current verified action evidence; not a blanket legal clearance.",
        "- **REVIEW** — verified DOJ action-domain overlap exists; inspect actual business activity and counterparties.",
        "- **HOLD** — use when transaction-specific facts indicate licensing/registration/approval may be required before proceeding.",
        "- **BLOCK** — use only when a verified prohibition or denied authorization applies.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    checked_at = datetime.now(timezone.utc).isoformat()
    config = load_config()
    try:
        items, source_evidence = fetch_doj()
        repos = list_repositories()
    except urllib.error.HTTPError as exc:
        print(f"fatal HTTP error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"fatal error: {exc}", file=sys.stderr)
        return 2

    assessed = assess(repos, items, config)
    summary = {
        "total_repositories": len(assessed),
        "pass": sum(1 for r in assessed if r["decision"] == "PASS"),
        "review": sum(1 for r in assessed if r["decision"] == "REVIEW"),
        "hold": sum(1 for r in assessed if r["decision"] == "HOLD"),
        "block": sum(1 for r in assessed if r["decision"] == "BLOCK"),
        "high_severity_reviews": sum(1 for r in assessed if r["decision"] == "REVIEW" and r["severity"] == "high"),
        "doj_actions_scanned": len(items),
    }
    payload = {
        "checked_at": checked_at,
        "owner": OWNER,
        "policy": "DOJ NSD verified-public-action repository triage",
        "summary": summary,
        "source_evidence": source_evidence,
        "repositories": assessed,
        "guardrails": {
            "x_feed_is_alert_only": True,
            "justice_gov_verification_required": True,
            "policy_pages_are_context_not_incidents": True,
            "hold_requires_transaction_context": True,
            "block_requires_verified_prohibition": True,
        },
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))

    action_sources = [ev for ev in source_evidence.values() if ev.get("extract_actions")]
    return 1 if action_sources and not any(ev.get("ok") for ev in action_sources) else 0


if __name__ == "__main__":
    sys.exit(main())
