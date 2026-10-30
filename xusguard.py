#!/usr/bin/env python3
"""
XusGuard - Cross-platform ad blocker using hosts files
Supports macOS, Linux, and Windows

Created by: EngineXus-dev
"""

import os
import sys
import platform
import subprocess
import urllib.request
import urllib.error
import shutil
import ssl
import json
import re
import socket
import time
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import ipaddress
import hashlib
import secrets
import stat

# Avoid exceptions when classic Windows consoles cannot encode Unicode UI symbols.
# Preserve the configured output encoding; replace only unrepresentable glyphs.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors='replace')
    except (AttributeError, OSError, ValueError):
        pass

if sys.version_info < (3, 10):
    raise SystemExit("XusGuard requires Python 3.10 or newer")

VERSION = "2.1.0"




HOSTS_FILE_LOCATIONS = {
    'Darwin': '/etc/hosts',
    'Linux': '/etc/hosts',
    'Windows': r'C:\Windows\System32\drivers\etc\hosts'
}

BACKUP_SUFFIX = '.adblock_backup'
DEFAULT_BACKUP_DIR = 'hosts_backups'
SOURCES_DIR = 'hosts_sources'
SOURCES_JSON_FILE = 'sources.json'


def safe_comment(value):
    """Prevent configured source names from injecting hosts-file lines."""
    return re.sub(r'[\x00-\x1f\x7f]', ' ', str(value))[:160]


def get_source_file_path(source_name):
    """Unique, deterministic cache file; names cannot collide after sanitizing."""
    source_bytes = source_name.encode('utf-8')
    suffix = hashlib.sha256(source_bytes).hexdigest()[:16]
    filename = f"{sanitize_filename(source_name)[:80]}_{suffix}.hosts"
    return get_sources_directory() / filename


def validate_sources_payload(sources):
    """Validate configuration without contacting any configured URL."""
    from urllib.parse import urlsplit
    if not isinstance(sources, dict):
        raise ValueError("sources.json must contain an object")
    normalized = {}
    seen_names = set()
    for key, source in sources.items():
        if (not isinstance(key, str) or not key.isdigit()
                or not isinstance(source, dict)):
            raise ValueError("Malformed source identifier or record")
        name = source.get('name')
        url = source.get('url')
        if (not isinstance(name, str) or not name or len(name) > 100
                or safe_comment(name) != name):
            raise ValueError(f"Invalid source name at {key}")
        try:
            name.encode('utf-8')
        except UnicodeError as exc:
            raise ValueError(f"Invalid Unicode source name at {key}") from exc
        if name.casefold() in seen_names:
            raise ValueError(f"Duplicate source name at {key}; cache names must be unique")
        seen_names.add(name.casefold())
        if not isinstance(url, str) or len(url) > 2048 or any(c.isspace() for c in url):
            raise ValueError(f"Invalid source URL at {key}")
        parts = urlsplit(url)
        if (parts.scheme != 'https' or not parts.hostname or
                parts.username is not None or parts.password is not None
                or parts.fragment):
            raise ValueError(f"Source {key} must use HTTPS without credentials/fragments")
        if 'enabled' in source and not isinstance(source['enabled'], bool):
            raise ValueError(f"Source {key} has a non-boolean enabled flag")
        record = dict(source)
        record.setdefault('enabled', False)
        normalized[key] = record
    return normalized


def get_sources_json_path():
    return Path(__file__).resolve().parent / SOURCES_JSON_FILE


def load_sources():
    """Invalid configuration remains untouched; refuse unsafe auto-recovery."""
    path = get_sources_json_path()
    if not path.exists():
        print_warning("No sources.json found. Extract the complete repository.")
        return {}
    try:
        if path.is_symlink():
            raise OSError("Refusing symlinked sources.json")
        with path.open('r', encoding='utf-8') as file:
            return validate_sources_payload(json.load(file))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print_error(f"sources.json could not be read: {exc}")
        print_warning("Original configuration preserved; repair it before enabling sources.")
        return {}


def save_sources(sources):
    """Never overwrite an unreadable, malformed, or symlinked configuration."""
    temp_path = None
    path = get_sources_json_path()
    try:
        validated = validate_sources_payload(sources)
        if path.is_symlink():
            raise OSError("Refusing symlinked sources.json")
        if path.exists():
            with path.open('r', encoding='utf-8') as file:
                validate_sources_payload(json.load(file))
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', dir=path.parent,
            prefix='.xusguard-sources-', delete=False
        ) as temp:
            temp_path = Path(temp.name)
            json.dump(validated, temp, indent=2, ensure_ascii=False)
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temp_path, path)
        temp_path = None
        return True
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print_error(f"Failed to save sources.json; original preserved: {exc}")
        return False
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


HOSTS_SOURCES = {}  # Populate only after startup; importing must not read files or perform I/O.


def get_default_hosts_content():
    """Get the default hosts file content for the current OS"""
    system = platform.system()
    
    if system == 'Windows':
        return """

127.0.0.1       localhost
::1             localhost
"""
    else:
        return """
127.0.0.1	localhost
255.255.255.255	broadcasthost
::1             localhost
"""


class Colors:
    """ANSI color codes for terminal output (MUD-style colors)"""
    ENDC = '\033[0m'
    RESET = '\033[0m'
    
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    HEADER = BRIGHT_MAGENTA
    OKBLUE = BRIGHT_BLUE
    OKCYAN = BRIGHT_CYAN
    OKGREEN = BRIGHT_GREEN
    WARNING = BRIGHT_YELLOW
    FAIL = BRIGHT_RED


def clear_screen():
    """Clear the screen (cross-platform)"""
    print('\x1b[2J\x1b[H', end='')


