# XusGuard — Third-Party Feed Verification

**Snapshot:** October 30, 2026, 17:29 UTC. **Scope:** 16 currently bundled opt-in feeds.

This report records an actual read-only GitHub Actions verification using XusGuard's HTTPS downloader and hosts/domain parser. It does not install or modify the runner's hosts file. No source is activated by default.

**Result: 16 / 16 retrieved and parsed successfully.**

| Source ID | Feed | Unique domains parsed | Test result |
|---|---|---:|---|
| 2 | Steven Black Unified Hosts | 76,736 | Valid HTTPS/hosts format |
| 3 | AdAway Default | 6,540 | Valid HTTPS/hosts format |
| 4 | Someone Who Cares | 12,972 | Valid HTTPS/hosts format |
| 5 | Peter Lowe | 3,562 | Valid HTTPS/hosts format |
| 6 | Spam404 | 8,140 | Valid HTTPS/hosts format |
| 8 | Steven Black fakenews + gambling + porn | 162,089 | Valid HTTPS/hosts format |
| 9 | Goodbye Ads | 277,744 | Valid HTTPS/hosts format |
| 10 | 1Hosts Lite | 202,869 | Valid HTTPS/hosts format |
| 13 | Disconnect Tracking | 34 | Valid HTTPS/hosts format |
| 14 | Disconnect Ads | 2,700 | Valid HTTPS/hosts format |
| 15 | Steven Black social | 80,890 | Valid HTTPS/hosts format |
| 16 | Steven Black gambling | 83,825 | Valid HTTPS/hosts format |
| 17 | Steven Black porn | 153,191 | Valid HTTPS/hosts format |
| 18 | Steven Black fakenews | 79,301 | Valid HTTPS/hosts format |
| 19 | Phishing Army | 152,548 | Valid HTTPS/hosts format |
| 28 | Ultimate Hosts Blacklist | 153,775 | Valid HTTPS/hosts format |

[View the specific audit run](https://github.com/EngineXus-dev/XusGuard/actions/runs/41099173766) and its `xusguard-feed-audit` artifact. A fresh audit is also triggered by pushes to `main`; run `python scripts/verify_feeds.py --output feed-audit.json` locally for an on-demand, read-only check.

## What the audit verifies

- Connection over HTTPS with certificate validation, including HTTPS-only redirects
- Response fits within XusGuard's 32 MiB limit
- Content is not obvious HTML/XML or Adblock Plus-style rules
- At least 25 unique valid hosts-file or domain-list entries are parsed
- Reports entry count and errors per individual feed

## What it does not verify

- Whether any listed domain actually distributes malicious content or ads
- False-positive rates, completeness, threat freshness, malicious upstream changes
- Publisher identities, maintenance quality, provenance of every entry, or licensing conditions
- That combining feeds is safe (many overlap substantially)

**Caution:** The Disconnect Tracking source currently has only 34 parsed domains; its small size does not make it comprehensive. The Steven Black alternate feeds overlap with the base list. Opt into only the categories needed, and maintain backups before any changes.

## Removed or corrected feed presets

- **MVPS Hosts:** removed from defaults because the published file header indicates a last update in March 2021
- **1Hosts Pro:** removed because the configured Pro URL returned HTTP 404 and is no longer the documented publisher variant
- **1Hosts Lite:** switched to the official publisher GitHub hosts-file mirror
- **URLhaus old hostfile endpoint:** removed because it returned HTTP 410; current URLhaus community API requires an auth key
- **AdAway Extended:** removed as a duplicate of the same underlying AdAway hosts file
- Previously removed AdGuard rule syntax and IP-only feeds are not compatible with XusGuard's current hosts parser

See `sources.json` for the active, opt-in URL catalog. If an audit later reports a failure, investigate the feed before enabling it; never disable TLS verification to make a source pass.
