# Uni-Adblock — Hosts Firewall

**Cross-platform, open-source hosts-file domain blocker** for Windows, Linux and macOS. Version shown in the application: 1.1.3.

Uni-Adblock downloads enabled third-party blocklists, merges domain entries, and updates the system hosts file. It provides an interactive CLI to manage lists, backups, restores, categories, and DNS flushing.

> **Security:** This software can change system-wide DNS resolution. Review the source and selected blocklists before granting administrator/root access. No third-party list can be guaranteed safe, accurate or uninterrupted.

## Safer installation

1. Download or clone **this** repository: `https://github.com/EngineXus-dev/Uni-Adblock`.
2. Inspect `uniadblock.py`, `sources.json`, and the installer for your OS.
3. Install Python 3 yourself if it is not installed. Do not run unknown `curl | bash` or remote PowerShell one-liners.
4. Extract the complete directory and run the local `install.bat` on Windows or `bash install.sh` on Linux/macOS. You can also run `python3 uniadblock.py` (or `py -3 uniadblock.py` on Windows).
5. Create and retain a backup of your existing hosts file **before** installing blocklists. Use the restore option if you need to undo changes.

Administrator/root privileges are required **only for actions that write the system hosts file**. Avoid running the entire program elevated when browsing the menus, managing lists, or inspecting results.

## How it works

- Downloads configured **HTTPS** blocklists with certificate validation; invalid certificates or HTTPS-to-HTTP redirects are rejected. Individual downloads are limited to 32 MiB.
- Parses and combines domains from enabled sources, and writes hosts-file entries.
- Supports timestamped backups, manual restore, DNS cache flush, source enable/disable, and custom domain redirection.
- `sources.json` contains third-party sources, many disabled by default. Enable only lists you understand and trust.

## Limitations and safety

- Hosts-file blocking cannot filter individual page elements and may not block first-party ads, encrypted DNS, or traffic bypassing the operating system resolver.
- Incorrect or compromised third-party lists can block legitimate services. HTTPS protects transport, **not** the source's intent or accuracy.
- Editing the system hosts file can affect connectivity for all users. Keep a verified, off-device backup. Review any custom redirect before applying it.
- This project is **not** an antivirus product, a DNS firewall, or a guarantee against tracking or malware.
- Current validation covers source-level checks; the application has not been certified or dynamically security audited.

## Development and security

Run the included security smoke tests with `python3 -m unittest discover -s tests -v`. The GitHub Actions workflow also runs compilation and tests without modifying the runner's hosts file.

Please report vulnerabilities privately via GitHub's security advisory reporting when enabled, or contact the repository maintainer privately. Do not publish exploit details before a fix is available.

## Credits and license

Original project attribution: **InfoSecREDD**. Current repository maintained by **EngineXus-dev**. See [LICENSE](LICENSE).
