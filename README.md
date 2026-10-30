# 🛡️ XusGuard

**XusGuard v2.0.0**

A personal, cross-platform hosts-file blocker for **Windows, macOS, and Linux**. XusGuard helps block selected advertising and tracking domains using your computer's hosts file. No upstream project download, release lookup, or execution is required.

> **Security first:** XusGuard changes system-wide DNS behavior. Review the code and enabled blocklists before using administrator/root privileges. Blocklists are third-party data, not inherently trustworthy.

## What makes this edition different?

- **Local-only launchers:** `install.bat` and `install.sh` run the checked-out Python file. They never download and execute remote Python code or silently install packages.
- **Verified HTTPS:** external blocklists require valid TLS certificates, HTTPS redirects, and a 32 MiB per-download limit.
- **Strict hostnames:** invalid domains, IP redirections and malformed blocklist lines are discarded.
- **Fail-closed writes:** every hosts-file replacement requires a backup; writes are staged to a temporary file in the destination directory before replacement. If replacement is blocked, XusGuard reports an error instead of truncating the original.
- **Explicit ownership:** new managed records sit between `# BEGIN XUSGUARD MANAGED` and `# END XUSGUARD MANAGED`. Other entries are preserved.
- **Opt-in lists:** all sources are disabled until you choose one. Cached lists and backups are kept outside the repository.
- **Safe cleanup:** non-interactive cleanup cannot delete backups or preferences.

## Installation

Requires **Python 3.10+** and an internet connection **only if you download a blocklist**. XusGuard does not auto-install Python, `pip`, or dependencies.

1. [Download this repository as a ZIP](https://github.com/EngineXus-dev/XusGuard/archive/refs/heads/main.zip), or clone it from your own repository. Extract the entire folder.
2. Read `sources.json`, `xusguard.py`, and the launcher for your OS.
3. Run **`install.bat`** in Windows or **`bash install.sh`** in Linux/macOS. To run directly: `py -3 xusguard.py` (Windows) or `python3 xusguard.py` (Linux/macOS).
4. First use **Backup current hosts file**. Then enable **one reputable HTTPS blocklist**, download/update, inspect the result, and confirm installation.
5. Elevate **only when changing the system hosts file**. If replacement is blocked by your OS security settings, XusGuard fails rather than weakening protections.

Do **not** paste a `curl | bash` or downloaded-code PowerShell one-liner into an elevated shell.

## What it does

The text menu lets you select/download third-party lists, merge and deduplicate domains, see statistics, inspect the hosts file, back it up, restore it, flush the DNS cache, choose service categories, and add or remove marked domain redirects.

### Backups and recovery

Every safe write saves a private timestamped backup:

- Windows: `%LOCALAPPDATA%\XusGuard\hosts_backups` (or the current user's home folder if LOCALAPPDATA is absent)
- Linux/macOS: `~/.local/share/xusguard/hosts_backups`

Downloaded lists are cached next to the backups under `hosts_sources`. **If launched as Administrator/root, the effective account may have a different backup directory.** Keep a separate backup outside this tool as well.

The restore menu also looks for older backups in the repository's former `hosts_backups` folder. Restoring a default hosts template removes custom mappings; prefer restoring your own verified backup.

**Migration warning:** Entries previously added by older, unmarked releases are not automatically identified or deleted. XusGuard deliberately avoids guessing which entries it owns. Restore a known-good pre-installation hosts backup or manually review older entries before your first v2 installation.

### Important limitations

- Hosts-file blocking cannot reliably filter page elements, first-party advertising, or DNS traffic that bypasses the OS resolver.
- Blocking selected services can disrupt logins, software updates, and websites.
- HTTPS validates the transport, **not** that a third-party list is benign.
- Atomic replacements can be denied by Windows file protection, antivirus, or system ACLs. A failed replacement is **not** a successful install.
- The Python source is still a large legacy application; automated tests do not replace a full multi-platform security audit.
- XusGuard is not antivirus, a malware guarantee, or an enterprise DNS firewall.

## Tests

Run the **offline** regression suite (never touches the real hosts file):

```bash
python3 -m unittest discover -s tests -v
```

GitHub Actions runs syntax checks and tests against Python 3.10, 3.12 and 3.13. Tests exercise malicious domain inputs, managed-block preservation, backup failures, atomic write errors, marked redirects and upstream URL checks.

## Security and license

Read [SECURITY.md](SECURITY.md) for vulnerability reporting and security boundaries. The source is published under the [MIT License](LICENSE). Its legally required original copyright notice remains in `LICENSE`; this independent edition does not need or contact the upstream repository at runtime.

**Maintained and customized by EngineXus-dev.**
