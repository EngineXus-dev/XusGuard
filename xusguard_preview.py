"""Read-only hosts preview and race-checked explicit apply for the desktop UI."""
from hashlib import sha256
from pathlib import Path

MAX_HOSTS_BYTES = 40 * 1024 * 1024


def build_preview(app, hosts_path, sources):
    """Combine already-downloaded, fresh lists; NEVER download or write hosts."""
    selected = [(key, item) for key, item in app.validate_sources_payload(sources).items()
                if item["enabled"]]
    if not selected:
        raise ValueError("No blocklist sources enabled. Choose and save a source first.")
    by_name = {}
    for _, item in selected:
        name = item["name"]
        if not app.is_source_cache_fresh(name):
            raise ValueError(f"{name}: missing or stale cache. Download enabled sources first.")
        path = app.get_source_file_path(name)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_HOSTS_BYTES:
            raise ValueError(f"{name}: invalid cached list")
        source_data = path.read_text(encoding="utf-8", errors="strict")
        entries = app.parse_hosts_file(source_data)
        if not entries:
            raise ValueError(f"{name}: downloaded list contains no valid domains")
        merged, _ = app.merge_hosts_entries([entries])
        by_name[name] = merged
    combined, _ = app.merge_hosts_entries(
        [[(ip, domain) for domain, ip in entries.items()]
         for entries in by_name.values()]
    )
    if not combined:
        raise ValueError("No valid domains to install")
    target = Path(hosts_path)
    if target.is_symlink() or not target.is_file():
        raise ValueError("The system hosts file is unavailable or is a symbolic link")
    old_bytes = target.read_bytes()
    try:
        old_content = old_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("Hosts file is not UTF-8. Preserve it and use the recovery workflow.") from exc
    managed = app.create_hosts_content_merged(
        combined, by_name, "# XusGuard - Blocked domains\n"
    )
    replacement = app.replace_managed_section(old_content, managed)
    if len(replacement.encode("utf-8")) > MAX_HOSTS_BYTES:
        raise ValueError("Merged hosts file exceeds 40 MiB safety limit")
    return {
        "hosts_path": str(target), "original_sha256": sha256(old_bytes).hexdigest(),
        "new_sha256": sha256(replacement.encode("utf-8")).hexdigest(),
        "sources": [source["name"] for _, source in selected],
        "domains": len(combined),
        "content": replacement,
    }


def apply_preview(app, preview, sources):
    """Refuse to write if sources or system hosts changed since user previewed."""
    rebuilt = build_preview(app, preview["hosts_path"], sources)
    for field in ("hosts_path", "original_sha256", "new_sha256", "sources", "domains"):
        if rebuilt[field] != preview[field]:
            raise ValueError("Sources or hosts file changed after preview; preview again.")
    return bool(app.install_hosts_file(preview["hosts_path"], rebuilt["content"]))