def strip_ansi_codes(text):
    """Remove ANSI color codes from text"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def print_boxed_menu(lines, width=70):
    """Print content inside a styled box (MUD-style colors)"""
    top_left = '╔'
    top_right = '╗'
    bottom_left = '╚'
    bottom_right = '╝'
    horizontal = '═'
    vertical = '║'
    
    content_width = width - 2
    
    print(f"{Colors.BRIGHT_CYAN}{top_left}{horizontal * (width - 2)}{top_right}{Colors.ENDC}")
    
    for line in lines:
        visual_length = len(strip_ansi_codes(line))
        
        padding = content_width - visual_length
        if padding > 0:
            padded_line = line + ' ' * padding
        else:
            padded_line = line
        
        print(f"{Colors.BRIGHT_CYAN}{vertical}{Colors.ENDC}{padded_line}{Colors.BRIGHT_CYAN}{vertical}{Colors.ENDC}")
    
    print(f"{Colors.BRIGHT_CYAN}{bottom_left}{horizontal * (width - 2)}{bottom_right}{Colors.ENDC}")


def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def check_root():
    """Check if running with administrator/root privileges"""
    if platform.system() == 'Windows':
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0


def get_hosts_file_path():
    """Get the system hosts file path based on OS"""
    system = platform.system()
    return HOSTS_FILE_LOCATIONS.get(system, '/etc/hosts')


def download_hosts_file(url, timeout=60):
    """Download a blocklist over verified HTTPS only.

    Never downgrade certificate verification or accept untrusted redirects.
    """
    from urllib.parse import urlsplit

    if urlsplit(url).scheme.lower() != 'https':
        print_error(f"Refusing non-HTTPS blocklist source: {url}")
        return None

    class HTTPSOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            if urlsplit(newurl).scheme.lower() != 'https':
                raise urllib.error.URLError("Refusing redirect to non-HTTPS URL")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    try:
        print_info(f"Downloading from {url}...")
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl.create_default_context()),
            HTTPSOnlyRedirectHandler(),
        )
        req = urllib.request.Request(url, headers={'User-Agent': 'XusGuard/2.0'})
        with opener.open(req, timeout=timeout) as response:
            if urlsplit(response.geturl()).scheme.lower() != 'https':
                raise urllib.error.URLError("Non-HTTPS response rejected")
            # Bound memory consumption when processing third-party lists.
            max_bytes = 32 * 1024 * 1024
            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise ValueError("Blocklist exceeds 32 MiB download limit")
            return data.decode('utf-8', errors='replace')
    except (urllib.error.URLError, ValueError, TimeoutError, OSError) as e:
        print_error(f"Failed to download verified blocklist from {url}: {e}")
        return None


def normalize_domain(domain):
    """Return a strict ASCII DNS hostname or None; never accept hosts-file syntax."""
    if not isinstance(domain, str) or not domain or domain.strip() != domain:
        return None
    if domain.endswith('.') or '..' in domain or '/' in domain:
        return None
    try:
        ascii_domain = domain.encode('idna').decode('ascii').lower()
    except (UnicodeError, UnicodeEncodeError):
        return None
    if len(ascii_domain) > 253 or '.' not in ascii_domain:
        return None
    if ascii_domain.endswith(('.localhost', '.local', '.home.arpa', '.internal')):
        return None
    try:
        ipaddress.ip_address(ascii_domain)
        return None
    except ValueError:
        pass
    for label in ascii_domain.split('.'):
        if not 1 <= len(label) <= 63 or not re.fullmatch(r'[a-z0-9]+(?:[a-z0-9-]*[a-z0-9])?', label):
            return None
    return ascii_domain


def parse_hosts_file(content):
    """Parse only valid domain-only lists and sinkhole hosts mappings.

    Ignore invalid hostnames and arbitrary IP redirects supplied by blocklists.
    """
    entries = []
    for line in content.splitlines():
        body = line.split('#', 1)[0].strip()
        if not body:
            continue
        parts = body.split()
        if len(parts) >= 2 and parts[0] in ('0.0.0.0', '127.0.0.1'):
            candidates = parts[1:]
            ip = parts[0]
        elif len(parts) == 1:
            candidates = parts
            ip = '0.0.0.0'
        else:
            continue
        for candidate in candidates:
            domain = normalize_domain(candidate)
            if domain:
                entries.append((ip, domain))
            if len(entries) > 1000000:
                print_error("Blocklist exceeds 1,000,000 entries; rejecting it")
                return []
    return entries


def merge_hosts_entries(entries_list):
    """Merge multiple hosts entry lists and deduplicate"""
    merged = {}
    total_entries = 0
    
    for entries in entries_list:
        for ip, hostname in entries:
            hostname_lower = hostname.lower()
            if hostname_lower not in merged:
                merged[hostname_lower] = ip
                total_entries += 1
            elif merged[hostname_lower] == '127.0.0.1' and ip == '0.0.0.0':
                merged[hostname_lower] = ip
    
    return merged, total_entries


def create_hosts_content_merged(merged_entries, source_entries_dict, header_comment):
    """Create hosts file content with deduplicated entries from all sources"""
    lines = [header_comment]
    lines.append(f"# Generated by XusGuard on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"# Total unique blocked domains: {len(merged_entries)}")
    lines.append(f"# Sources: {safe_comment(', '.join(sorted(source_entries_dict.keys())))}")
    lines.append("#")
    
    for hostname in sorted(merged_entries.keys()):
        lines.append(f"{merged_entries[hostname]}\t{hostname}")
    
    return '\n'.join(lines) + '\n'


def get_backup_directory():
    """Store backups outside the checkout in a private per-user directory."""
    if platform.system() == 'Windows':
        base = Path(os.environ.get('LOCALAPPDATA') or Path.home())
        backup_dir = base / 'XusGuard' / 'hosts_backups'
    else:
        backup_dir = Path.home() / '.local' / 'share' / 'xusguard' / 'hosts_backups'
    if backup_dir.is_symlink():
        raise OSError("Backup directory must not be a symbolic link")
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if backup_dir.is_symlink():
        raise OSError("Backup directory must not be a symbolic link")
    if os.name != 'nt':
        backup_dir.chmod(0o700)
    return backup_dir


def get_sources_directory():
    """Keep downloaded cache away from the repository checkout."""
    sources_dir = get_backup_directory().parent / SOURCES_DIR
    if sources_dir.is_symlink():
        raise OSError("Sources cache directory must not be a symlink")
    sources_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if sources_dir.is_symlink():
        raise OSError("Sources cache directory must not be a symlink")
    if os.name != 'nt':
        sources_dir.chmod(0o700)
    return sources_dir


def sanitize_filename(name):
    """Sanitize a source name to create a valid filename (summary name with no spaces)"""
    filename = name.lower()
    invalid_chars = '<>:"/\\|?* .'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    while '__' in filename:
        filename = filename.replace('__', '_')
    filename = filename.strip('_')
    filename = ''.join(c if c.isalnum() or c == '_' else '_' for c in filename)
    if len(filename) > 100:
        filename = filename[:100]
    return filename


def save_source_file(source_id, source_name, entries):
    """Atomically cache downloaded entries; never overwrite a symlink target."""
    temp_path = None
    try:
        file_path = get_source_file_path(source_name)
        if file_path.is_symlink():
            raise OSError("Refusing a symlinked blocklist cache")
        lines = [
            f"# Source: {safe_comment(source_name)}",
            f"# Generated by XusGuard on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Total domains: {len(entries)}", "#", ""
        ]
        for hostname, ip in sorted(entries.items()):
            checked = normalize_domain(hostname)
            if checked is None or ip not in ('0.0.0.0', '127.0.0.1'):
                raise ValueError("Invalid cached blocklist entry")
            lines.append(f"{ip}\t{checked}")
        content = '\n'.join(lines) + '\n'
        with tempfile.NamedTemporaryFile(
            mode='w', dir=file_path.parent, prefix='.xusguard-list-',
            suffix='.tmp', encoding='utf-8', delete=False
        ) as temp:
            temp_path = Path(temp.name)
            temp.write(content)
            temp.flush()
            os.fsync(temp.fileno())
        os.replace(temp_path, file_path)
        temp_path = None
        return str(file_path)
    except (OSError, ValueError) as exc:
        print_error(f"Failed to safely cache source {safe_comment(source_name)}: {exc}")
        return None
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def is_source_cached(source_name):
    path = get_source_file_path(source_name)
    return (not path.is_symlink() and path.is_file()
            and 0 < path.stat().st_size <= 40 * 1024 * 1024)


def is_source_cache_fresh(source_name, max_age_days=7):
    """A cache from the future is never considered fresh."""
    if not is_source_cached(source_name):
        return False
    path = get_source_file_path(source_name)
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return timedelta(0) <= age < timedelta(days=max_age_days)


def read_source_name_from_file(file_path):
    """Extract source name from a saved hosts file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith('# Source:'):
                return first_line.replace('# Source:', '').strip()
    except Exception:
        pass
    return Path(file_path).stem.replace('_', ' ')


def backup_hosts_file(hosts_path, use_timestamp=True):
    """Create a durable, verified copy; incomplete backups are always removed."""
    backup_path = None
    try:
        target = Path(hosts_path)
        if target.is_symlink() or not target.is_file():
            raise OSError("Hosts file is missing, not regular, or a symbolic link")
        before = target.stat()
        if not 0 < before.st_size <= 40 * 1024 * 1024:
            raise ValueError("Hosts file must be between 1 byte and 40 MiB")
        backup_dir = get_backup_directory()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backup_path = backup_dir / (
            f"{target.name}_{timestamp}_{secrets.token_hex(4)}{BACKUP_SUFFIX}"
        )
        import hashlib
        source_digest = hashlib.sha256()
        copied = 0
        with target.open('rb') as src, backup_path.open('xb') as dst:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                copied += len(chunk)
                if copied > 40 * 1024 * 1024:
                    raise ValueError("Backup exceeds the maximum allowed size")
                source_digest.update(chunk)
                dst.write(chunk)
            dst.flush()
            os.fsync(dst.fileno())
        if os.name != 'nt':
            backup_path.chmod(0o600)
        after = target.stat()
        if (copied != before.st_size or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns):
            raise OSError("Hosts file changed during backup")
        verify_digest = hashlib.sha256()
        with backup_path.open('rb') as verify:
            while True:
                chunk = verify.read(1024 * 1024)
                if not chunk:
                    break
                verify_digest.update(chunk)
        if backup_path.stat().st_size != copied or verify_digest.digest() != source_digest.digest():
            raise OSError("Backup integrity verification failed")
        print_success(f"Verified backup created: {backup_path}")
        return True
    except (OSError, ValueError) as exc:
        if backup_path is not None:
            try:
                backup_path.unlink(missing_ok=True)
            except OSError:
                pass
        print_error(f"Backup failed; refusing to modify hosts file: {exc}")
        return False


def save_default_hosts_file():
    """Save the default OS hosts file template"""
    backup_dir = get_backup_directory()
    system = platform.system()
    default_filename = f"default_hosts_{system.lower()}.txt"
    default_path = backup_dir / default_filename
    
    try:
        default_content = get_default_hosts_content()
        with open(default_path, 'w', encoding='utf-8') as f:
            f.write(default_content)
        print_success(f"Default hosts file saved: {default_path}")
        return str(default_path)
    except Exception as e:
        print_error(f"Failed to save default hosts file: {e}")
        return None


