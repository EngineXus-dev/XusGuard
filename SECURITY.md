# XusGuard Security Policy

**Maintainer:** EngineXus-dev. Version family: 2.x.

## Security boundaries

- XusGuard is a locally executed hosts-file editor, not an antivirus product.
- It must never download executable code from the original project or any other project at launch.
- Remote blocklist URLs must use verified HTTPS, with HTTPS-only redirects.
- Editing the OS hosts file must require a successful local backup.
- Replacement must be staged before replacing the target; failures must leave the original unchanged.
- Only the contents between XusGuard's explicit managed markers should be replaced.
- Do not run untrusted downloads or installers with elevated privileges.

## Known limitations

- The application still uses a sizeable legacy Python codebase and has not been formally audited.
- TLS does not guarantee that the content of a third-party blocklist is trustworthy.
- DNS configuration, endpoint protection, network policies or file ACLs may prevent installation.
- Legacy (pre-v2) entries without explicit managed markers cannot be safely identified automatically.
- Automated tests use temporary files and do not constitute full Windows/macOS/Linux end-to-end testing.
- Very old backups may be stored in the former checkout-local `hosts_backups/` folder.

## Reporting a vulnerability

Please use GitHub **Private vulnerability reporting** under the repository's Security tab if it is enabled. If private reporting is unavailable, contact the repository maintainer privately rather than publishing exploitable details.

Include the affected version, OS, minimal reproduction steps, and possible consequences. Avoid exposing secrets or private hosts-file contents. Do not submit vulnerability details in a public issue.

## License and provenance

This version is independently maintained under the MIT License. The original copyright notice in `LICENSE` is retained to satisfy MIT terms; it does not imply an operational dependency, endorsement, or a need to contact the original project.
