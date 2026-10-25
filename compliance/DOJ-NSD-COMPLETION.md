# Sonoxo DOJ NSD Compliance Mapping Pipeline

## Scope

This pipeline continuously maps verified U.S. Department of Justice National Security Division (NSD) public enforcement and policy signals to Sonoxo repositories.

## Source-of-truth order

1. justice.gov/NSD and justice.gov/NSD-FARA
2. Controlling statutes, regulations, licenses, orders, and regulator publications
3. @DOJNatSec only as an alerting feed; material claims must be verified against an authoritative source before being treated as a compliance requirement

## Automated flow

```text
DOJ NSD source pages
  -> fetch + SHA-256 evidence
  -> extract current public actions/news
  -> classify domains
       export controls
       sanctions
       FARA / foreign influence
       CFIUS / foreign investment
       data security
       national-security cyber
       classified-information risk
  -> dynamically inventory public sonoxo/* repositories through GitHub API
  -> map repository name/description/topics to domains
  -> compute repository decision
       PASS   = no mapped intersection
       REVIEW = domain intersection; inspect actual activity
       HOLD   = transaction-specific facts indicate approval/license/registration may be required
       BLOCK  = verified prohibition or denied authorization
  -> JSON evidence artifact
  -> Markdown audit report
  -> GitHub Actions job summary
  -> 90-day artifact retention
```

## Important decision rule

Repository names, forks, public source code, simulations, or defense-adjacent terminology do not by themselves establish a legal violation or regulatory status. `HOLD` and `BLOCK` require facts about the actual transaction, user, counterparty, destination, data, technology classification, contract, authorization, or controlling legal restriction.

## Files

- `compliance/authoritative-sources.yaml`
- `compliance/repo-risk-map.json`
- `scripts/compliance_watch.py`
- `scripts/doj_nsd_repo_mapper.py`
- `tests/test_doj_nsd_repo_mapper.py`
- `.github/workflows/compliance-24h.yml`

## Operations

The workflow runs on relevant integration-branch changes, by manual dispatch, and daily after merge to the default branch if the workflow is retained there. Evidence is generated on every successful mapping run.