def restore_from_default_hosts(hosts_path):
    """Restore hosts file from OS default template"""
    backup_dir = get_backup_directory()
    system = platform.system()
    default_filename = f"default_hosts_{system.lower()}.txt"
    default_path = backup_dir / default_filename
    
    if not default_path.exists():
        print_info("Default hosts file not found, creating from template...")
        save_default_hosts_file()
    
    if not default_path.exists():
        print_error("Failed to create default hosts file")
        return False
    
    try:
        if not install_hosts_file(hosts_path, default_path.read_text(encoding='utf-8')):
            return False
        print_success(f"Hosts file restored from OS default: {default_path}")
        return True
    except Exception as e:
        print_error(f"Failed to restore from default: {e}")
        return False


def get_available_backups(hosts_path):
    """List only verified backups matching the current hosts-file basename."""
    from xusguard_recovery import list_backups
    legacy = Path(__file__).resolve().parent / DEFAULT_BACKUP_DIR
    legacy = legacy if legacy.is_dir() and not legacy.is_symlink() else None
    return list_backups(hosts_path, get_backup_directory(), legacy)


def recover_selected_backup(hosts_path, selected_path, expected_sha256):
    """Validate user-selected backup and restore exact bytes with a new safety backup."""
    from xusguard_recovery import restore_backup
    primary = get_backup_directory()
    legacy = Path(__file__).resolve().parent / DEFAULT_BACKUP_DIR
    allowed = [primary]
    if legacy.is_dir() and not legacy.is_symlink():
        allowed.append(legacy)
    try:
        return restore_backup(hosts_path, selected_path, allowed,
                              expected_sha256, install_hosts_file)
    except (ValueError, OSError) as exc:
        print_error(f"Recovery refused: {exc}")
        return False


def restore_hosts_file(hosts_path):
    """Interactive restore using verified backups and explicit SHA-256 consent."""
    records = get_available_backups(hosts_path)
    if not records:
        print_warning("No valid backups found for this hosts file")
        return False
    clear_screen()
    print_boxed_menu(["XusGuard - Safe Recovery",
                      "A new backup of the current hosts file is mandatory.",
                      "0. Cancel"] +
                     [f"{i}. {r['created']} ({r['size']:,} bytes) - {Path(r['path']).name}"
                      for i, r in enumerate(records, 1)], width=90)
    try:
        index = int(safe_input("Backup number (0 to cancel): ").strip())
        if index == 0:
            return False
        if index < 1 or index > len(records):
            print_error("Invalid backup number")
            return False
    except ValueError:
        return False
    selected = records[index - 1]
    print_info(f"Selected SHA-256: {selected['sha256']}")
    if safe_input("Restore exact backup bytes? Type RESTORE to confirm: ").strip() != "RESTORE":
        print_info("Recovery cancelled")
        return False
    if recover_selected_backup(hosts_path, selected["path"], selected["sha256"]):
        print_success("Hosts file recovered from verified backup")
        return True
    return False


MANAGED_START = '# BEGIN XUSGUARD MANAGED'
MANAGED_END = '# END XUSGUARD MANAGED'


def split_managed_section(content):
    """Return content excluding our section and the previous managed body."""
    lines = content.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.strip() == MANAGED_START]
    ends = [i for i, line in enumerate(lines) if line.strip() == MANAGED_END]
    if not starts and not ends:
        return content, ''
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        raise ValueError("Malformed XusGuard markers; refusing to rewrite hosts file")
    before = ''.join(lines[:starts[0]])
    managed = ''.join(lines[starts[0] + 1:ends[0]])
    after = ''.join(lines[ends[0] + 1:])
    return before + after, managed


def replace_managed_section(content, managed_body):
    """Update only our explicitly bounded section; preserve all other entries."""
    base, _ = split_managed_section(content)
    if not isinstance(managed_body, str):
        raise ValueError("Managed hosts content must be text")
    return (base.rstrip('\r\n') + '\n\n' + MANAGED_START + '\n' +
            managed_body.strip('\r\n') + '\n' + MANAGED_END + '\n')


def replace_preserving_metadata(temp_path, target):
    """Use Win32 ReplaceFileW to preserve Windows file ACLs; POSIX uses rename."""
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        replace_file = kernel32.ReplaceFileW
        replace_file.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p,
                                 ctypes.c_wchar_p, wintypes.DWORD,
                                 ctypes.c_void_p, ctypes.c_void_p]
        replace_file.restype = wintypes.BOOL
        if not replace_file(str(target), str(temp_path), None, 0, None, None):
            error = ctypes.get_last_error()
            raise OSError(error, f"Windows ReplaceFileW failed: {error}")
    else:
        os.replace(temp_path, target)


def install_hosts_file(hosts_path, content):
    """Back up then stage the full write before replacing the hosts file."""
    temp_path = None
    try:
        target = Path(hosts_path)
        if target.is_symlink() or not target.is_file():
            raise OSError("Refusing to change a missing, non-regular or symlink hosts file")
        if isinstance(content, str):
            payload = content.encode('utf-8')
        elif isinstance(content, bytes):
            payload = content
        else:
            raise ValueError("Hosts file content must be UTF-8 text or exact backup bytes")
        if b'\x00' in payload or len(payload) == 0 or len(payload) > 40 * 1024 * 1024:
            raise ValueError("Invalid hosts file contents or larger than 40 MiB")
        if not backup_hosts_file(str(target)):
            return False
        old_stat = target.stat()
        with tempfile.NamedTemporaryFile(
            mode='wb', prefix='.xusguard-', suffix='.tmp',
            dir=str(target.parent), delete=False
        ) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(payload)
            tmp.flush()
            os.fsync(tmp.fileno())
        shutil.copystat(target, temp_path)
        if os.name != 'nt' and hasattr(os, 'chown'):
            os.chown(temp_path, old_stat.st_uid, old_stat.st_gid)
            os.chmod(temp_path, stat.S_IMODE(old_stat.st_mode))
        # Refuse unsafe in-place fallback if Windows or antivirus blocks replacement.
        replace_preserving_metadata(temp_path, target)
        temp_path = None
        print_success(f"Hosts file updated: {target}")
        return True
    except Exception as exc:
        print_error(f"Safe hosts-file replacement failed: {exc}")
        return False
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def get_stats():
    """Get statistics about blocked domains and sources"""
    stats = {
        'domains_to_be_blocked': 0,
        'current_blocked_domains': 0,
        'blocked_services': 0,
        'enabled_sources': 0,
        'total_sources': len(HOSTS_SOURCES),
        'cached_sources': 0
    }
    
    stats['enabled_sources'] = sum(1 for source in HOSTS_SOURCES.values() if source.get('enabled', False))
    
    sources_dir = get_sources_directory()
    if sources_dir.exists():
        stats['cached_sources'] = len(list(sources_dir.glob('*.hosts')))
    
    if stats['enabled_sources'] > 0 and sources_dir.exists():
        try:
            all_entries_list = []
            enabled_source_names = {source['name'] for source in HOSTS_SOURCES.values() if source.get('enabled', False)}
            
            for source_file in sources_dir.glob('*.hosts'):
                try:
                    with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        source_name = read_source_name_from_file(str(source_file))
                        
                        if source_name in enabled_source_names:
                            entries = parse_hosts_file(content)
                            if entries:
                                all_entries_list.append(entries)
                except Exception:
                    pass
            
            if all_entries_list:
                merged_all, _ = merge_hosts_entries(all_entries_list)
                stats['domains_to_be_blocked'] = len(merged_all)
        except Exception:
            pass
    
    hosts_path = get_hosts_file_path()
    blocked_domains_set = set()
    if os.path.exists(hosts_path):
        try:
            with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                in_adblock_section = False
                for line in content.split('\n'):
                    line = line.strip()
                    if '# XusGuard' in line:
                        in_adblock_section = True
                    elif line and not line.startswith('#') and in_adblock_section:
                        parts = line.split()
                        if len(parts) >= 2 and parts[0] in ['127.0.0.1', '0.0.0.0']:
                            for hostname in parts[1:]:
                                hostname = hostname.strip()
                                if hostname and not hostname.startswith('#'):
                                    blocked_domains_set.add(hostname.lower())
                stats['current_blocked_domains'] = len(blocked_domains_set)
        except Exception:
            pass
    
    stats['blocked_services'] = 0
    if blocked_domains_set:
        try:
            services = get_individual_services()
            blocked_services_count = 0
            for service_key, service in services.items():
                service_domains = service.get('domains', [])
                if service_domains:
                    for domain in service_domains:
                        if domain.lower() in blocked_domains_set:
                            blocked_services_count += 1
                            break
            stats['blocked_services'] = blocked_services_count
        except Exception:
            pass
    
    return stats


