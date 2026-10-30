"""Recover XusGuard hosts backups without trusting arbitrary filesystem paths.

Only verified backup files under trusted backup directories are eligible. This
module does not edit /etc/hosts or the Windows hosts file by itself.
"""
from datetime import datetime
from hashlib import sha256
from pathlib import Path

MAX_BACKUP_BYTES = 40 * 1024 * 1024
SUFFIX = ".adblock_backup"


def _trusted_directory(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Backup directory is missing or is a symbolic link")
    return directory.resolve(strict=True)


def _valid_backup_name(hosts_path, name):
    basename = Path(hosts_path).name
    # Modern timestamped backup, or the old same-name backup next to hosts.
    if name == basename + SUFFIX:
        return True
    return (name.startswith(basename + "_") and name.endswith(SUFFIX)
            and len(name) > len(basename) + len(SUFFIX) + 1)


def _ensure_trusted(hosts_path, backup_path, allowed_dirs):
    target = Path(hosts_path)
    if target.is_symlink() or not target.is_file():
        raise ValueError("Target hosts file must be an existing, regular non-symlink file")
    path = Path(backup_path)
    if not _valid_backup_name(target, path.name):
        raise ValueError("Backup filename does not match the hosts target")
    if path.is_symlink() or not path.is_file():
        raise ValueError("Backup is not a regular file or is a symbolic link")
    resolved = path.resolve(strict=True)
    parents = {_trusted_directory(d) for d in allowed_dirs}
    if resolved.parent not in parents:
        raise ValueError("Backup is outside approved directories")
    return resolved


def inspect_backup(hosts_path, backup_path, allowed_dirs):
    """Return basic validation metadata and a SHA-256 of the exact bytes."""
    path = _ensure_trusted(hosts_path, backup_path, allowed_dirs)
    size = path.stat().st_size
    if size <= 0 or size > MAX_BACKUP_BYTES:
        raise ValueError("Backup is empty or exceeds the 40 MiB maximum")
    digest = sha256()
    with path.open("rb") as stream:
        while True:
            block = stream.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    if path.stat().st_size != size:
        raise ValueError("Backup changed during inspection")
    return {"path": str(path), "size": size, "sha256": digest.hexdigest(),
            "created": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")}


def list_backups(hosts_path, backup_dir, legacy_dir=None):
    """Find and inspect only backups for this hosts file, newest first."""
    dirs = [Path(backup_dir)]
    if legacy_dir is not None and Path(legacy_dir).is_dir() and not Path(legacy_dir).is_symlink():
        dirs.append(Path(legacy_dir))
    results = []
    for folder in dirs:
        try:
            _trusted_directory(folder)
        except (OSError, ValueError):
            continue
        for path in folder.glob("*" + SUFFIX):
            if not _valid_backup_name(hosts_path, path.name):
                continue
            try:
                results.append(inspect_backup(hosts_path, path, dirs))
            except (OSError, ValueError):
                continue
    return sorted(results, key=lambda item: item["created"], reverse=True)


def restore_backup(hosts_path, backup_path, allowed_dirs, expected_sha256, write_hosts):
    """Verify then restore exact backup bytes through the fail-closed hosts writer.

    A separate backup of the current hosts file must be created by write_hosts.
    Expected SHA-256 prevents a selected backup changing between preview and apply.
    """
    info = inspect_backup(hosts_path, backup_path, allowed_dirs)
    if not isinstance(expected_sha256, str) or info["sha256"] != expected_sha256:
        raise ValueError("Backup changed after preview or expected digest missing")
    source = Path(info["path"])
    payload = source.read_bytes()
    if len(payload) != info["size"] or sha256(payload).hexdigest() != expected_sha256:
        raise ValueError("Backup changed while reading; refusing restore")
    return bool(write_hosts(hosts_path, payload))
