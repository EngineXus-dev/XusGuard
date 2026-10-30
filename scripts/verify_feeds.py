#!/usr/bin/env python3
"""Read-only HTTPS audit of each opt-in source; does not access the OS hosts file."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import xusguard as app  # noqa: E402

MINIMUM_DOMAINS = 25


def verify_one(source_id, source):
    name = source["name"]
    url = source["url"]
    result = {
        "id": source_id, "name": name, "url": url,
        "status": "unknown", "unique_domains": 0,
        "bytes": 0, "detail": "",
    }
    try:
        body = app.download_hosts_file(url, timeout=12)
        if body is None:
            result["status"] = "unreachable_or_rejected"
            result["detail"] = "Download failed, timed out, TLS rejected or size limit exceeded"
            return result
        result["bytes"] = len(body.encode("utf-8"))
        cleaned = body.lstrip().lower()
        noncomments = next(
            (line.strip() for line in body.splitlines()
             if line.strip() and not line.lstrip().startswith("#")), ""
        ).lower()
        if (cleaned.startswith(("<html", "<!doctype html", "<?xml"))
                or noncomments.startswith(("[adblock", "||", "@@"))):
            result["status"] = "unsupported_format"
            result["detail"] = "HTML/XML or adblock-rule syntax detected"
            return result
        entries = app.parse_hosts_file(body)
        result["unique_domains"] = len({hostname for _, hostname in entries})
        if result["unique_domains"] < MINIMUM_DOMAINS:
            result["status"] = "too_few_domains"
            result["detail"] = "Insufficient valid hosts/domain entries"
        else:
            result["status"] = "valid_format"
            result["detail"] = "HTTPS download, domain parsing and size checks passed"
    except Exception as exc:
        result["status"] = "audit_error"
        result["detail"] = f"{type(exc).__name__}: {str(exc)[:120]}"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="feed-audit.json")
    args = parser.parse_args()
    sources = app.validate_sources_payload(json.loads(
        (ROOT / "sources.json").read_text(encoding="utf-8")
    ))
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(verify_one, source_id, source): source_id
            for source_id, source in sources.items()
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda x: int(x["id"]))
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Read-only feed availability and basic hosts-format validation",
        "note": "Valid format does NOT prove a list is safe, current, accurate or license-compatible.",
        "results": results
    }
    output = Path(args.output)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("\nFEED AUDIT RESULTS")
    for row in results:
        print(f"ID {row['id']:>2} {row['status']:<24} {row['unique_domains']:>8}  {row['name']}")
    passed = sum(row["status"] == "valid_format" for row in results)
    print(f"Validated {passed}/{len(results)} bundled feeds. Report: {output}")
    # External outages or incompatible feeds are warnings; do not break offline CI.
    # Results are surfaced in artifacts and should inform maintenance decisions.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