def show_menu():
    """Display the main menu"""
    clear_screen()
    stats = get_stats()
    
    menu_lines = []
    
    menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_WHITE}  Created by {Colors.BRIGHT_GREEN}EngineXus-dev{Colors.ENDC} {Colors.BRIGHT_CYAN}v{VERSION}{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}  Statistics{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append(f"{Colors.WHITE}  • Domains to be Blocked: {Colors.BRIGHT_GREEN}{Colors.BOLD}{stats['domains_to_be_blocked']:,}{Colors.ENDC}")
    menu_lines.append(f"{Colors.WHITE}  • Current blocked domains: {Colors.BRIGHT_YELLOW}{Colors.BOLD}{stats['current_blocked_domains']:,}{Colors.ENDC}")
    menu_lines.append(f"{Colors.WHITE}  • Blocked services: {Colors.BRIGHT_MAGENTA}{Colors.BOLD}{stats['blocked_services']}{Colors.ENDC}")
    menu_lines.append(f"{Colors.WHITE}  • Enabled sources: {Colors.BRIGHT_CYAN}{Colors.BOLD}{stats['enabled_sources']}{Colors.ENDC}{Colors.WHITE} / {Colors.BRIGHT_WHITE}{stats['total_sources']}{Colors.ENDC}")
    menu_lines.append(f"{Colors.WHITE}  • Cached sources: {Colors.BRIGHT_BLUE}{Colors.BOLD}{stats['cached_sources']}{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append("")
    
    menu_lines.append(f"{Colors.BRIGHT_GREEN}{Colors.BOLD}  1.{Colors.ENDC}{Colors.WHITE} Install AdBlock (Use enabled sources){Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_BLUE}{Colors.BOLD}  2.{Colors.ENDC}{Colors.WHITE} Update AdBlock Hosts Files{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}  3.{Colors.ENDC}{Colors.WHITE} View current hosts file{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_YELLOW}{Colors.BOLD}  4.{Colors.ENDC}{Colors.WHITE} Backup current hosts file{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  5.{Colors.ENDC}{Colors.WHITE} Restore from backup{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_RED}{Colors.BOLD}  6.{Colors.ENDC}{Colors.WHITE} Restore OS default hosts file{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_GREEN}{Colors.BOLD}  7.{Colors.ENDC}{Colors.WHITE} Manage sources (Enable/Disable){Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_BLUE}{Colors.BOLD}  8.{Colors.ENDC}{Colors.WHITE} View available sources{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}  9.{Colors.ENDC}{Colors.WHITE} Add new source{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_YELLOW}{Colors.BOLD}  10.{Colors.ENDC}{Colors.WHITE} Remove source{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  11.{Colors.ENDC}{Colors.WHITE} Flush DNS cache{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_RED}{Colors.BOLD}  12.{Colors.ENDC}{Colors.WHITE} Block services{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_GREEN}{Colors.BOLD}  13.{Colors.ENDC}{Colors.WHITE} Redirect domains{Colors.ENDC}")
    menu_lines.append("")
    menu_lines.append("")
    menu_lines.append(f"{Colors.BRIGHT_RED}{Colors.BOLD}  0.{Colors.ENDC}{Colors.BRIGHT_WHITE} Exit{Colors.ENDC}")
    
    print()
    print_boxed_menu(menu_lines, width=70)
    print()


def show_sources_menu():
    """Display available hosts file sources (MUD-style colors)"""
    clear_screen()
    menu_lines = []
    
    menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    
    menu_lines.append(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  Available Sources{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append("")
    
    key_colors = [Colors.BRIGHT_GREEN, Colors.BRIGHT_BLUE, Colors.BRIGHT_CYAN, Colors.BRIGHT_YELLOW, 
                 Colors.BRIGHT_MAGENTA, Colors.BRIGHT_RED, Colors.BRIGHT_GREEN, Colors.BRIGHT_BLUE,
                 Colors.BRIGHT_CYAN, Colors.BRIGHT_YELLOW]
    
    for key, source in sorted(HOSTS_SOURCES.items(), key=lambda x: int(x[0])):
        key_color = key_colors[(int(key) - 1) % len(key_colors)] if key.isdigit() else Colors.BRIGHT_WHITE
        status = f"{Colors.BRIGHT_GREEN}{Colors.BOLD}[ENABLED]{Colors.ENDC}" if source.get('enabled', False) else f"{Colors.BRIGHT_RED}{Colors.BOLD}[DISABLED]{Colors.ENDC}"
        menu_lines.append(f"{key_color}{Colors.BOLD}  {key}.{Colors.ENDC}{Colors.WHITE} {source['name']} {status}{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_CYAN}    {source['description']}{Colors.ENDC}")
    
    print()
    print_boxed_menu(menu_lines, width=70)
    print()


def add_source():
    """Add a new source to the sources list"""
    global HOSTS_SOURCES
    clear_screen()
    
    menu_lines = []
    menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  Add New Source{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    
    print()
    print_boxed_menu(menu_lines, width=70)
    print()
    
    name = input(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}Source name: {Colors.ENDC}").strip()
    if not name or safe_comment(name) != name or len(name) > 100:
        print_error("Source name must be a single line of at most 100 characters")
        return False
    if any(src.get('name', '').casefold() == name.casefold() for src in HOSTS_SOURCES.values()):
        print_error("A source with that name already exists")
        return False
    
    url = input(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}Source URL: {Colors.ENDC}").strip()
    if not url:
        print_error("Source URL cannot be empty")
        return False
    
    if not url.startswith('https://') or not urllib.parse.urlsplit(url).hostname or urllib.parse.urlsplit(url).username or urllib.parse.urlsplit(url).password:
        print_error("Source URL must be valid HTTPS without credentials")
        return False
    
    description = input(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}Description (optional): {Colors.ENDC}").strip()
    if not description:
        description = f"Custom source: {name}"
    
    enabled_input = input(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}Enable this source? (y/n) [n]: {Colors.ENDC}").strip().lower()
    enabled = enabled_input == 'y'
    
    max_key = 0
    for key in HOSTS_SOURCES.keys():
        try:
            key_num = int(key)
            if key_num > max_key:
                max_key = key_num
        except ValueError:
            pass
    
    new_key = str(max_key + 1)
    
    HOSTS_SOURCES[new_key] = {
        'name': name,
        'url': url,
        'description': description,
        'enabled': enabled
    }
    
    if save_sources(HOSTS_SOURCES):
        print_success(f"Source '{name}' added successfully (ID: {new_key})")
        return True
    else:
        print_error("Failed to save new source")
        del HOSTS_SOURCES[new_key]
        return False


def remove_source():
    """Remove a source from the sources list"""
    global HOSTS_SOURCES
    clear_screen()
    
    if not HOSTS_SOURCES:
        print_warning("No sources available to remove")
        return False
    
    menu_lines = []
    
    menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    
    menu_lines.append(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  Remove Source{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append("")
    
    key_colors = [Colors.BRIGHT_GREEN, Colors.BRIGHT_BLUE, Colors.BRIGHT_CYAN, Colors.BRIGHT_YELLOW, 
                 Colors.BRIGHT_MAGENTA, Colors.BRIGHT_RED, Colors.BRIGHT_GREEN, Colors.BRIGHT_BLUE,
                 Colors.BRIGHT_CYAN, Colors.BRIGHT_YELLOW]
    
    for key, source in sorted(HOSTS_SOURCES.items(), key=lambda x: int(x[0])):
        key_color = key_colors[(int(key) - 1) % len(key_colors)] if key.isdigit() else Colors.BRIGHT_WHITE
        menu_lines.append(f"{key_color}{Colors.BOLD}  {key}.{Colors.ENDC}{Colors.WHITE} {source['name']}{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_CYAN}    {source['description']}{Colors.ENDC}")
    
    menu_lines.append("")
    menu_lines.append("")
    menu_lines.append(f"{Colors.BRIGHT_RED}{Colors.BOLD}  0.{Colors.ENDC}{Colors.BRIGHT_WHITE} Back{Colors.ENDC}")
    
    print()
    print_boxed_menu(menu_lines, width=70)
    print()
    
    choice = input(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}Enter your choice: {Colors.ENDC}").strip().lower()
    
    if choice == '0':
        print_info("Removal cancelled")
        return False
    
    if choice not in HOSTS_SOURCES:
        print_error("Invalid source number")
        return False
    
    source_name = HOSTS_SOURCES[choice]['name']
    source_backup = HOSTS_SOURCES[choice].copy()
    
    print_warning(f"You are about to remove: {source_name}")
    confirm = input(f"{Colors.WARNING}Are you sure? (y/n): {Colors.ENDC}").strip().lower()
    
    if confirm != 'y':
        print_info("Removal cancelled")
        return False
    
    del HOSTS_SOURCES[choice]
    
    if save_sources(HOSTS_SOURCES):
        print_success(f"Source '{source_name}' removed successfully")
        HOSTS_SOURCES = load_sources()
        return True
    else:
        print_error("Failed to save changes")
        HOSTS_SOURCES[choice] = source_backup
        return False


def manage_sources():
    """Standalone menu to manage which hosts file sources are enabled/disabled"""
    global HOSTS_SOURCES
    while True:
        clear_screen()
        menu_lines = []
        
        menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
        
        menu_lines.append(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  Manage Sources{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
        menu_lines.append("")
        
        enabled_count = 0
        key_colors = [Colors.BRIGHT_GREEN, Colors.BRIGHT_BLUE, Colors.BRIGHT_CYAN, Colors.BRIGHT_YELLOW, 
                     Colors.BRIGHT_MAGENTA, Colors.BRIGHT_RED, Colors.BRIGHT_GREEN, Colors.BRIGHT_BLUE,
                     Colors.BRIGHT_CYAN, Colors.BRIGHT_YELLOW]
        
        for key, source in sorted(HOSTS_SOURCES.items(), key=lambda x: int(x[0])):
            key_color = key_colors[(int(key) - 1) % len(key_colors)] if key.isdigit() else Colors.BRIGHT_WHITE
            status_text = f"{Colors.BRIGHT_GREEN}{Colors.BOLD}[ON]{Colors.ENDC}" if source.get('enabled', False) else f"{Colors.BRIGHT_RED}{Colors.BOLD}[OFF]{Colors.ENDC}"
            menu_lines.append(f"{key_color}{Colors.BOLD}  {key}.{Colors.ENDC}{Colors.WHITE} {source['name']} {status_text}{Colors.ENDC}")
            if source.get('enabled', False):
                enabled_count += 1
        
        menu_lines.append("")
        menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}  Enabled: {Colors.BRIGHT_GREEN}{enabled_count}{Colors.ENDC}{Colors.BRIGHT_CYAN} | Disabled: {Colors.BRIGHT_RED}{len(HOSTS_SOURCES) - enabled_count}{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
        menu_lines.append("")
        menu_lines.append("")
        menu_lines.append(f"{Colors.BRIGHT_RED}{Colors.BOLD}  0.{Colors.ENDC}{Colors.BRIGHT_WHITE} Back{Colors.ENDC}")
        
        print()
        print_boxed_menu(menu_lines, width=70)
        print()
        
        choice = input(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}Enter your choice: {Colors.ENDC}").strip().lower()
        
        if choice == '0':
            enabled_sources = [key for key, source in HOSTS_SOURCES.items() if source.get('enabled', False)]
            if not enabled_sources:
                print_warning("No sources are enabled. You won't be able to install adblock without enabling at least one source.")
                response = input(f"{Colors.WARNING}Continue anyway? (y/n): {Colors.ENDC}").strip().lower()
                if response != 'y':
                    continue
            if save_sources(HOSTS_SOURCES):
                print_success("Source settings saved")
            else:
                print_error("Failed to save source settings")
            return True
        
        elif choice in HOSTS_SOURCES:
            current_state = HOSTS_SOURCES[choice].get('enabled', False)
            HOSTS_SOURCES[choice]['enabled'] = not current_state
            status = "enabled" if not current_state else "disabled"
            print_success(f"{HOSTS_SOURCES[choice]['name']} {status}")
        
        else:
            print_error("Invalid choice. Please try again.")


def update_adblock_hosts():
    """Update AdBlock hosts files using enabled sources"""
    clear_screen()
    menu_lines = []
    menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  Update AdBlock Hosts Files{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    
    selected_sources = [key for key, source in HOSTS_SOURCES.items() if source.get('enabled', False)]
    
    if not selected_sources:
        menu_lines.append(f"{Colors.BRIGHT_RED}  No sources are enabled.{Colors.ENDC}")
        menu_lines.append(f"{Colors.WHITE}  Please enable at least one source in 'Manage sources' menu.{Colors.ENDC}")
        print()
        print_boxed_menu(menu_lines, width=70)
        print()
        return False
    
    menu_lines.append(f"{Colors.WHITE}  Updating {Colors.BRIGHT_CYAN}{len(selected_sources)}{Colors.ENDC}{Colors.WHITE} enabled source(s)...{Colors.ENDC}")
    menu_lines.append("")
    for source_key in selected_sources:
        menu_lines.append(f"{Colors.BRIGHT_CYAN}  • {HOSTS_SOURCES[source_key]['name']}{Colors.ENDC}")
    
    print()
    print_boxed_menu(menu_lines, width=70)
    print()
    
    print_info(f"Downloading from {len(selected_sources)} source(s)...")
    
    saved_files = []
    successful_downloads = 0
    
    for source_key in selected_sources:
        source = HOSTS_SOURCES[source_key]
        content = download_hosts_file(source['url'])
        if content:
            entries = parse_hosts_file(content)
            if entries:
                merged, _ = merge_hosts_entries([entries])
                file_path = save_source_file(source_key, source['name'], merged)
                if file_path:
                    saved_files.append(file_path)
                    successful_downloads += 1
                    print_success(f"Saved {len(merged)} entries from {source['name']} to {file_path}")
                else:
                    print_warning(f"Failed to save file for {source['name']}")
            else:
                print_warning(f"No valid entries found in {source['name']}")
    
    if not saved_files:
        print_error("No hosts files were saved")
        return False
    
    all_domains = set()
    for file_path in saved_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                entries = parse_hosts_file(content)
                merged, _ = merge_hosts_entries([entries])
                all_domains.update(merged.keys())
        except Exception:
            pass
    
    print_success(f"Downloaded and saved {len(saved_files)} source file(s)")
    print_success(f"Total unique domains across all sources: {len(all_domains)}")
    print_info(f"Source files saved in: {get_sources_directory()}")
    
    return True


def install_adblock():
    """Main function to install adblock using currently enabled sources (uses cached files if less than 1 week old)"""
    clear_screen()
    menu_lines = []
    menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  Installing AdBlock{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    
    selected_sources = [key for key, source in HOSTS_SOURCES.items() if source.get('enabled', False)]
    
    if not selected_sources:
        menu_lines.append(f"{Colors.BRIGHT_RED}  No sources are enabled.{Colors.ENDC}")
        menu_lines.append(f"{Colors.WHITE}  Please enable at least one source in 'Manage sources' menu.{Colors.ENDC}")
        print()
        print_boxed_menu(menu_lines, width=70)
        print()
        return False
    
    menu_lines.append(f"{Colors.WHITE}  Using {Colors.BRIGHT_CYAN}{len(selected_sources)}{Colors.ENDC}{Colors.WHITE} enabled source(s)...{Colors.ENDC}")
    menu_lines.append("")
    for source_key in selected_sources:
        menu_lines.append(f"{Colors.BRIGHT_CYAN}  • {HOSTS_SOURCES[source_key]['name']}{Colors.ENDC}")
    
    print()
    print_boxed_menu(menu_lines, width=70)
    print()
    
    saved_files = []
    successful_downloads = 0
    cached_files_used = 0
    
    for source_key in selected_sources:
        source = HOSTS_SOURCES[source_key]
        source_name = source['name']
        
        if is_source_cache_fresh(source_name, max_age_days=7):
            file_path = get_source_file_path(source_name)
            saved_files.append(file_path)
            cached_files_used += 1
            print_info(f"Using cached file for {source_name} (less than 1 week old)")
        else:
            if is_source_cached(source_name):
                print_info(f"Cache expired for {source_name}, downloading fresh copy...")
            else:
                print_info(f"Downloading {source_name}...")
            
            content = download_hosts_file(source['url'])
            if content:
                entries = parse_hosts_file(content)
                if entries:
                    merged, _ = merge_hosts_entries([entries])
                    file_path = save_source_file(source_key, source['name'], merged)
                    if file_path:
                        saved_files.append(file_path)
                        successful_downloads += 1
                        print_success(f"Downloaded and saved {len(merged)} entries from {source['name']}")
                    else:
                        print_warning(f"Failed to save file for {source['name']}")
                else:
                    print_warning(f"No valid entries found in {source['name']}")
            else:
                print_error(f"Verified download failed for {source['name']}; stale cache will not be installed")
    
    if not saved_files:
        print_error("No hosts files available (downloaded or cached)")
        return False
    
    if cached_files_used > 0:
        print_info(f"Used {cached_files_used} cached file(s), downloaded {successful_downloads} new file(s)")
    
    all_domains = set()
    for file_path in saved_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                entries = parse_hosts_file(content)
                merged, _ = merge_hosts_entries([entries])
                all_domains.update(merged.keys())
        except Exception:
            pass
    
    if successful_downloads > 0:
        print_success(f"Downloaded {successful_downloads} new source file(s)")
    print_success(f"Ready to install from {len(saved_files)} source file(s)")
    print_success(f"Total unique domains across all sources: {len(all_domains)}")
    print_info(f"Source files saved in: {get_sources_directory()}")
    
    menu_lines = []
    menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  Installation Ready{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append(f"{Colors.WHITE}  Total unique domains: {Colors.BRIGHT_GREEN}{Colors.BOLD}{len(all_domains):,}{Colors.ENDC}")
    menu_lines.append(f"{Colors.WHITE}  Source files saved in: {Colors.BRIGHT_CYAN}{get_sources_directory()}{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    
    print()
    print_boxed_menu(menu_lines, width=70)
    print()
    
    response = input(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}Install merged hosts file to system? (y/n): {Colors.ENDC}").strip().lower()
    if response == 'y':
        source_entries_dict = {}
        for file_path in saved_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    entries = parse_hosts_file(content)
                    if entries:
                        merged, _ = merge_hosts_entries([entries])
                        source_name = read_source_name_from_file(file_path)
                        source_entries_dict[source_name] = merged
            except Exception:
                pass
        
        if source_entries_dict:
            all_entries_list = []
            for entries in source_entries_dict.values():
                entries_list = [(ip, hostname) for hostname, ip in entries.items()]
                all_entries_list.append(entries_list)
            
            merged_all, _ = merge_hosts_entries(all_entries_list)
            
            header = f"# XusGuard - Blocked domains\n"
            hosts_content = create_hosts_content_merged(merged_all, source_entries_dict, header)
            
            hosts_path = get_hosts_file_path()
            
            try:
                with open(hosts_path, 'r', encoding='utf-8', errors='replace') as f:
                    original_content = f.read()
                final_content = replace_managed_section(original_content, hosts_content)
            except (OSError, ValueError) as e:
                print_error(f"Refusing unsafe hosts update: {e}")
                return False

            if install_hosts_file(hosts_path, final_content):
                print_success("AdBlock installed successfully!")
                print_info("You may need to flush your DNS cache for changes to take effect.")
                print_info("Use option 11 from the main menu to flush DNS cache.")
                return True
    
    return True


def flush_dns_cache():
    """Flush DNS caches without restarting network services or using a shell."""
    system = platform.system()
    if system == 'Windows':
        commands = [['ipconfig', '/flushdns']]
    elif system == 'Darwin':
        commands = [['dscacheutil', '-flushcache'], ['killall', '-HUP', 'mDNSResponder']]
    elif system == 'Linux':
        if shutil.which('resolvectl'):
            commands = [['resolvectl', 'flush-caches']]
        elif shutil.which('systemd-resolve'):
            commands = [['systemd-resolve', '--flush-caches']]
        else:
            print_warning("No supported DNS cache flusher was found.")
            return False
    else:
        print_warning(f"Unsupported OS for DNS flushing: {system}")
        return False

    success = True
    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=15, check=False)
            if result.returncode != 0:
                print_warning(f"DNS command failed: {command[0]} ({result.returncode})")
                success = False
        except (OSError, subprocess.TimeoutExpired) as exc:
            print_warning(f"DNS command unavailable or timed out: {exc}")
            success = False

    if success:
        print_success("DNS cache flush completed")
    else:
        print_warning("DNS flush incomplete. No network service was restarted.")
    return success


SERVICE_START = '# BEGIN XUSGUARD SERVICES'
SERVICE_END = '# END XUSGUARD SERVICES'


def split_service_section(content):
    """Return the unrelated file text and the bounded service-rule section."""
    lines = content.splitlines(keepends=True)
    start = [i for i, line in enumerate(lines) if line.strip() == SERVICE_START]
    end = [i for i, line in enumerate(lines) if line.strip() == SERVICE_END]
    if not start and not end:
        return content, ''
    if len(start) != 1 or len(end) != 1 or end[0] <= start[0]:
        raise ValueError("Malformed XusGuard service markers; refusing modification")
    return ''.join(lines[:start[0]] + lines[end[0] + 1:]), ''.join(lines[start[0] + 1:end[0]])


def get_service_blocked_domains(content):
    _, section = split_service_section(content)
    return set(dict.fromkeys(host for _, host in parse_hosts_file(section)))


def update_service_section(content, blocked_domains):
    base, _ = split_service_section(content)
    if not blocked_domains:
        return base.rstrip('\r\n') + '\n'
    entries = []
    for domain in sorted(blocked_domains):
        normalized = normalize_domain(domain)
        if domain != normalized:
            raise ValueError(f"Invalid service domain: {domain}")
        entries.append(f"0.0.0.0\t{domain}")
    return (base.rstrip('\r\n') + '\n\n' + SERVICE_START + '\n'
            + '\n'.join(entries) + '\n' + SERVICE_END + '\n')


def apply_service_changes(hosts_path, service_domains, enable, service_name):
    """Write only the dedicated service section; never remove third-party blocks."""
    try:
        original = Path(hosts_path).read_text(encoding='utf-8', errors='replace')
        existing = get_service_blocked_domains(original)
        for domain in service_domains:
            normalized = normalize_domain(domain)
            if normalized != domain:
                raise ValueError(f"Invalid service domain: {domain}")
            if enable:
                existing.add(domain)
            else:
                existing.discard(domain)
        revised = update_service_section(original, existing)
        if revised == original:
            return True
        return install_hosts_file(hosts_path, revised)
    except (OSError, ValueError) as exc:
        print_error(f"Cannot modify service rules safely: {exc}")
        return False

def load_service_catalog():
    """Load the opt-in access-blocking catalog; never auto-download services."""
    path = Path(__file__).resolve().parent / 'services.json'
    if path.is_symlink():
        raise ValueError("Refusing symlinked services catalog")
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not load services.json: {exc}") from exc
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise ValueError("Unsupported services.json schema")
    categories = data.get('categories')
    services = data.get('services')
    if (not isinstance(categories, list) or not 1 <= len(categories) <= 12
            or not all(isinstance(c, str) and c and len(c) <= 60 for c in categories)
            or len(categories) != len(set(categories))):
        raise ValueError("Invalid service categories")
    if not isinstance(services, list) or not 1 <= len(services) <= 100:
        raise ValueError("Invalid service collection")
    names = set()
    catalog = {}
    for idx, item in enumerate(services, 1):
        if not isinstance(item, dict):
            raise ValueError("Invalid service item")
        name, category, domains = item.get('name'), item.get('category'), item.get('domains')
        if (not isinstance(name, str) or not name or len(name) > 80
                or safe_comment(name) != name or name.casefold() in names
                or category not in categories or not isinstance(domains, list)
                or not 1 <= len(domains) <= 40):
            raise ValueError(f"Invalid service definition #{idx}")
        if not all(isinstance(d, str) and normalize_domain(d) == d for d in domains):
            raise ValueError(f"Unsafe domain in service definition #{idx}")
        if len(domains) != len(set(domains)):
            raise ValueError(f"Duplicate domain in service definition #{idx}")
        names.add(name.casefold())
        catalog[str(idx)] = {'name': name, 'category': category, 'domains': domains}
    return categories, catalog


def get_individual_services():
    return load_service_catalog()[1]


def get_service_domains_for_service(service_key):
    service = get_individual_services().get(str(service_key))
    return {domain: '0.0.0.0' for domain in service['domains']} if service else {}


def show_category_menu():
    clear_screen()
    categories, _ = load_service_catalog()
    print_boxed_menu(
        [f"{Colors.BOLD}XusGuard - Opt-in Service Blocking{Colors.ENDC}",
         "Service blocking can prevent entire websites and apps from working.",
         "Choose a category. [0] Back.", ""] +
        [f" {i}. {name}" for i, name in enumerate(categories, 1)],
        width=70,
    )
    return [(category, category) for category in categories]


def show_services_in_category(category_name):
    """Toggle an explicit service only inside XusGuard's service-owned section."""
    services = get_individual_services()
    matching = [(key, service) for key, service in services.items()
                if service['category'] == category_name]
    hosts_path = get_hosts_file_path()
    while True:
        try:
            hosts_content = Path(hosts_path).read_text(encoding='utf-8', errors='replace')
            enabled = get_service_blocked_domains(hosts_content)
        except (OSError, ValueError) as exc:
            print_error(f"Cannot read managed service rules: {exc}")
            return False
        clear_screen()
        options = [
            f"{Colors.BOLD}XusGuard - {category_name}{Colors.ENDC}",
            "Only entries in the XusGuard service section are changed.",
            "A service may use shared domains; blocking can break other websites.", ""
        ]
        for idx, (_, service) in enumerate(matching, 1):
            names = set(service['domains'])
            active = len(names & enabled)
            state = 'ON' if active == len(names) else ('PARTIAL' if active else 'OFF')
            options.append(f" {idx}. {service['name']} [{state}]")
        options.extend(["", " ALL. Toggle this entire category", " 0. Back"])
        print_boxed_menu(options, width=70)
        choice = safe_input("Choice: ").strip().lower()
        if choice == '0':
            return True
        if choice == 'all':
            if not matching:
                return True
            domain_set = set().union(*(set(s['domains']) for _, s in matching))
            currently_all_enabled = domain_set <= enabled
            changes = {d: '0.0.0.0' for d in domain_set}
            target = not currently_all_enabled
            if not apply_service_changes(hosts_path, changes, target, category_name):
                print_error("Category update failed")
            continue
        try:
            index = int(choice) - 1
            if index < 0 or index >= len(matching):
                raise ValueError("Not a menu option")
        except ValueError:
            print_warning("Invalid menu selection")
            continue
        key, service = matching[index]
        domains = get_service_domains_for_service(key)
        target = not set(domains).issubset(enabled)
        if not apply_service_changes(hosts_path, domains, target, service['name']):
            print_error("Service update failed")


def manage_service_blocking():
    while True:
        try:
            categories = show_category_menu()
        except ValueError as exc:
            print_error(f"Invalid services catalog: {exc}")
            return False
        selection = safe_input("Category number (0 to exit): ").strip()
        if selection == '0':
            return True
        try:
            index = int(selection) - 1
            if index < 0 or index >= len(categories):
                raise ValueError("Invalid category")
        except ValueError:
            print_warning("Invalid category")
            continue
        if not show_services_in_category(categories[index][1]):
            return False

def view_hosts_file():
    """View the current hosts file"""
    clear_screen()
    hosts_path = get_hosts_file_path()
    
    if not os.path.exists(hosts_path):
        print_error(f"Hosts file not found at {hosts_path}")
        return
    
    menu_lines = []
    menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  Current Hosts File{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append(f"{Colors.WHITE}  {hosts_path}{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    
    print()
    print_boxed_menu(menu_lines, width=70)
    print()
    try:
        with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
            if len(lines) > 50:
                print_info(f"Showing last 50 lines of {len(lines)} total lines:")
                print('\n'.join(lines[-50:]))
            else:
                print(content)
    except PermissionError:
        print_error("Permission denied. Please run with administrator/root privileges.")
    except Exception as e:
        print_error(f"Failed to read hosts file: {e}")


def get_owned_redirects(hosts_content):
    """Discover only XusGuard-owned redirects; reject incomplete marker pairs."""
    lines = hosts_content.splitlines()
    redirects = {}
    marker_prefix = '# XusGuard redirect: '
    for index, line in enumerate(lines):
        if not line.startswith(marker_prefix):
            continue
        domain = line[len(marker_prefix):].strip()
        if normalize_domain(domain) != domain or index + 1 >= len(lines):
            raise ValueError("Invalid or truncated XusGuard redirect marker")
        parts = lines[index + 1].split()
        if len(parts) != 2 or parts[1] != domain:
            raise ValueError(f"Malformed redirect target for {domain}")
        try:
            address = str(ipaddress.ip_address(parts[0]))
        except ValueError as exc:
            raise ValueError(f"Invalid redirect address for {domain}") from exc
        if domain in redirects:
            raise ValueError(f"Duplicate redirect marker for {domain}")
        redirects[domain] = address
    return redirects


def manage_domain_redirects():
    """Manage domain redirects (redirect domains to specific IP addresses)"""
    hosts_path = get_hosts_file_path()
    
    while True:
        clear_screen()
        redirects = {}
        if os.path.exists(hosts_path):
            try:
                with open(hosts_path, 'r', encoding='utf-8', errors='replace') as f:
                    redirects = get_owned_redirects(f.read())
            except (OSError, ValueError) as exc:
                print_error(f"Cannot read safe redirect entries: {exc}")
                return False
        
        menu_lines = []
        menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  Domain Redirects{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
        menu_lines.append("")
        
        if redirects:
            menu_lines.append(f"{Colors.WHITE}  Current Redirects:{Colors.ENDC}")
            menu_lines.append("")
            key_colors = [Colors.BRIGHT_GREEN, Colors.BRIGHT_BLUE, Colors.BRIGHT_CYAN, Colors.BRIGHT_YELLOW, 
                         Colors.BRIGHT_MAGENTA, Colors.BRIGHT_RED]
            for i, (domain, ip) in enumerate(sorted(redirects.items()), 1):
                key_color = key_colors[(i - 1) % len(key_colors)]
                menu_lines.append(f"{key_color}  {domain}{Colors.ENDC} → {Colors.BRIGHT_WHITE}{ip}{Colors.ENDC}")
            menu_lines.append("")
        else:
            menu_lines.append(f"{Colors.WHITE}  No redirects configured.{Colors.ENDC}")
            menu_lines.append("")
        
        menu_lines.append(f"{Colors.BRIGHT_GREEN}{Colors.BOLD}  1.{Colors.ENDC}{Colors.WHITE} Add redirect{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_BLUE}{Colors.BOLD}  2.{Colors.ENDC}{Colors.WHITE} Remove redirect{Colors.ENDC}")
        menu_lines.append("")
        menu_lines.append("")
        menu_lines.append(f"{Colors.BRIGHT_RED}{Colors.BOLD}  0.{Colors.ENDC}{Colors.BRIGHT_WHITE} Back{Colors.ENDC}")
        
        print()
        print_boxed_menu(menu_lines, width=70)
        print()
        
        choice = input(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}Enter your choice: {Colors.ENDC}").strip()
        
        if choice == '0':
            return True
        elif choice == '1':
            clear_screen()
            menu_lines = []
            menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
            menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
            menu_lines.append(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  Add Domain Redirect{Colors.ENDC}")
            menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
            print()
            print_boxed_menu(menu_lines, width=70)
            print()
            
            domain = input(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}Enter domain to redirect (e.g., example.com): {Colors.ENDC}").strip().lower()
            if not domain:
                print_error("Domain cannot be empty")
                input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
                continue
            
            if not normalize_domain(domain):
                print_error("Invalid domain format")
                input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
                continue
            
            target = input(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}Enter target (IP address or domain, e.g., 192.168.1.1 or target.com): {Colors.ENDC}").strip()
            if not target:
                print_error("Target cannot be empty")
                input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
                continue
            
            try:
                ip = str(ipaddress.ip_address(target))
            except ValueError:
                ip = None
            if ip is not None:
                pass
            else:
                if not normalize_domain(target):
                    print_error("Target must be a valid IP address or DNS hostname")
                    continue
                print_info(f"Resolving {target}...")
                try:
                    resolved_ip = socket.gethostbyname(target)
                    print_success(f"Resolved {target} → {resolved_ip}")
                    ip = resolved_ip
                except socket.gaierror:
                    print_error(f"Failed to resolve domain {target}")
                    input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
                    continue
                except Exception as e:
                    print_error(f"Error resolving domain: {e}")
                    input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
                    continue
            
            if add_redirect_to_hosts(hosts_path, domain, ip):
                if target != ip:
                    print_success(f"Redirect added: {domain} → {target} ({ip})")
                else:
                    print_success(f"Redirect added: {domain} → {ip}")
            else:
                print_error("Failed to add redirect")
            
            input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
        
        elif choice == '2':
            if not redirects:
                print_warning("No redirects to remove")
                input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
                continue
            
            clear_screen()
            menu_lines = []
            menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
            menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
            menu_lines.append(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  Remove Domain Redirect{Colors.ENDC}")
            menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
            menu_lines.append("")
            
            key_colors = [Colors.BRIGHT_GREEN, Colors.BRIGHT_BLUE, Colors.BRIGHT_CYAN, Colors.BRIGHT_YELLOW, 
                         Colors.BRIGHT_MAGENTA, Colors.BRIGHT_RED]
            redirect_list = sorted(redirects.items())
            
            if not redirect_list:
                print_warning("No user-configured redirects to remove")
                input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
                continue
            
            for i, (domain, ip) in enumerate(redirect_list, 1):
                key_color = key_colors[(i - 1) % len(key_colors)]
                menu_lines.append(f"{key_color}{Colors.BOLD}  {i}.{Colors.ENDC}{Colors.WHITE} {domain} → {ip}{Colors.ENDC}")
            
            menu_lines.append("")
            menu_lines.append("")
            menu_lines.append(f"{Colors.BRIGHT_RED}{Colors.BOLD}  0.{Colors.ENDC}{Colors.BRIGHT_WHITE} Back{Colors.ENDC}")
            
            print()
            print_boxed_menu(menu_lines, width=70)
            print()
            
            choice = input(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}Enter number to remove (or 0 to cancel): {Colors.ENDC}").strip()
            
            if choice == '0':
                continue
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(redirect_list):
                    domain_to_remove, ip_to_remove = redirect_list[idx]
                    if remove_redirect_from_hosts(hosts_path, domain_to_remove, ip_to_remove):
                        print_success(f"Redirect removed: {domain_to_remove} → {ip_to_remove}")
                    else:
                        print_error("Failed to remove redirect")
                else:
                    print_error("Invalid selection")
            except ValueError:
                print_error("Invalid input")
            
            input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
        
        else:
            print_error("Invalid choice. Please try again.")
            input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")


def add_redirect_to_hosts(hosts_path, domain, ip):
    """Add a clearly marked redirect, without rewriting unrelated entries."""
    domain = normalize_domain(domain)
    try:
        address = str(ipaddress.ip_address(ip))
        if not domain:
            raise ValueError("Invalid DNS hostname")
        with open(hosts_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        marker = f"# XusGuard redirect: {domain}"
        get_owned_redirects(content)  # Reject malformed markers before modifying anything.
        lines = content.splitlines()
        filtered = []
        index = 0
        while index < len(lines):
            if lines[index].strip() == marker:
                index += 2
            else:
                filtered.append(lines[index])
                index += 1
        filtered.extend([marker, f"{address}\t{domain}"])
        return install_hosts_file(hosts_path, '\n'.join(filtered).rstrip('\n') + '\n')
    except (OSError, ValueError) as exc:
        print_error(f"Failed to add redirect safely: {exc}")
        return False


def remove_redirect_from_hosts(hosts_path, domain, ip):
    """Remove only a redirect previously marked as owned by XusGuard."""
    domain = normalize_domain(domain)
    try:
        if not domain:
            raise ValueError("Invalid DNS hostname")
        marker = f"# XusGuard redirect: {domain}"
        with open(hosts_path, 'r', encoding='utf-8', errors='replace') as f:
            original_content = f.read()
        get_owned_redirects(original_content)  # Never remove unverified marker pairs.
        lines = original_content.splitlines()
        filtered = []
        removed = False
        i = 0
        while i < len(lines):
            if (lines[i].strip() == marker and i + 1 < len(lines)
                    and lines[i + 1].strip() == f"{ip}\t{domain}"):
                i += 2
                removed = True
            else:
                filtered.append(lines[i])
                i += 1
        if not removed:
            print_warning("No matching XusGuard-owned redirect found")
            return False
        return install_hosts_file(hosts_path, '\n'.join(filtered).rstrip('\n') + '\n')
    except (OSError, ValueError) as exc:
        print_error(f"Failed to remove redirect safely: {exc}")
        return False


def safe_input(prompt=""):
    """Safely handle input() calls, catching EOFError for non-interactive execution"""
    try:
        return input(prompt)
    except EOFError:
        # Try to use /dev/tty as fallback if stdin is not available
        try:
            with open('/dev/tty', 'r') as tty:
                print(prompt, end='', flush=True)
                return tty.readline().rstrip('\n')
        except (OSError, IOError, FileNotFoundError):
            # /dev/tty not available, show error and exit
            print_error("\nError: This script requires interactive input (stdin).")
            print_error("When using a one-liner with piping, stdin is not available.")
            print_info("\nPlease use one of these methods instead:")
            print_info("1. Download the script first, then run it:")
            print_info("   Download your XusGuard repository and run python3 xusguard.py locally.")
            print_info("   Elevate only when writing the system hosts file.")
            print_info("\n2. Use the installer script:")
            print_info("   Or run bash install.sh from the extracted project folder.")
            sys.exit(1)


def is_interactive():
    """Check if running in interactive mode (stdin is available or /dev/tty is accessible)"""
    if sys.stdin.isatty():
        return True
    # Check if /dev/tty is available as fallback
    try:
        with open('/dev/tty', 'r'):
            return True
    except (OSError, IOError, FileNotFoundError):
        return False


def main():
    """Main entry point"""
    global HOSTS_SOURCES
    
    # Check if running in interactive mode
    if not is_interactive():
        print_error("Error: This script requires interactive input (stdin).")
        print_error("When using a one-liner with piping, stdin is not available.")
        print_info("\nPlease use one of these methods instead:")
        print_info("1. Download the script first, then run it:")
        print_info("   Download your XusGuard repository and run python3 xusguard.py locally.")
        print_info("   Elevate only when writing the system hosts file.")
        print_info("\n2. Use the installer script:")
        print_info("   Or run bash install.sh from the extracted project folder.")
        sys.exit(1)
    
    HOSTS_SOURCES = load_sources()
    
    backup_dir = get_backup_directory()
    system = platform.system()
    default_filename = f"default_hosts_{system.lower()}.txt"
    default_path = backup_dir / default_filename
    if not default_path.exists():
        save_default_hosts_file()
    
    if not check_root():
        print_warning("Running without administrator/root privileges; read-only features remain available.")
        print_warning("Hosts-file changes require elevated privileges and will fail safely otherwise.")
    
    while True:
        show_menu()
        choice = safe_input(f"{Colors.BOLD}Enter your choice: {Colors.ENDC}").strip()
        
        if choice == '1':
            install_adblock()
        elif choice == '2':
            update_adblock_hosts()
        elif choice == '3':
            view_hosts_file()
        elif choice == '4':
            hosts_path = get_hosts_file_path()
            if backup_hosts_file(hosts_path, use_timestamp=True):
                print_success("Hosts file backed up successfully")
            else:
                print_error("Failed to backup hosts file")
        elif choice == '5':
            hosts_path = get_hosts_file_path()
            restore_hosts_file(hosts_path)
        elif choice == '6':
            hosts_path = get_hosts_file_path()
            print_warning("This will restore the OS default hosts file (removing all ad-blocking entries).")
            response = safe_input(f"{Colors.WARNING}Continue? (y/n): {Colors.ENDC}").strip().lower()
            if response == 'y':
                if restore_from_default_hosts(hosts_path):
                    print_success("Hosts file restored to OS default")
                else:
                    print_error("Failed to restore OS default hosts file")
            else:
                print_info("Restore cancelled")
        elif choice == '7':
            manage_sources()
            HOSTS_SOURCES = load_sources()
        elif choice == '8':
            show_sources_menu()
        elif choice == '9':
            if add_source():
                HOSTS_SOURCES = load_sources()
        elif choice == '10':
            if remove_source():
                pass
        elif choice == '11':
            flush_dns_cache()
        elif choice == '12':
            manage_service_blocking()
        elif choice == '13':
            manage_domain_redirects()
        elif choice == '0':
            print_info("Goodbye!")
            sys.exit(0)
        else:
            print_error("Invalid choice. Please try again.")
        
        if choice != '0':
            safe_input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")


def cleanup_project(non_interactive=False):
    """Only clear cached downloaded blocklists after explicit confirmation.

    Backups, source preferences and virtual environments are NEVER deleted here.
    """
    if non_interactive:
        print_error("Non-interactive cleanup disabled; backups are never auto-deleted.")
        return False
    response = safe_input("Delete only cached downloaded source files? Type 'yes': ").strip().lower()
    if response != 'yes':
        return False
    cache_dir = get_sources_directory()
    for cached in cache_dir.glob('*.hosts'):
        if not cached.is_symlink() and cached.is_file():
            cached.unlink()
    print_success("Cached source files removed. Backups and settings were preserved.")
    return True


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--cleanup':
        cleanup_project(non_interactive=True)
    else:
        main()

