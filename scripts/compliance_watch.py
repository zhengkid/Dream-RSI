#!/usr/bin/env python3
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCES = {
    "OFAC": {
        "url": "https://ofac.treasury.gov/sanctions-programs-and-country-information",
        "critical_group": "sanctions",
    },
    "BIS_EAR": {
        "url": "https://www.bis.gov/regulations/ear",
        "critical_group": "export_controls",
    },
    "DDTC_ITAR": {
        "url": "https://deccs.pmddtc.state.gov/deccs?id=ddtc_search&q=itar",
        "critical_group": "export_controls",
    },
    "DOJ_NSD_EXPORT": {
        "url": "https://www.justice.gov/nsd/export-control-and-sanctions",
        "critical_group": None,
    },
    "DOJ_NSD_FARA": {
        "url": "https://www.justice.gov/nsd-fara",
        "critical_group": None,
    },
    "DOJ_NSD_DATA_SECURITY": {
        "url": "https://www.justice.gov/nsd/data-security",
        "critical_group": None,
    },
    "DCSA_FOCI": {
        "url": "https://www.dcsa.mil/Industrial-Security/Entity-Vetting-Facility-Clearances-FOCI/",
        "critical_group": None,
    },
    "FAA_SPACE": {
        "url": "https://www.faa.gov/space/licenses/licensing_process",
        "critical_group": None,
    },
    "ITU_SPACE": {
        "url": "https://www.itu.int/ITU-R/go/space-e-submission/en",
        "critical_group": None,
    },
    "UNOOSA_SPACE_LAW": {
        "url": "https://www.unoosa.org/oosa/SpaceLaw/treaties.html",
        "critical_group": None,
    },
    "NIST_CSF": {
        "url": "https://www.nist.gov/cyberframework",
        "critical_group": None,
    },
    "CISA": {
        "url": "https://www.cisa.gov/news-events/cybersecurity-advisories",
        "critical_group": None,
    },
}

OUT = Path("artifacts/compliance-watch.json")


def fetch(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; SonoxoComplianceWatch/2.0; +https://github.com/sonoxo)",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            final_url = resp.geturl()
            parsed = urllib.parse.urlparse(final_url)
            auth_redirect = "auth.itu.int" in parsed.netloc or "logout" in parsed.path.lower()
            return {
                "ok": 200 <= resp.status < 400 and not auth_redirect,
                "status": resp.status,
                "final_url": final_url,
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
                "auth_redirect": auth_redirect,
            }
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status": None, "error": str(exc)}


def main() -> int:
    checked_at = datetime.now(timezone.utc).isoformat()
    results = {}
    for name, spec in SOURCES.items():
        result = fetch(spec["url"])
        result.update({"source": spec["url"], "critical_group": spec["critical_group"]})
        results[name] = result

    unavailable = sorted(name for name, result in results.items() if not result.get("ok"))

    groups = {}
    for name, result in results.items():
        group = result.get("critical_group")
        if group:
            groups.setdefault(group, []).append((name, bool(result.get("ok"))))

    blocking_groups = []
    for group, entries in groups.items():
        # A group blocks only if every independent controlling source in that group
        # is unavailable. A single website's anti-bot response is evidence degradation,
        # not evidence of noncompliance.
        if not any(ok for _, ok in entries):
            blocking_groups.append(group)

    degraded = bool(unavailable)
    blocked = bool(blocking_groups)
    payload = {
        "checked_at": checked_at,
        "policy": "authoritative-source-availability-and-change-evidence-v2",
        "results": results,
        "unavailable_sources": unavailable,
        "blocking_groups": sorted(blocking_groups),
        "status": "blocked" if blocked else ("degraded" if degraded else "ok"),
        "decision": "HOLD" if blocked else ("REVIEW" if degraded else "PASS"),
        "note": (
            "Source availability is operational evidence, not a compliance verdict. "
            "403/anti-bot responses are recorded as degraded access. The pipeline blocks "
            "only when every configured controlling source for a critical sanctions or "
            "export-control group is unavailable."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 2 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
