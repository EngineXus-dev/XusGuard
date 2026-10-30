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
import secrets
import stat

VERSION = "2.0.0"




HOSTS_FILE_LOCATIONS = {
    'Darwin': '/etc/hosts',
    'Linux': '/etc/hosts',
    'Windows': r'C:\Windows\System32\drivers\etc\hosts'
}

BACKUP_SUFFIX = '.adblock_backup'
DEFAULT_BACKUP_DIR = 'hosts_backups'
SOURCES_DIR = 'hosts_sources'
SOURCES_JSON_FILE = 'sources.json'


def get_default_sources():
    """Get default sources from sources.json file (if it exists in script directory)"""
    script_dir = Path(__file__).resolve().parent
    default_json_path = script_dir / SOURCES_JSON_FILE
    
    if default_json_path.exists():
        try:
            with open(default_json_path, 'r', encoding='utf-8') as f:
                sources = json.load(f)
                for key, source in sources.items():
                    if 'enabled' not in source:
                        source['enabled'] = False
                return sources
        except (json.JSONDecodeError, IOError):
            pass
    
    return {}


def get_sources_json_path():
    """Get the path to the sources JSON file"""
    script_dir = Path(__file__).resolve().parent
    return script_dir / SOURCES_JSON_FILE


def load_sources():
    """Load sources from JSON file, or create default if it doesn't exist"""
    json_path = get_sources_json_path()
    
    if json_path.exists():
        try:
            if json_path.is_symlink():
                raise OSError("Refusing symlinked sources.json")
            with open(json_path, 'r', encoding='utf-8') as f:
                sources = json.load(f)
                for key, source in sources.items():
                    if 'enabled' not in source:
                        source['enabled'] = False
                return sources
        except (json.JSONDecodeError, OSError) as e:
            print_warning(f"Failed to load sources.json: {e}")
            print_info("Creating new sources.json...")
    
    default_sources = get_default_sources()
    
    if not default_sources:
        print_warning("No sources.json found. Creating empty sources file.")
        print_info("Please add sources using the 'Add new source' menu option.")
        default_sources = {}
    
    save_sources(default_sources)
    return default_sources


def save_sources(sources):
    """Save sources to JSON file"""
    json_path = get_sources_json_path()
    try:
        if json_path.is_symlink():
            raise OSError("Refusing to write symlinked sources.json")
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=json_path.parent,
                                         prefix='.xusguard-sources-', delete=False) as f:
            tmp_path = Path(f.name)
            json.dump(sources, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, json_path)
        return True
    except OSError as e:
        print_error(f"Failed to save sources.json: {e}")
        return False

HOSTS_SOURCES = get_default_sources()


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
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(text):
    """Print a formatted header (MUD-style colors)"""
    print(f"\n{Colors.BRIGHT_MAGENTA}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


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
        except:
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
        req = urllib.request.Request(url, headers={'User-Agent': 'XusGuard/1.1'})
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


def create_hosts_content_by_source(source_entries_dict, header_comment):
    """Create hosts file content with entries organized by source"""
    lines = [header_comment]
    lines.append(f"# Generated by XusGuard on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_domains = set()
    for entries in source_entries_dict.values():
        all_domains.update(entries.keys())
    lines.append(f"# Total unique blocked domains: {len(all_domains)}")
    lines.append("#")
    
    for source_name, entries in sorted(source_entries_dict.items()):
        if entries:
            lines.append(f"# {'='*60}")
            lines.append(f"# Source: {safe_comment(source_name)}")
            lines.append(f"# Domains: {len(entries)}")
            lines.append(f"# {'='*60}")
            lines.append("")
            
            for hostname in sorted(entries.keys()):
                lines.append(f"{entries[hostname]}\t{hostname}")
            
            lines.append("")
    
    return '\n'.join(lines) + '\n'


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


def safe_comment(value):
    """Prevent configured source names from injecting hosts-file lines."""
    return re.sub(r'[\x00-\x1f\x7f]', ' ', str(value))[:160]


def save_source_file(source_id, source_name, entries):
    """Save a source's entries to its own file"""
    sources_dir = get_sources_directory()
    filename = sanitize_filename(source_name) + '.hosts'
    file_path = sources_dir / filename
    
    try:
        lines = []
        lines.append(f"# Source: {safe_comment(source_name)}")
        lines.append(f"# Generated by XusGuard on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"# Total domains: {len(entries)}")
        lines.append("#")
        lines.append("")
        
        for hostname in sorted(entries.keys()):
            lines.append(f"{entries[hostname]}\t{hostname}")
        
        content = '\n'.join(lines) + '\n'
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(file_path)
    except Exception as e:
        print_error(f"Failed to save source file for {source_name}: {e}")
        return None


def get_source_file_path(source_name):
    """Get the file path for a source based on its name"""
    sources_dir = get_sources_directory()
    filename = sanitize_filename(source_name) + '.hosts'
    return sources_dir / filename


def is_source_cached(source_name):
    """Check if a source file is already cached"""
    file_path = get_source_file_path(source_name)
    return file_path.exists() and file_path.stat().st_size > 0


def is_source_cache_fresh(source_name, max_age_days=7):
    """Check if a cached source file exists and is less than max_age_days old"""
    file_path = get_source_file_path(source_name)
    if not file_path.exists():
        return False
    
    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
    age = datetime.now() - file_mtime
    
    return age < timedelta(days=max_age_days)


def read_source_name_from_file(file_path):
    """Extract source name from a saved hosts file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line.startswith('# Source:'):
                return first_line.replace('# Source:', '').strip()
    except:
        pass
    return Path(file_path).stem.replace('_', ' ')


def backup_hosts_file(hosts_path, use_timestamp=True):
    """Fail closed if the hosts file cannot be safely and completely backed up."""
    try:
        target = Path(hosts_path)
        if target.is_symlink() or not target.is_file():
            raise OSError("Hosts file is missing, not regular, or is a symbolic link")
        backup_dir = get_backup_directory()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backup_path = backup_dir / (
            f"{target.name}_{timestamp}_{secrets.token_hex(4)}{BACKUP_SUFFIX}"
        )
        with target.open('rb') as src, backup_path.open('xb') as dst:
            shutil.copyfileobj(src, dst)
            dst.flush()
            os.fsync(dst.fileno())
        if os.name != 'nt':
            backup_path.chmod(0o600)
        if backup_path.stat().st_size != target.stat().st_size:
            backup_path.unlink(missing_ok=True)
            raise OSError("Backup size verification failed")
        print_success(f"Backup created: {backup_path}")
        return True
    except Exception as exc:
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


def restore_hosts_file(hosts_path):
    """Restore hosts file from backup - shows menu to select backup"""
    clear_screen()
    backup_dir = get_backup_directory()
    
    backups = []
    
    simple_backup = Path(hosts_path + BACKUP_SUFFIX)
    if simple_backup.exists():
        backups.append(('1', str(simple_backup), simple_backup.stat().st_mtime))
    
    backup_files = list(backup_dir.glob(f"*{BACKUP_SUFFIX}"))
    # Preserve access to backups made by older releases inside the checkout.
    legacy_backup_dir = Path(__file__).resolve().parent / DEFAULT_BACKUP_DIR
    if (legacy_backup_dir != backup_dir and legacy_backup_dir.is_dir()
            and not legacy_backup_dir.is_symlink()):
        backup_files.extend(legacy_backup_dir.glob(f"*{BACKUP_SUFFIX}"))
    backup_files = [p for p in backup_files if p.is_file() and not p.is_symlink()]
    for backup_file in sorted(backup_files, key=lambda x: x.stat().st_mtime, reverse=True):
        backups.append((str(len(backups) + 1), str(backup_file), backup_file.stat().st_mtime))
    
    if not backups:
        print_error("No backup files found")
        return False
    
    menu_lines = []
    
    menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    
    menu_lines.append(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  Select Backup to Restore{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append("")
    
    key_colors = [Colors.BRIGHT_GREEN, Colors.BRIGHT_BLUE, Colors.BRIGHT_CYAN, Colors.BRIGHT_YELLOW, 
                 Colors.BRIGHT_MAGENTA, Colors.BRIGHT_RED, Colors.BRIGHT_GREEN, Colors.BRIGHT_BLUE,
                 Colors.BRIGHT_CYAN, Colors.BRIGHT_YELLOW]
    
    for idx, (num, backup_path, mtime) in enumerate(backups, 1):
        timestamp = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        key_color = key_colors[(int(num) - 1) % len(key_colors)] if num.isdigit() else Colors.BRIGHT_WHITE
        menu_lines.append(f"{key_color}{Colors.BOLD}  {num}.{Colors.ENDC}{Colors.WHITE} {backup_path}{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_CYAN}    Created: {timestamp}{Colors.ENDC}")
    
    menu_lines.append("")
    menu_lines.append("")
    menu_lines.append(f"{Colors.BRIGHT_RED}{Colors.BOLD}  0.{Colors.ENDC}{Colors.BRIGHT_WHITE} Back{Colors.ENDC}")
    
    print()
    print_boxed_menu(menu_lines, width=70)
    print()
    
    choice = input(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}Enter your choice: {Colors.ENDC}").strip()
    
    if choice == '0' or not choice:
        print_info("Restore cancelled")
        return False
    
    selected_backup = None
    for num, backup_path, _ in backups:
        if num == choice:
            selected_backup = backup_path
            break
    
    if not selected_backup or not os.path.exists(selected_backup):
        print_error("Invalid selection")
        return False
    
    try:
        if Path(selected_backup).is_symlink() or not Path(selected_backup).is_file():
            return False
        if not install_hosts_file(hosts_path, Path(selected_backup).read_text(encoding='utf-8')):
            return False
        print_success(f"Hosts file restored from {selected_backup}")
        return True
    except Exception as e:
        print_error(f"Failed to restore backup: {e}")
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


def install_hosts_file(hosts_path, content):
    """Back up then stage the full write before replacing the hosts file."""
    temp_path = None
    try:
        target = Path(hosts_path)
        if target.is_symlink() or not target.is_file():
            raise OSError("Refusing to change a missing, non-regular or symlink hosts file")
        if not isinstance(content, str) or '\x00' in content or len(content.encode('utf-8')) > 40 * 1024 * 1024:
            raise ValueError("Invalid hosts file contents or larger than 40 MiB")
        if not backup_hosts_file(str(target)):
            return False
        old_stat = target.stat()
        with tempfile.NamedTemporaryFile(
            mode='wb', prefix='.xusguard-', suffix='.tmp',
            dir=str(target.parent), delete=False
        ) as tmp:
            temp_path = Path(tmp.name)
            tmp.write(content.encode('utf-8'))
            tmp.flush()
            os.fsync(tmp.fileno())
        shutil.copystat(target, temp_path)
        if os.name != 'nt' and hasattr(os, 'chown'):
            os.chown(temp_path, old_stat.st_uid, old_stat.st_gid)
            os.chmod(temp_path, stat.S_IMODE(old_stat.st_mode))
        # Refuse unsafe in-place fallback if Windows or antivirus blocks replacement.
        os.replace(temp_path, target)
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
        except:
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
                if is_source_cached(source_name):
                    file_path = get_source_file_path(source_name)
                    saved_files.append(file_path)
                    print_warning(f"Download failed for {source['name']}, using cached file")
                else:
                    print_error(f"Download failed for {source['name']} and no cached file available")
    
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
        except:
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
            except:
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


def get_service_domains(matching_sources):
    """Get all domains from matching service sources"""
    all_domains = {}
    
    for source_key, source in matching_sources:
        source_file_path = get_source_file_path(source_key, source['name'])
        if source_file_path and os.path.exists(source_file_path):
            try:
                with open(source_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    entries = parse_hosts_file(content)
                    if entries:
                        merged, _ = merge_hosts_entries([entries])
                        all_domains.update(merged)
            except Exception as e:
                print_warning(f"Could not read cached file for {source['name']}: {e}")
        
        if not all_domains or not (source_file_path and os.path.exists(source_file_path)):
            print_info(f"Downloading {source['name']}...")
            content = download_hosts_file(source['url'])
            if content:
                entries = parse_hosts_file(content)
                if entries:
                    merged, _ = merge_hosts_entries([entries])
                    all_domains.update(merged)
                    if source_file_path:
                        save_source_file(source_key, source['name'], merged)
    
    return all_domains


def apply_service_changes(hosts_path, service_domains, enable, service_name):
    """Change only the marked managed section, leaving user entries untouched."""
    try:
        with open(hosts_path, 'r', encoding='utf-8', errors='replace') as f:
            original = f.read()
        base, managed = split_managed_section(original)
        existing, _ = merge_hosts_entries([parse_hosts_file(managed)])
        for domain, ip in service_domains.items():
            normalized = normalize_domain(domain)
            if not normalized:
                continue
            if enable:
                existing[normalized] = '0.0.0.0'
            else:
                existing.pop(normalized, None)
        body = '# XusGuard - Blocked domains\n' + ''.join(
            f"0.0.0.0\t{domain}\n" for domain in sorted(existing)
        )
        # Pass the complete original to preserve any previous marked section.
        return install_hosts_file(hosts_path, replace_managed_section(original, body))
    except (OSError, ValueError) as exc:
        print_error(f"Failed to update service blocking safely: {exc}")
        return False


def get_individual_services():
    """Get comprehensive list of individual services with their domains"""
    services = {}
    service_id = 1
    
    social_media = [
        {'name': 'Facebook', 'domains': ['facebook.com', 'www.facebook.com', 'm.facebook.com', 'fb.com', 'facebook.net', 'fbcdn.net', 'facebookmail.com', 'fbsbx.com', 'fbstatic.com', 'facebook.org', 'messenger.com']},
        {'name': 'Instagram', 'domains': ['instagram.com', 'www.instagram.com', 'cdninstagram.com', 'instagramstatic.com', 'ig.com']},
        {'name': 'Twitter/X', 'domains': ['twitter.com', 'www.twitter.com', 'x.com', 'www.x.com', 't.co', 'twimg.com', 'twitpic.com', 'twitterinc.com', 'twitter.jp']},
        {'name': 'TikTok', 'domains': ['tiktok.com', 'www.tiktok.com', 'tiktokcdn.com', 'tiktokv.com', 'tiktok.org', 'musical.ly', 'tiktokads.com']},
        {'name': 'Snapchat', 'domains': ['snapchat.com', 'www.snapchat.com', 'snap.com', 'sc-cdn.net', 'snap-dev.net', 'snapkit.co']},
        {'name': 'LinkedIn', 'domains': ['linkedin.com', 'www.linkedin.com', 'licdn.com', 'linkedin.at', 'linkedin.cn']},
        {'name': 'Pinterest', 'domains': ['pinterest.com', 'www.pinterest.com', 'pinimg.com', 'pinterestmail.com', 'pinterest.jp']},
        {'name': 'Reddit', 'domains': ['reddit.com', 'www.reddit.com', 'redd.it', 'redditstatic.com', 'redditmedia.com', 'redditgifts.com']},
        {'name': 'Discord', 'domains': ['discord.com', 'www.discord.com', 'discordapp.com', 'discord.gg', 'discordapp.net', 'discord.media']},
        {'name': 'WhatsApp', 'domains': ['whatsapp.com', 'www.whatsapp.com', 'wa.me', 'whatsapp.net', 'whatsapp.org', 'whatsapp-cdn-shv-01-ams2.fbcdn.net']},
        {'name': 'Telegram', 'domains': ['telegram.org', 'www.telegram.org', 't.me', 'telegram.me', 'tdesktop.com', 'telegram-cdn.org']},
        {'name': 'YouTube', 'domains': ['youtube.com', 'www.youtube.com', 'youtu.be', 'ytimg.com', 'googlevideo.com', 'youtube-nocookie.com', 'youtubeeducation.com']},
        {'name': 'Twitch', 'domains': ['twitch.tv', 'www.twitch.tv', 'ttvnw.net', 'twitchcdn.net', 'twitchsvc.net', 'twitchcon.com']},
        {'name': 'Tumblr', 'domains': ['tumblr.com', 'www.tumblr.com', 'tumblr.co', 'tumblr.io']},
        {'name': 'VK (VKontakte)', 'domains': ['vk.com', 'www.vk.com', 'vk.me', 'vk-cdn.net', 'vk.ru']},
        {'name': 'WeChat', 'domains': ['wechat.com', 'www.wechat.com', 'weixin.qq.com', 'weixin110.qq.com']},
        {'name': 'Line', 'domains': ['line.me', 'www.line.me', 'line-apps.com', 'line-scdn.net']},
        {'name': 'Weibo', 'domains': ['weibo.com', 'www.weibo.com', 'weibocdn.com']},
        {'name': 'QQ', 'domains': ['qq.com', 'www.qq.com', 'qzone.com', 'tencent.com']},
        {'name': 'Baidu', 'domains': ['baidu.com', 'www.baidu.com', 'baidupcs.com']},
        {'name': 'Mixi', 'domains': ['mixi.jp', 'www.mixi.jp']},
        {'name': 'Viber', 'domains': ['viber.com', 'www.viber.com', 'viber.com.cy']},
        {'name': 'Skype', 'domains': ['skype.com', 'www.skype.com', 'skypeassets.com', 'skypeforbusiness.com']},
        {'name': 'Signal', 'domains': ['signal.org', 'www.signal.org', 'signal.art']},
        {'name': 'Mastodon', 'domains': ['mastodon.social', 'mastodon.online', 'mastodon.cloud']},
        {'name': 'Truth Social', 'domains': ['truthsocial.com', 'www.truthsocial.com']},
        {'name': 'Parler', 'domains': ['parler.com', 'www.parler.com']},
        {'name': 'Gab', 'domains': ['gab.com', 'www.gab.com']},
        {'name': 'MeWe', 'domains': ['mewe.com', 'www.mewe.com']},
        {'name': 'Clubhouse', 'domains': ['clubhouse.com', 'www.clubhouse.com', 'joinclubhouse.com']},
    ]
    
    streaming = [
        {'name': 'Netflix', 'domains': ['netflix.com', 'www.netflix.com', 'nflxext.com', 'nflximg.net', 'nflxso.net', 'nflxvideo.net', 'netflix.net']},
        {'name': 'Disney+', 'domains': ['disneyplus.com', 'www.disneyplus.com', 'disney.com', 'disneystreaming.com', 'disneynow.com']},
        {'name': 'Hulu', 'domains': ['hulu.com', 'www.hulu.com', 'huluim.com', 'hulustream.com']},
        {'name': 'Amazon Prime Video', 'domains': ['primevideo.com', 'www.primevideo.com', 'amazonvideo.com', 'aiv-cdn.net']},
        {'name': 'HBO Max', 'domains': ['hbomax.com', 'www.hbomax.com', 'hbo.com', 'hbonow.com']},
        {'name': 'Spotify', 'domains': ['spotify.com', 'www.spotify.com', 'spotifycdn.com', 'spotify.net', 'scdn.co', 'spotifyads.com']},
        {'name': 'Apple Music', 'domains': ['music.apple.com', 'itunes.apple.com', 'itunes.com']},
        {'name': 'SoundCloud', 'domains': ['soundcloud.com', 'www.soundcloud.com', 'sndcdn.com', 'soundcloud.org']},
        {'name': 'Pandora', 'domains': ['pandora.com', 'www.pandora.com']},
        {'name': 'Deezer', 'domains': ['deezer.com', 'www.deezer.com']},
        {'name': 'Tidal', 'domains': ['tidal.com', 'www.tidal.com']},
        {'name': 'Apple TV+', 'domains': ['tv.apple.com']},
        {'name': 'Paramount+', 'domains': ['paramountplus.com', 'www.paramountplus.com', 'cbs.com']},
        {'name': 'Peacock', 'domains': ['peacocktv.com', 'www.peacocktv.com', 'nbc.com']},
        {'name': 'Crunchyroll', 'domains': ['crunchyroll.com', 'www.crunchyroll.com']},
        {'name': 'Funimation', 'domains': ['funimation.com', 'www.funimation.com']},
        {'name': 'Vudu', 'domains': ['vudu.com', 'www.vudu.com']},
        {'name': 'FuboTV', 'domains': ['fubo.tv', 'www.fubo.tv']},
        {'name': 'Sling TV', 'domains': ['sling.com', 'www.sling.com']},
        {'name': 'YouTube TV', 'domains': ['tv.youtube.com']},
        {'name': 'Pluto TV', 'domains': ['pluto.tv', 'www.pluto.tv']},
        {'name': 'Tubi', 'domains': ['tubitv.com', 'www.tubitv.com']},
        {'name': 'Crackle', 'domains': ['crackle.com', 'www.crackle.com']},
        {'name': 'Vimeo', 'domains': ['vimeo.com', 'www.vimeo.com', 'vimeocdn.com']},
        {'name': 'Dailymotion', 'domains': ['dailymotion.com', 'www.dailymotion.com']},
    ]
    
    gaming = [
        {'name': 'Steam', 'domains': ['steamcommunity.com', 'steampowered.com', 'steam-chat.com', 'steamcontent.com', 'steamstatic.com']},
        {'name': 'Epic Games', 'domains': ['epicgames.com', 'www.epicgames.com', 'epicgames.net', 'unrealengine.com']},
        {'name': 'Xbox Live', 'domains': ['xbox.com', 'www.xbox.com', 'xboxlive.com', 'xboxservices.com', 'xboxab.com']},
        {'name': 'PlayStation Network', 'domains': ['playstation.com', 'www.playstation.com', 'sonyentertainmentnetwork.com', 'playstation.net']},
        {'name': 'Nintendo', 'domains': ['nintendo.com', 'www.nintendo.com', 'nintendo.net', 'nintendoswitch.com', 'nintendo.co.jp']},
        {'name': 'Roblox', 'domains': ['roblox.com', 'www.roblox.com', 'robloxlabs.com', 'rbxcdn.com']},
        {'name': 'Minecraft', 'domains': ['minecraft.net', 'www.minecraft.net', 'mojang.com', 'minecraftshop.net']},
        {'name': 'EA Origin', 'domains': ['origin.com', 'www.origin.com', 'ea.com', 'eaplay.com']},
        {'name': 'Battle.net', 'domains': ['battle.net', 'www.battle.net', 'blizzard.com', 'blizzcon.com']},
        {'name': 'Ubisoft', 'domains': ['ubisoft.com', 'www.ubisoft.com', 'uplay.com']},
        {'name': 'GOG', 'domains': ['gog.com', 'www.gog.com']},
        {'name': 'Riot Games', 'domains': ['riotgames.com', 'www.riotgames.com', 'leagueoflegends.com']},
        {'name': 'Valorant', 'domains': ['playvalorant.com', 'www.playvalorant.com', 'valorant.com']},
        {'name': 'Fortnite', 'domains': ['fortnite.com', 'www.fortnite.com']},
        {'name': 'PUBG', 'domains': ['pubg.com', 'www.pubg.com', 'pubgmobile.com']},
        {'name': 'Call of Duty', 'domains': ['callofduty.com', 'www.callofduty.com']},
        {'name': 'Apex Legends', 'domains': ['apexlegends.com', 'www.apexlegends.com']},
        {'name': 'Overwatch', 'domains': ['playoverwatch.com', 'www.playoverwatch.com']},
        {'name': 'World of Warcraft', 'domains': ['worldofwarcraft.com', 'www.worldofwarcraft.com']},
        {'name': 'Counter-Strike', 'domains': ['counter-strike.net', 'www.counter-strike.net']},
        {'name': 'Dota 2', 'domains': ['dota2.com', 'www.dota2.com']},
        {'name': 'Team Fortress 2', 'domains': ['teamfortress.com', 'www.teamfortress.com']},
        {'name': 'Among Us', 'domains': ['innersloth.com', 'www.innersloth.com']},
        {'name': 'Fall Guys', 'domains': ['fallguys.com', 'www.fallguys.com']},
        {'name': 'Genshin Impact', 'domains': ['genshin.mihoyo.com', 'genshin.hoyoverse.com', 'hoyoverse.com']},
        {'name': 'Honkai Impact', 'domains': ['honkaiimpact3.mihoyo.com', 'honkai.hoyoverse.com']},
        {'name': 'GTA Online', 'domains': ['rockstargames.com', 'www.rockstargames.com']},
        {'name': 'FIFA', 'domains': ['fifa.com', 'www.fifa.com', 'ea.com']},
        {'name': 'Madden NFL', 'domains': ['madden.com', 'www.madden.com']},
        {'name': 'NBA 2K', 'domains': ['2k.com', 'www.2k.com']},
    ]
    
    shopping = [
        {'name': 'Amazon', 'domains': ['amazon.com', 'www.amazon.com', 'amazon.co.uk', 'amazon.de', 'amazon.fr', 'amazonaws.com', 'amazon-adsystem.com']},
        {'name': 'eBay', 'domains': ['ebay.com', 'www.ebay.com', 'ebayimg.com', 'ebaystatic.com', 'ebayinc.com']},
        {'name': 'AliExpress', 'domains': ['aliexpress.com', 'www.aliexpress.com', 'aliexpress.ru']},
        {'name': 'Wish', 'domains': ['wish.com', 'www.wish.com']},
        {'name': 'Etsy', 'domains': ['etsy.com', 'www.etsy.com']},
        {'name': 'Walmart', 'domains': ['walmart.com', 'www.walmart.com', 'walmart.ca']},
        {'name': 'Target', 'domains': ['target.com', 'www.target.com']},
        {'name': 'Best Buy', 'domains': ['bestbuy.com', 'www.bestbuy.com']},
        {'name': 'Costco', 'domains': ['costco.com', 'www.costco.com']},
        {'name': 'Home Depot', 'domains': ['homedepot.com', 'www.homedepot.com']},
        {'name': 'Lowe\'s', 'domains': ['lowes.com', 'www.lowes.com']},
        {'name': 'Macy\'s', 'domains': ['macys.com', 'www.macys.com']},
        {'name': 'Nordstrom', 'domains': ['nordstrom.com', 'www.nordstrom.com']},
        {'name': 'Zappos', 'domains': ['zappos.com', 'www.zappos.com']},
        {'name': 'ASOS', 'domains': ['asos.com', 'www.asos.com']},
        {'name': 'Shein', 'domains': ['shein.com', 'www.shein.com']},
        {'name': 'Temu', 'domains': ['temu.com', 'www.temu.com']},
        {'name': 'Wayfair', 'domains': ['wayfair.com', 'www.wayfair.com']},
        {'name': 'Overstock', 'domains': ['overstock.com', 'www.overstock.com']},
        {'name': 'Newegg', 'domains': ['newegg.com', 'www.newegg.com']},
        {'name': 'Shopify', 'domains': ['shopify.com', 'www.shopify.com']},
        {'name': 'WooCommerce', 'domains': ['woocommerce.com', 'www.woocommerce.com']},
        {'name': 'Magento', 'domains': ['magento.com', 'www.magento.com']},
        {'name': 'BigCommerce', 'domains': ['bigcommerce.com', 'www.bigcommerce.com']},
        {'name': 'Square', 'domains': ['square.com', 'www.square.com', 'squareup.com']},
    ]
    
    news = [
        {'name': 'CNN', 'domains': ['cnn.com', 'www.cnn.com', 'cnn.io', 'cnn.net']},
        {'name': 'BBC', 'domains': ['bbc.com', 'www.bbc.com', 'bbc.co.uk', 'bbci.co.uk', 'bbcnews.com']},
        {'name': 'Fox News', 'domains': ['foxnews.com', 'www.foxnews.com', 'fox.com', 'foxbusiness.com']},
        {'name': 'The New York Times', 'domains': ['nytimes.com', 'www.nytimes.com', 'nyt.com', 'nytimes.net']},
        {'name': 'The Guardian', 'domains': ['theguardian.com', 'www.theguardian.com', 'guardian.co.uk']},
        {'name': 'The Washington Post', 'domains': ['washingtonpost.com', 'www.washingtonpost.com']},
        {'name': 'USA Today', 'domains': ['usatoday.com', 'www.usatoday.com']},
        {'name': 'Wall Street Journal', 'domains': ['wsj.com', 'www.wsj.com']},
        {'name': 'Reuters', 'domains': ['reuters.com', 'www.reuters.com']},
        {'name': 'Associated Press', 'domains': ['ap.org', 'www.ap.org', 'apnews.com']},
        {'name': 'NPR', 'domains': ['npr.org', 'www.npr.org']},
        {'name': 'ABC News', 'domains': ['abcnews.go.com', 'abc.com']},
        {'name': 'CBS News', 'domains': ['cbsnews.com', 'www.cbsnews.com', 'cbs.com']},
        {'name': 'NBC News', 'domains': ['nbcnews.com', 'www.nbcnews.com', 'nbc.com']},
        {'name': 'MSNBC', 'domains': ['msnbc.com', 'www.msnbc.com']},
        {'name': 'CNBC', 'domains': ['cnbc.com', 'www.cnbc.com']},
        {'name': 'Bloomberg', 'domains': ['bloomberg.com', 'www.bloomberg.com']},
        {'name': 'Forbes', 'domains': ['forbes.com', 'www.forbes.com']},
        {'name': 'Time', 'domains': ['time.com', 'www.time.com']},
        {'name': 'Newsweek', 'domains': ['newsweek.com', 'www.newsweek.com']},
        {'name': 'The Economist', 'domains': ['economist.com', 'www.economist.com']},
        {'name': 'Politico', 'domains': ['politico.com', 'www.politico.com']},
        {'name': 'The Hill', 'domains': ['thehill.com', 'www.thehill.com']},
        {'name': 'Breitbart', 'domains': ['breitbart.com', 'www.breitbart.com']},
        {'name': 'Daily Mail', 'domains': ['dailymail.co.uk', 'www.dailymail.co.uk']},
        {'name': 'The Telegraph', 'domains': ['telegraph.co.uk', 'www.telegraph.co.uk']},
        {'name': 'The Times', 'domains': ['thetimes.co.uk', 'www.thetimes.co.uk']},
        {'name': 'Al Jazeera', 'domains': ['aljazeera.com', 'www.aljazeera.com']},
        {'name': 'RT (Russia Today)', 'domains': ['rt.com', 'www.rt.com']},
        {'name': 'Xinhua', 'domains': ['xinhuanet.com', 'www.xinhuanet.com']},
    ]
    
    productivity = [
        {'name': 'Google Drive', 'domains': ['drive.google.com', 'docs.google.com', 'sheets.google.com', 'slides.google.com', 'forms.google.com']},
        {'name': 'Dropbox', 'domains': ['dropbox.com', 'www.dropbox.com', 'dropboxapi.com', 'dropboxusercontent.com']},
        {'name': 'OneDrive', 'domains': ['onedrive.com', 'www.onedrive.com', 'onedrive.live.com', 'live.com']},
        {'name': 'iCloud', 'domains': ['icloud.com', 'www.icloud.com', 'icloud-content.com']},
        {'name': 'Zoom', 'domains': ['zoom.us', 'www.zoom.us', 'zoom.com', 'zoomgov.com']},
        {'name': 'Microsoft Teams', 'domains': ['teams.microsoft.com', 'teams.live.com', 'office.com']},
        {'name': 'Slack', 'domains': ['slack.com', 'www.slack.com', 'slack-edge.com', 'slack-imgs.com']},
        {'name': 'Microsoft Office', 'domains': ['office.com', 'www.office.com', 'office365.com', 'microsoft.com']},
        {'name': 'Google Workspace', 'domains': ['workspace.google.com', 'gsuite.google.com']},
        {'name': 'Notion', 'domains': ['notion.so', 'www.notion.so']},
        {'name': 'Evernote', 'domains': ['evernote.com', 'www.evernote.com']},
        {'name': 'Trello', 'domains': ['trello.com', 'www.trello.com']},
        {'name': 'Asana', 'domains': ['asana.com', 'www.asana.com']},
        {'name': 'Monday.com', 'domains': ['monday.com', 'www.monday.com']},
        {'name': 'Basecamp', 'domains': ['basecamp.com', 'www.basecamp.com']},
        {'name': 'Jira', 'domains': ['atlassian.com', 'www.atlassian.com', 'jira.com']},
        {'name': 'Confluence', 'domains': ['confluence.com', 'www.confluence.com']},
        {'name': 'GitHub', 'domains': ['github.com', 'www.github.com', 'github.io', 'githubusercontent.com']},
        {'name': 'GitLab', 'domains': ['gitlab.com', 'www.gitlab.com']},
        {'name': 'Bitbucket', 'domains': ['bitbucket.org', 'www.bitbucket.org']},
        {'name': 'Figma', 'domains': ['figma.com', 'www.figma.com']},
        {'name': 'Adobe Creative Cloud', 'domains': ['adobe.com', 'www.adobe.com', 'adobelogin.com']},
        {'name': 'Canva', 'domains': ['canva.com', 'www.canva.com']},
        {'name': 'Grammarly', 'domains': ['grammarly.com', 'www.grammarly.com']},
        {'name': 'LastPass', 'domains': ['lastpass.com', 'www.lastpass.com']},
    ]
    
    adult = [
        {'name': 'Pornhub', 'domains': ['pornhub.com', 'www.pornhub.com', 'pornhubpremium.com']},
        {'name': 'OnlyFans', 'domains': ['onlyfans.com', 'www.onlyfans.com']},
        {'name': 'XVideos', 'domains': ['xvideos.com', 'www.xvideos.com', 'xvideos.red', 'www.xvideos.red']},
        {'name': 'xHamster', 'domains': ['xhamster.com', 'www.xhamster.com', 'xhamsterlive.com']},
        {'name': 'RedTube', 'domains': ['redtube.com', 'www.redtube.com']},
        {'name': 'YouPorn', 'domains': ['youporn.com', 'www.youporn.com']},
        {'name': 'Tube8', 'domains': ['tube8.com', 'www.tube8.com']},
        {'name': 'SpankWire', 'domains': ['spankwire.com', 'www.spankwire.com']},
        {'name': 'PornMD', 'domains': ['pornmd.com', 'www.pornmd.com']},
        {'name': 'Porn.com', 'domains': ['porn.com', 'www.porn.com']},
        {'name': 'Beeg', 'domains': ['beeg.com', 'www.beeg.com']},
        {'name': 'TnaFlix', 'domains': ['tnaflix.com', 'www.tnaflix.com']},
        {'name': '4Tube', 'domains': ['4tube.com', 'www.4tube.com']},
        {'name': 'DaftSex', 'domains': ['daftsex.com', 'www.daftsex.com']},
        {'name': 'Nuvid', 'domains': ['nuvid.com', 'www.nuvid.com']},
        {'name': 'PornOne', 'domains': ['pornone.com', 'www.pornone.com']},
        {'name': 'SunPorno', 'domains': ['sunporno.com', 'www.sunporno.com']},
        {'name': 'Vidz7', 'domains': ['vidz7.com', 'www.vidz7.com']},
        {'name': 'XXXBunker', 'domains': ['xxxbunker.com', 'www.xxxbunker.com']},
    ]
    
    gambling = [
        {'name': 'Bet365', 'domains': ['bet365.com', 'www.bet365.com']},
        {'name': 'DraftKings', 'domains': ['draftkings.com', 'www.draftkings.com']},
        {'name': 'FanDuel', 'domains': ['fanduel.com', 'www.fanduel.com']},
        {'name': 'PokerStars', 'domains': ['pokerstars.com', 'www.pokerstars.com', 'pokerstars.net']},
        {'name': '888 Casino', 'domains': ['888.com', 'www.888.com']},
        {'name': 'Betfair', 'domains': ['betfair.com', 'www.betfair.com']},
        {'name': 'William Hill', 'domains': ['williamhill.com', 'www.williamhill.com']},
        {'name': 'Ladbrokes', 'domains': ['ladbrokes.com', 'www.ladbrokes.com']},
        {'name': 'Coral', 'domains': ['coral.co.uk', 'www.coral.co.uk']},
        {'name': 'Paddy Power', 'domains': ['paddypower.com', 'www.paddypower.com']},
        {'name': 'Betway', 'domains': ['betway.com', 'www.betway.com']},
        {'name': 'Unibet', 'domains': ['unibet.com', 'www.unibet.com']},
        {'name': 'Bwin', 'domains': ['bwin.com', 'www.bwin.com']},
        {'name': 'BetMGM', 'domains': ['betmgm.com', 'www.betmgm.com']},
        {'name': 'Caesars', 'domains': ['caesars.com', 'www.caesars.com']},
        {'name': 'Bovada', 'domains': ['bovada.lv', 'www.bovada.lv']},
        {'name': 'Bodog', 'domains': ['bodog.com', 'www.bodog.com']},
        {'name': 'Intertops', 'domains': ['intertops.eu', 'www.intertops.eu']},
        {'name': 'BetOnline', 'domains': ['betonline.ag', 'www.betonline.ag']},
        {'name': 'MyBookie', 'domains': ['mybookie.ag', 'www.mybookie.ag']},
        {'name': 'SportsBetting', 'domains': ['sportsbetting.ag', 'www.sportsbetting.ag']},
        {'name': 'GTBets', 'domains': ['gtbets.eu', 'www.gtbets.eu']},
        {'name': 'BetUS', 'domains': ['betus.com', 'www.betus.com']},
        {'name': 'XBet', 'domains': ['xbet.ag', 'www.xbet.ag']},
        {'name': 'Slots.lv', 'domains': ['slots.lv', 'www.slots.lv']},
    ]
    
    vpn_proxy = [
        {'name': 'NordVPN', 'domains': ['nordvpn.com', 'www.nordvpn.com', 'nordaccount.com', 'nordcdn.com']},
        {'name': 'ExpressVPN', 'domains': ['expressvpn.com', 'www.expressvpn.com', 'expressvpn.net']},
        {'name': 'Surfshark', 'domains': ['surfshark.com', 'www.surfshark.com']},
        {'name': 'CyberGhost', 'domains': ['cyberghostvpn.com', 'www.cyberghostvpn.com', 'cyberghost.com']},
        {'name': 'Private Internet Access (PIA)', 'domains': ['privateinternetaccess.com', 'www.privateinternetaccess.com']},
        {'name': 'ProtonVPN', 'domains': ['protonvpn.com', 'www.protonvpn.com', 'proton.me']},
        {'name': 'IPVanish', 'domains': ['ipvanish.com', 'www.ipvanish.com']},
        {'name': 'Hotspot Shield', 'domains': ['hotspotshield.com', 'www.hotspotshield.com', 'anchorfree.com']},
        {'name': 'TunnelBear', 'domains': ['tunnelbear.com', 'www.tunnelbear.com']},
        {'name': 'Windscribe', 'domains': ['windscribe.com', 'www.windscribe.com']},
        {'name': 'VyprVPN', 'domains': ['vyprvpn.com', 'www.vyprvpn.com', 'goldenfrog.com']},
        {'name': 'PureVPN', 'domains': ['purevpn.com', 'www.purevpn.com']},
        {'name': 'StrongVPN', 'domains': ['strongvpn.com', 'www.strongvpn.com']},
        {'name': 'HideMyAss (HMA)', 'domains': ['hidemyass.com', 'www.hidemyass.com', 'hmavpn.com']},
        {'name': 'TorGuard', 'domains': ['torguard.net', 'www.torguard.net']},
        {'name': 'Mullvad', 'domains': ['mullvad.net', 'www.mullvad.net']},
        {'name': 'IVPN', 'domains': ['ivpn.net', 'www.ivpn.net']},
        {'name': 'Perfect Privacy', 'domains': ['perfect-privacy.com', 'www.perfect-privacy.com']},
        {'name': 'AirVPN', 'domains': ['airvpn.org', 'www.airvpn.org']},
        {'name': 'AzireVPN', 'domains': ['azirevpn.com', 'www.azirevpn.com']},
        {'name': 'CactusVPN', 'domains': ['cactusvpn.com', 'www.cactusvpn.com']},
        {'name': 'Celo VPN', 'domains': ['celovpn.com', 'www.celovpn.com']},
        {'name': 'CryptoStorm', 'domains': ['cryptostorm.is', 'www.cryptostorm.is']},
        {'name': 'FrootVPN', 'domains': ['frootvpn.com', 'www.frootvpn.com']},
        {'name': 'GhostPath', 'domains': ['ghostpath.com', 'www.ghostpath.com']},
        {'name': 'Hide.me', 'domains': ['hide.me', 'www.hide.me']},
        {'name': 'IronSocket', 'domains': ['ironsocket.com', 'www.ironsocket.com']},
        {'name': 'LiquidVPN', 'domains': ['liquidvpn.com', 'www.liquidvpn.com']},
        {'name': 'Mozilla VPN', 'domains': ['vpn.mozilla.org']},
        {'name': 'Norton Secure VPN', 'domains': ['norton.com', 'www.norton.com']},
        {'name': 'OVPN', 'domains': ['ovpn.com', 'www.ovpn.com']},
        {'name': 'PrivateVPN', 'domains': ['privatevpn.com', 'www.privatevpn.com']},
        {'name': 'ProXPN', 'domains': ['proxpn.com', 'www.proxpn.com']},
        {'name': 'SaferVPN', 'domains': ['safervpn.com', 'www.safervpn.com']},
        {'name': 'Seed4.Me', 'domains': ['seed4.me', 'www.seed4.me']},
        {'name': 'Speedify', 'domains': ['speedify.com', 'www.speedify.com']},
        {'name': 'Trust.Zone', 'domains': ['trust.zone', 'www.trust.zone']},
        {'name': 'VPN.ac', 'domains': ['vpn.ac', 'www.vpn.ac']},
        {'name': 'VPN Unlimited', 'domains': ['vpnunlimited.com', 'www.vpnunlimited.com', 'keepsolid.com', 'www.keepsolid.com']},
        {'name': 'VPN.ht', 'domains': ['vpn.ht', 'www.vpn.ht']},
        {'name': 'VPNHub', 'domains': ['vpnhub.com', 'www.vpnhub.com']},
        {'name': 'VPNLand', 'domains': ['vpnland.com', 'www.vpnland.com']},
        {'name': 'VPNMaster', 'domains': ['vpnmaster.com', 'www.vpnmaster.com']},
        {'name': 'VPNReactor', 'domains': ['vpnreactor.com', 'www.vpnreactor.com']},
        {'name': 'VPNShazam', 'domains': ['vpnshazam.com', 'www.vpnshazam.com']},
        {'name': 'VPNTunnel', 'domains': ['vpntunnel.com', 'www.vpntunnel.com']},
        {'name': 'ZenMate', 'domains': ['zenmate.com', 'www.zenmate.com']},
        {'name': 'ZorroVPN', 'domains': ['zorro-vpn.com', 'www.zorro-vpn.com']},
        {'name': 'Betternet', 'domains': ['betternet.co', 'www.betternet.co']},
        {'name': 'Opera VPN', 'domains': ['opera.com', 'www.opera.com']},
        {'name': 'Hola VPN', 'domains': ['hola.org', 'www.hola.org', 'hola.com']},
        {'name': 'Psiphon', 'domains': ['psiphon.ca', 'www.psiphon.ca', 'psiphon3.com']},
        {'name': 'Lantern', 'domains': ['getlantern.org', 'www.getlantern.org']},
        {'name': 'Tor Browser', 'domains': ['torproject.org', 'www.torproject.org', 'tor-browser.org']},
        {'name': 'Freegate', 'domains': ['freegate.net', 'www.freegate.net']},
        {'name': 'UltraSurf', 'domains': ['ultrasurf.us', 'www.ultrasurf.us']},
        {'name': 'VPN Gate', 'domains': ['vpngate.net', 'www.vpngate.net']},
        {'name': 'OpenVPN', 'domains': ['openvpn.net', 'www.openvpn.net', 'openvpn.org']},
        {'name': 'WireGuard', 'domains': ['wireguard.com', 'www.wireguard.com']},
        {'name': 'Shadowsocks', 'domains': ['shadowsocks.org', 'www.shadowsocks.org']},
        {'name': 'V2Ray', 'domains': ['v2ray.com', 'www.v2ray.com', 'v2fly.org']},
        {'name': 'Clash', 'domains': ['clash.dev', 'www.clash.dev']},
        {'name': 'Proxifier', 'domains': ['proxifier.com', 'www.proxifier.com']},
        {'name': 'ProxyCap', 'domains': ['proxycap.com', 'www.proxycap.com']},
        {'name': 'ProxyChains', 'domains': ['proxychains.org', 'www.proxychains.org']},
        {'name': 'ProxyScrape', 'domains': ['proxyscrape.com', 'www.proxyscrape.com']},
        {'name': 'ProxyRack', 'domains': ['proxyrack.com', 'www.proxyrack.com']},
        {'name': 'Smartproxy', 'domains': ['smartproxy.com', 'www.smartproxy.com']},
        {'name': 'Bright Data', 'domains': ['brightdata.com', 'www.brightdata.com', 'luminati.io']},
        {'name': 'Oxylabs', 'domains': ['oxylabs.io', 'www.oxylabs.io']},
        {'name': 'IPRoyal', 'domains': ['iproyal.com', 'www.iproyal.com']},
        {'name': 'Soax', 'domains': ['soax.com', 'www.soax.com']},
        {'name': 'NetNut', 'domains': ['netnut.io', 'www.netnut.io']},
        {'name': 'Webshare', 'domains': ['webshare.io', 'www.webshare.io']},
        {'name': 'Proxy-Cheap', 'domains': ['proxy-cheap.com', 'www.proxy-cheap.com']},
        {'name': 'MyPrivateProxy', 'domains': ['myprivateproxy.com', 'www.myprivateproxy.com']},
        {'name': 'ProxyMesh', 'domains': ['proxymesh.com', 'www.proxymesh.com']},
        {'name': 'Storm Proxies', 'domains': ['stormproxies.com', 'www.stormproxies.com']},
        {'name': 'Blazing SEO', 'domains': ['blazingseollc.com', 'www.blazingseollc.com']},
        {'name': 'RSocks', 'domains': ['rsocks.net', 'www.rsocks.net']},
        {'name': 'ProxySeller', 'domains': ['proxyseller.com', 'www.proxyseller.com']},
        {'name': 'BuyProxies', 'domains': ['buyproxies.org', 'www.buyproxies.org']},
        {'name': 'HighProxies', 'domains': ['highproxies.com', 'www.highproxies.com']},
        {'name': 'GeoSurf', 'domains': ['geosurf.com', 'www.geosurf.com']},
    ]
    
    bypass_tools = [
        {'name': 'ProxySite', 'domains': ['proxysite.com', 'www.proxysite.com']},
        {'name': 'Hide.me Proxy', 'domains': ['hide.me', 'www.hide.me']},
        {'name': 'KProxy', 'domains': ['kproxy.com', 'www.kproxy.com']},
        {'name': 'Hidester', 'domains': ['hidester.com', 'www.hidester.com']},
        {'name': '4everproxy', 'domains': ['4everproxy.com', 'www.4everproxy.com']},
        {'name': 'CroxyProxy', 'domains': ['croxyproxy.com', 'www.croxyproxy.com', 'croxyproxy.net']},
        {'name': 'Proxyium', 'domains': ['proxyium.com', 'www.proxyium.com']},
        {'name': 'Whoer.net', 'domains': ['whoer.net', 'www.whoer.net']},
        
        {'name': 'Unblock Games 66', 'domains': ['unblockgames66.com', 'www.unblockgames66.com']},
        {'name': 'Unblock Games 77', 'domains': ['unblockgames77.com', 'www.unblockgames77.com']},
        {'name': 'Unblock Games 99', 'domains': ['unblockgames99.com', 'www.unblockgames99.com']},
        {'name': 'Unblock Games 911', 'domains': ['unblockgames911.com', 'www.unblockgames911.com']},
    ]
    
    fake_news = [
        {'name': 'InfoWars', 'domains': ['infowars.com', 'www.infowars.com']},
        {'name': 'Natural News', 'domains': ['naturalnews.com', 'www.naturalnews.com']},
        {'name': 'The Gateway Pundit', 'domains': ['thegatewaypundit.com', 'www.thegatewaypundit.com']},
        {'name': 'WorldNetDaily (WND)', 'domains': ['wnd.com', 'www.wnd.com']},
        {'name': 'Your News Wire / NewsPunch', 'domains': ['yournewswire.com', 'www.yournewswire.com', 'newspunch.com', 'www.newspunch.com', 'thepeoplesvoice.tv', 'www.thepeoplesvoice.tv']},
        {'name': 'Liberty Writers News', 'domains': ['libertywritersnews.com', 'www.libertywritersnews.com']},
        {'name': 'Before It\'s News', 'domains': ['beforeitsnews.com', 'www.beforeitsnews.com']},
        {'name': 'Real Raw News', 'domains': ['realrawnews.com', 'www.realrawnews.com']},
        {'name': 'National Report', 'domains': ['nationalreport.net', 'www.nationalreport.net']},
        
        {'name': 'Activist Post', 'domains': ['activistpost.com', 'www.activistpost.com']},
        {'name': 'Collective Evolution', 'domains': ['collective-evolution.com', 'www.collective-evolution.com']},
        {'name': 'Disclose TV', 'domains': ['disclose.tv', 'www.disclose.tv']},
        {'name': 'Global Research', 'domains': ['globalresearch.ca', 'www.globalresearch.ca']},
        {'name': 'Veterans Today', 'domains': ['veteranstoday.com', 'www.veteranstoday.com']},
        {'name': 'Zero Hedge', 'domains': ['zerohedge.com', 'www.zerohedge.com']},
        {'name': '21st Century Wire', 'domains': ['21stcenturywire.com', 'www.21stcenturywire.com']},
        {'name': 'The Free Thought Project', 'domains': ['thefreethoughtproject.com', 'www.thefreethoughtproject.com']},
        {'name': 'Health Impact News', 'domains': ['healthimpactnews.com', 'www.healthimpactnews.com']},
        {'name': 'Intellihub', 'domains': ['intellihub.com', 'www.intellihub.com']},
        {'name': 'End Times Headlines', 'domains': ['endtimesheadlines.org', 'www.endtimesheadlines.org']},
        {'name': 'Freedom Outpost', 'domains': ['freedomoutpost.com', 'www.freedomoutpost.com']},
        {'name': 'WhatDoesItMean', 'domains': ['whatdoesitmean.com', 'www.whatdoesitmean.com']},
        {'name': 'True Pundit', 'domains': ['truepundit.com', 'www.truepundit.com']},
        {'name': 'DC Clothesline', 'domains': ['dcclothesline.com', 'www.dcclothesline.com']},
        {'name': 'Now8News', 'domains': ['now8news.com', 'www.now8news.com']},
        {'name': 'Political Ears', 'domains': ['politicalears.com', 'www.politicalears.com']},
        {'name': 'The Political Insider', 'domains': ['thepoliticalinsider.com', 'www.thepoliticalinsider.com']},
        {'name': 'TruthFeed', 'domains': ['truthfeed.com', 'www.truthfeed.com']},
        {'name': 'GotNews', 'domains': ['gotnews.com', 'www.gotnews.com']},
        {'name': 'Big League Politics', 'domains': ['bigleaguepolitics.com', 'www.bigleaguepolitics.com']},
        {'name': 'Conservative Treehouse', 'domains': ['theconservativetreehouse.com', 'www.theconservativetreehouse.com']},
        {'name': 'Eagle Rising', 'domains': ['eaglerising.com', 'www.eaglerising.com']},
        {'name': 'GOP The Daily Dose', 'domains': ['gopthedailydose.com', 'www.gopthedailydose.com']},
        {'name': 'Gulag Bound', 'domains': ['gulagbound.com', 'www.gulagbound.com']},
        {'name': 'The Right Stuff', 'domains': ['therightstuff.biz', 'www.therightstuff.biz']},
        {'name': 'Unz Review', 'domains': ['unz.com', 'www.unz.com']},
        {'name': 'VDARE', 'domains': ['vdare.com', 'www.vdare.com']},
        {'name': 'Bare Naked Islam', 'domains': ['barenakedislam.com', 'www.barenakedislam.com']},
        {'name': 'Jihad Watch', 'domains': ['jihadwatch.org', 'www.jihadwatch.org']},
        {'name': 'FrontPage Magazine', 'domains': ['frontpagemag.com', 'www.frontpagemag.com']},
        {'name': 'Renew America', 'domains': ['renewamerica.com', 'www.renewamerica.com']},
        {'name': 'Right Wing News', 'domains': ['rightwingnews.com', 'www.rightwingnews.com']},
        {'name': 'LifeSiteNews', 'domains': ['lifesitenews.com', 'www.lifesitenews.com']},
        {'name': 'The Epoch Times', 'domains': ['theepochtimes.com', 'www.theepochtimes.com']},
        {'name': 'The New American', 'domains': ['thenewamerican.com', 'www.thenewamerican.com']},
        {'name': 'American Thinker', 'domains': ['americanthinker.com', 'www.americanthinker.com']},
        {'name': 'Western Journal', 'domains': ['westernjournal.com', 'www.westernjournal.com']},
        {'name': 'US Uncut', 'domains': ['usuncut.com', 'www.usuncut.com']},
    ]
    
    tracking = [
        {'name': 'Google Analytics', 'domains': ['google-analytics.com', 'www.google-analytics.com', 'analytics.google.com', 'googletagmanager.com', 'www.googletagmanager.com']},
        {'name': 'Google Tag Manager', 'domains': ['googletagmanager.com', 'www.googletagmanager.com']},
        {'name': 'Google AdSense', 'domains': ['googleadsense.com', 'www.googleadsense.com', 'googlesyndication.com', 'www.googlesyndication.com']},
        {'name': 'Google DoubleClick', 'domains': ['doubleclick.net', 'www.doubleclick.net', 'doubleclick.com', 'www.doubleclick.com']},
        {'name': 'Google AdWords', 'domains': ['googleadservices.com', 'www.googleadservices.com']},
        {'name': 'Google Marketing Platform', 'domains': ['marketingplatform.google.com']},
        {'name': 'Google Firebase Analytics', 'domains': ['firebase.google.com', 'firebaseio.com']},
        {'name': 'Google Optimize', 'domains': ['optimize.google.com']},
        
        {'name': 'Facebook Pixel', 'domains': ['connect.facebook.net', 'www.connect.facebook.net']},
        {'name': 'Facebook Analytics', 'domains': ['analytics.facebook.com']},
        {'name': 'Facebook Connect', 'domains': ['connect.facebook.com', 'www.connect.facebook.com']},
        {'name': 'Meta Pixel', 'domains': ['facebook.com', 'meta.com']},
        
        {'name': 'Adobe Analytics', 'domains': ['omniture.com', 'www.omniture.com', 'sc.omtrdc.net']},
        {'name': 'Adobe Audience Manager', 'domains': ['demdex.net', 'www.demdex.net']},
        {'name': 'Adobe Experience Cloud', 'domains': ['adobedtm.com', 'www.adobedtm.com']},
        {'name': 'Adobe Target', 'domains': ['tt.omtrdc.net']},
        
        {'name': 'Microsoft Clarity', 'domains': ['clarity.ms', 'www.clarity.ms']},
        {'name': 'Microsoft Advertising', 'domains': ['bingads.microsoft.com']},
        
        {'name': 'Mixpanel', 'domains': ['mixpanel.com', 'www.mixpanel.com']},
        {'name': 'Segment', 'domains': ['segment.com', 'www.segment.com', 'segment.io', 'www.segment.io']},
        {'name': 'Amplitude', 'domains': ['amplitude.com', 'www.amplitude.com']},
        {'name': 'Heap Analytics', 'domains': ['heap.io', 'www.heap.io']},
        {'name': 'Hotjar', 'domains': ['hotjar.com', 'www.hotjar.com']},
        {'name': 'FullStory', 'domains': ['fullstory.com', 'www.fullstory.com']},
        {'name': 'LogRocket', 'domains': ['logrocket.com', 'www.logrocket.com']},
        {'name': 'Sentry', 'domains': ['sentry.io', 'www.sentry.io']},
        {'name': 'New Relic', 'domains': ['newrelic.com', 'www.newrelic.com']},
        {'name': 'Datadog', 'domains': ['datadoghq.com', 'www.datadoghq.com']},
        {'name': 'Matomo', 'domains': ['matomo.org', 'www.matomo.org']},
        {'name': 'Plausible Analytics', 'domains': ['plausible.io', 'www.plausible.io']},
        
        {'name': 'Amazon Associates', 'domains': ['associates.amazon.com', 'amazon-adsystem.com', 'www.amazon-adsystem.com']},
        {'name': 'Criteo', 'domains': ['criteo.com', 'www.criteo.com']},
        {'name': 'The Trade Desk', 'domains': ['thetradedesk.com', 'www.thetradedesk.com']},
        {'name': 'MediaMath', 'domains': ['mediamath.com', 'www.mediamath.com']},
        {'name': 'AppNexus', 'domains': ['appnexus.com', 'www.appnexus.com']},
        {'name': 'OpenX', 'domains': ['openx.com', 'www.openx.com']},
        {'name': 'Rubicon Project', 'domains': ['rubiconproject.com', 'www.rubiconproject.com']},
        {'name': 'PubMatic', 'domains': ['pubmatic.com', 'www.pubmatic.com']},
        {'name': 'Index Exchange', 'domains': ['indexexchange.com', 'www.indexexchange.com']},
        {'name': 'Sovrn', 'domains': ['sovrn.com', 'www.sovrn.com']},
        {'name': '33Across', 'domains': ['33across.com', 'www.33across.com']},
        {'name': 'AdRoll', 'domains': ['adroll.com', 'www.adroll.com']},
        {'name': 'Lotame', 'domains': ['lotame.com', 'www.lotame.com']},
        {'name': 'Quantcast', 'domains': ['quantcast.com', 'www.quantcast.com']},
        {'name': 'ScoreCard Research', 'domains': ['scorecardresearch.com', 'www.scorecardresearch.com']},
        {'name': 'Nielsen', 'domains': ['nielsen.com', 'www.nielsen.com']},
        {'name': 'ComScore', 'domains': ['comscore.com', 'www.comscore.com']},
        {'name': 'Chartbeat', 'domains': ['chartbeat.com', 'www.chartbeat.com']},
        {'name': 'Parse.ly', 'domains': ['parsely.com', 'www.parsely.com']},
        
        {'name': 'Acxiom', 'domains': ['acxiom.com', 'www.acxiom.com']},
        {'name': 'Experian', 'domains': ['experian.com', 'www.experian.com']},
        {'name': 'Equifax', 'domains': ['equifax.com', 'www.equifax.com']},
        {'name': 'TransUnion', 'domains': ['transunion.com', 'www.transunion.com']},
        {'name': 'Epsilon', 'domains': ['epsilon.com', 'www.epsilon.com']},
        {'name': 'Oracle Data Cloud', 'domains': ['oracle.com', 'bluekai.com', 'www.bluekai.com']},
        
        {'name': 'Twitter Analytics', 'domains': ['analytics.twitter.com', 'ads.twitter.com']},
        {'name': 'LinkedIn Insight Tag', 'domains': ['snap.licdn.com']},
        {'name': 'Pinterest Tag', 'domains': ['analytics.pinterest.com']},
        {'name': 'TikTok Pixel', 'domains': ['analytics.tiktok.com', 'ads.tiktok.com']},
        {'name': 'Snapchat Pixel', 'domains': ['ads.snapchat.com']},
        
        {'name': 'Mailchimp', 'domains': ['mailchimp.com', 'www.mailchimp.com']},
        {'name': 'Constant Contact', 'domains': ['constantcontact.com', 'www.constantcontact.com']},
        {'name': 'SendGrid', 'domains': ['sendgrid.com', 'www.sendgrid.com']},
        {'name': 'Campaign Monitor', 'domains': ['campaignmonitor.com', 'www.campaignmonitor.com']},
        
        {'name': 'Crazy Egg', 'domains': ['crazyegg.com', 'www.crazyegg.com']},
        {'name': 'Mouseflow', 'domains': ['mouseflow.com', 'www.mouseflow.com']},
        {'name': 'Smartlook', 'domains': ['smartlook.com', 'www.smartlook.com']},
        {'name': 'Lucky Orange', 'domains': ['luckyorange.com', 'www.luckyorange.com']},
        
        {'name': 'Optimizely', 'domains': ['optimizely.com', 'www.optimizely.com']},
        {'name': 'VWO', 'domains': ['vwo.com', 'www.vwo.com']},
        
        {'name': 'Yandex Metrica', 'domains': ['metrica.yandex.com', 'mc.yandex.ru']},
        {'name': 'Baidu Analytics', 'domains': ['hm.baidu.com', 'tongji.baidu.com']},
    ]
    
    government_surveillance = [
        {'name': 'NSA (National Security Agency)', 'domains': ['nsa.gov', 'www.nsa.gov']},
        {'name': 'CIA (Central Intelligence Agency)', 'domains': ['cia.gov', 'www.cia.gov']},
        {'name': 'FBI (Federal Bureau of Investigation)', 'domains': ['fbi.gov', 'www.fbi.gov']},
        {'name': 'DHS (Department of Homeland Security)', 'domains': ['dhs.gov', 'www.dhs.gov', 'cisa.gov', 'www.cisa.gov']},
        {'name': 'DEA (Drug Enforcement Administration)', 'domains': ['dea.gov', 'www.dea.gov']},
        {'name': 'ATF (Bureau of Alcohol, Tobacco, Firearms)', 'domains': ['atf.gov', 'www.atf.gov']},
        {'name': 'US Secret Service', 'domains': ['secretservice.gov', 'www.secretservice.gov']},
        {'name': 'NRO (National Reconnaissance Office)', 'domains': ['nro.gov', 'www.nro.gov']},
        {'name': 'NGA (National Geospatial-Intelligence Agency)', 'domains': ['nga.mil', 'www.nga.mil']},
        {'name': 'DIA (Defense Intelligence Agency)', 'domains': ['dia.mil', 'www.dia.mil']},
        {'name': 'US Cyber Command', 'domains': ['cybercom.mil', 'www.cybercom.mil']},
        {'name': 'US Marshals Service', 'domains': ['usmarshals.gov', 'www.usmarshals.gov']},
        {'name': 'ICE (Immigration and Customs Enforcement)', 'domains': ['ice.gov', 'www.ice.gov']},
        {'name': 'CBP (Customs and Border Protection)', 'domains': ['cbp.gov', 'www.cbp.gov']},
        {'name': 'TSA (Transportation Security Administration)', 'domains': ['tsa.gov', 'www.tsa.gov']},
        
        {'name': 'GCHQ (Government Communications Headquarters)', 'domains': ['gchq.gov.uk', 'www.gchq.gov.uk']},
        {'name': 'MI5 (Security Service)', 'domains': ['mi5.gov.uk', 'www.mi5.gov.uk']},
        {'name': 'MI6 (Secret Intelligence Service)', 'domains': ['sis.gov.uk', 'www.sis.gov.uk']},
        {'name': 'NCA (National Crime Agency)', 'domains': ['nationalcrimeagency.gov.uk', 'www.nationalcrimeagency.gov.uk']},
        
        {'name': 'CSIS (Canadian Security Intelligence Service)', 'domains': ['csis.gc.ca', 'www.csis.gc.ca']},
        {'name': 'CSE (Communications Security Establishment)', 'domains': ['cse-cst.gc.ca', 'www.cse-cst.gc.ca']},
        {'name': 'RCMP (Royal Canadian Mounted Police)', 'domains': ['rcmp-grc.gc.ca', 'www.rcmp-grc.gc.ca']},
        
        {'name': 'ASIO (Australian Security Intelligence Organisation)', 'domains': ['asio.gov.au', 'www.asio.gov.au']},
        {'name': 'ASIS (Australian Secret Intelligence Service)', 'domains': ['asis.gov.au', 'www.asis.gov.au']},
        {'name': 'ASD (Australian Signals Directorate)', 'domains': ['asd.gov.au', 'www.asd.gov.au']},
        
        {'name': 'BND (German Federal Intelligence Service)', 'domains': ['bnd.bund.de', 'www.bnd.bund.de']},
        {'name': 'DGSE (French External Security Directorate)', 'domains': ['defense.gouv.fr', 'www.defense.gouv.fr']},
        {'name': 'AIVD (Dutch General Intelligence and Security Service)', 'domains': ['aivd.nl', 'www.aivd.nl']},
        {'name': 'SIS (Swedish Security Service)', 'domains': ['sakerhetspolisen.se', 'www.sakerhetspolisen.se']},
        
        {'name': 'Mossad (Israeli Intelligence)', 'domains': ['mossad.gov.il', 'www.mossad.gov.il']},
        {'name': 'FSB (Russian Federal Security Service)', 'domains': ['fsb.ru', 'www.fsb.ru']},
        {'name': 'MSS (Chinese Ministry of State Security)', 'domains': ['mss.gov.cn', 'www.mss.gov.cn']},
        
        {'name': 'Interpol', 'domains': ['interpol.int', 'www.interpol.int']},
        {'name': 'Europol', 'domains': ['europol.europa.eu', 'www.europol.europa.eu']},
        {'name': 'Frontex', 'domains': ['frontex.europa.eu', 'www.frontex.europa.eu']},
        
        {'name': 'Qaznet Trust Network (Kazakhstan Surveillance CA)', 'domains': ['qaznet.kz', 'www.qaznet.kz']},
        {'name': 'Root CA of Kazakhstan', 'domains': ['rootca.kz', 'www.rootca.kz']},
    ]
    
    cryptocurrency = [
        {'name': 'Coinbase', 'domains': ['coinbase.com', 'www.coinbase.com', 'pro.coinbase.com', 'exchange.coinbase.com', 'commerce.coinbase.com']},
        {'name': 'Binance', 'domains': ['binance.com', 'www.binance.com', 'binance.us', 'www.binance.us', 'binance.org', 'www.binance.org']},
        {'name': 'Kraken', 'domains': ['kraken.com', 'www.kraken.com']},
        {'name': 'Gemini', 'domains': ['gemini.com', 'www.gemini.com']},
        {'name': 'Bitfinex', 'domains': ['bitfinex.com', 'www.bitfinex.com']},
        {'name': 'Bitstamp', 'domains': ['bitstamp.net', 'www.bitstamp.net']},
        {'name': 'Huobi', 'domains': ['huobi.com', 'www.huobi.com', 'huobi.pro', 'www.huobi.pro']},
        {'name': 'OKX (OKEx)', 'domains': ['okx.com', 'www.okx.com', 'okex.com', 'www.okex.com']},
        {'name': 'KuCoin', 'domains': ['kucoin.com', 'www.kucoin.com']},
        {'name': 'Bybit', 'domains': ['bybit.com', 'www.bybit.com']},
        {'name': 'Crypto.com', 'domains': ['crypto.com', 'www.crypto.com', 'crypto.com', 'exchange.crypto.com']},
        {'name': 'FTX', 'domains': ['ftx.com', 'www.ftx.com', 'ftx.us', 'www.ftx.us']},
        {'name': 'Gate.io', 'domains': ['gate.io', 'www.gate.io']},
        {'name': 'BitMEX', 'domains': ['bitmex.com', 'www.bitmex.com']},
        {'name': 'Deribit', 'domains': ['deribit.com', 'www.deribit.com']},
        {'name': 'Poloniex', 'domains': ['poloniex.com', 'www.poloniex.com']},
        {'name': 'Bittrex', 'domains': ['bittrex.com', 'www.bittrex.com']},
        {'name': 'Upbit', 'domains': ['upbit.com', 'www.upbit.com']},
        {'name': 'Bithumb', 'domains': ['bithumb.com', 'www.bithumb.com']},
        {'name': 'Coinone', 'domains': ['coinone.co.kr', 'www.coinone.co.kr']},
        {'name': 'Korbit', 'domains': ['korbit.co.kr', 'www.korbit.co.kr']},
        {'name': 'BitFlyer', 'domains': ['bitflyer.com', 'www.bitflyer.com', 'bitflyer.jp', 'www.bitflyer.jp']},
        {'name': 'Liquid', 'domains': ['liquid.com', 'www.liquid.com']},
        {'name': 'Bitpanda', 'domains': ['bitpanda.com', 'www.bitpanda.com']},
        {'name': 'eToro', 'domains': ['etoro.com', 'www.etoro.com']},
        {'name': 'Robinhood Crypto', 'domains': ['robinhood.com', 'www.robinhood.com']},
        {'name': 'Cash App (Bitcoin)', 'domains': ['cash.app', 'www.cash.app', 'square.com', 'www.square.com']},
        {'name': 'PayPal Crypto', 'domains': ['paypal.com', 'www.paypal.com']},
        {'name': 'Venmo Crypto', 'domains': ['venmo.com', 'www.venmo.com']},
        {'name': 'Revolut Crypto', 'domains': ['revolut.com', 'www.revolut.com']},
        {'name': 'Nexo', 'domains': ['nexo.io', 'www.nexo.io']},
        {'name': 'BlockFi', 'domains': ['blockfi.com', 'www.blockfi.com']},
        {'name': 'Celsius', 'domains': ['celsius.network', 'www.celsius.network']},
        {'name': 'Voyager', 'domains': ['investvoyager.com', 'www.investvoyager.com']},
        {'name': 'Coinbase Wallet', 'domains': ['wallet.coinbase.com', 'www.wallet.coinbase.com']},
        {'name': 'MetaMask', 'domains': ['metamask.io', 'www.metamask.io']},
        {'name': 'Trust Wallet', 'domains': ['trustwallet.com', 'www.trustwallet.com']},
        {'name': 'Exodus', 'domains': ['exodus.com', 'www.exodus.com']},
        {'name': 'Electrum', 'domains': ['electrum.org', 'www.electrum.org']},
        {'name': 'Mycelium', 'domains': ['mycelium.com', 'www.mycelium.com']},
        {'name': 'Ledger', 'domains': ['ledger.com', 'www.ledger.com', 'ledger.io', 'www.ledger.io']},
        {'name': 'Trezor', 'domains': ['trezor.io', 'www.trezor.io']},
        {'name': 'KeepKey', 'domains': ['keepkey.com', 'www.keepkey.com']},
        {'name': 'Atomic Wallet', 'domains': ['atomicwallet.io', 'www.atomicwallet.io']},
        {'name': 'Jaxx', 'domains': ['jaxx.io', 'www.jaxx.io']},
        {'name': 'Coinomi', 'domains': ['coinomi.com', 'www.coinomi.com']},
        {'name': 'BRD Wallet', 'domains': ['brd.com', 'www.brd.com']},
        {'name': 'Blockchain.info', 'domains': ['blockchain.com', 'www.blockchain.com', 'blockchain.info', 'www.blockchain.info']},
        {'name': 'BitPay', 'domains': ['bitpay.com', 'www.bitpay.com']},
        {'name': 'Coinbase Commerce', 'domains': ['commerce.coinbase.com', 'www.commerce.coinbase.com']},
        {'name': 'BitPay Wallet', 'domains': ['bitpay.com', 'www.bitpay.com']},
        {'name': 'Uniswap', 'domains': ['uniswap.org', 'www.uniswap.org', 'app.uniswap.org']},
        {'name': 'SushiSwap', 'domains': ['sushi.com', 'www.sushi.com']},
        {'name': 'PancakeSwap', 'domains': ['pancakeswap.finance', 'www.pancakeswap.finance']},
        {'name': '1inch', 'domains': ['1inch.io', 'www.1inch.io', '1inch.exchange', 'www.1inch.exchange']},
        {'name': 'Curve Finance', 'domains': ['curve.fi', 'www.curve.fi']},
        {'name': 'Aave', 'domains': ['aave.com', 'www.aave.com']},
        {'name': 'Compound', 'domains': ['compound.finance', 'www.compound.finance']},
        {'name': 'MakerDAO', 'domains': ['makerdao.com', 'www.makerdao.com']},
        {'name': 'Yearn Finance', 'domains': ['yearn.finance', 'www.yearn.finance']},
        {'name': 'OpenSea', 'domains': ['opensea.io', 'www.opensea.io']},
        {'name': 'Rarible', 'domains': ['rarible.com', 'www.rarible.com']},
        {'name': 'Foundation', 'domains': ['foundation.app', 'www.foundation.app']},
        {'name': 'SuperRare', 'domains': ['superrare.com', 'www.superrare.com']},
        {'name': 'Nifty Gateway', 'domains': ['niftygateway.com', 'www.niftygateway.com']},
        {'name': 'MakersPlace', 'domains': ['makersplace.com', 'www.makersplace.com']},
        {'name': 'KnownOrigin', 'domains': ['knownorigin.io', 'www.knownorigin.io']},
        {'name': 'Async Art', 'domains': ['async.art', 'www.async.art']},
        {'name': 'F2Pool', 'domains': ['f2pool.com', 'www.f2pool.com']},
        {'name': 'Antpool', 'domains': ['antpool.com', 'www.antpool.com']},
        {'name': 'ViaBTC', 'domains': ['viabtc.com', 'www.viabtc.com']},
        {'name': 'Slush Pool', 'domains': ['slushpool.com', 'www.slushpool.com']},
        {'name': 'BTC.com Pool', 'domains': ['btc.com', 'www.btc.com']},
        {'name': 'Poolin', 'domains': ['poolin.com', 'www.poolin.com']},
        {'name': 'Binance Pool', 'domains': ['pool.binance.com', 'www.pool.binance.com']},
        {'name': 'NiceHash', 'domains': ['nicehash.com', 'www.nicehash.com']},
        {'name': 'Mining Pool Hub', 'domains': ['miningpoolhub.com', 'www.miningpoolhub.com']},
        {'name': 'Ethermine', 'domains': ['ethermine.org', 'www.ethermine.org']},
        {'name': 'SparkPool', 'domains': ['sparkpool.com', 'www.sparkpool.com']},
        {'name': 'Flexpool', 'domains': ['flexpool.io', 'www.flexpool.io']},
        {'name': '2Miners', 'domains': ['2miners.com', 'www.2miners.com']},
        {'name': 'Hiveon Pool', 'domains': ['hiveon.net', 'www.hiveon.net']},
        {'name': 'Coinbase Pro', 'domains': ['pro.coinbase.com', 'www.pro.coinbase.com']},
        {'name': 'Coinbase Advanced Trade', 'domains': ['advanced.coinbase.com', 'www.advanced.coinbase.com']},
        {'name': 'Coinbase Prime', 'domains': ['prime.coinbase.com', 'www.prime.coinbase.com']},
        {'name': 'Coinbase Custody', 'domains': ['custody.coinbase.com', 'www.custody.coinbase.com']},
        {'name': 'Coinbase NFT', 'domains': ['nft.coinbase.com', 'www.nft.coinbase.com']},
        {'name': 'Coinbase Cloud', 'domains': ['cloud.coinbase.com', 'www.cloud.coinbase.com']},
        {'name': 'Binance DEX', 'domains': ['binance.org', 'www.binance.org']},
        {'name': 'Binance NFT', 'domains': ['nft.binance.com', 'www.nft.binance.com']},
        {'name': 'Binance Launchpad', 'domains': ['launchpad.binance.com', 'www.launchpad.binance.com']},
        {'name': 'Binance Earn', 'domains': ['binance.com', 'www.binance.com']},
        {'name': 'Kraken Futures', 'domains': ['futures.kraken.com', 'www.futures.kraken.com']},
        {'name': 'Kraken Pro', 'domains': ['pro.kraken.com', 'www.pro.kraken.com']},
        {'name': 'Gemini Custody', 'domains': ['custody.gemini.com', 'www.custody.gemini.com']},
    ]
    
    category_map = {
        'social_media': 'Social Media',
        'streaming': 'Streaming',
        'gaming': 'Gaming',
        'shopping': 'Shopping',
        'news': 'News',
        'productivity': 'Productivity',
        'adult': 'Adult',
        'gambling': 'Gambling',
        'vpn_proxy': 'VPN/Proxy',
        'bypass_tools': 'Bypass Tools',
        'fake_news': 'Fake News',
        'tracking': 'Tracking',
        'government_surveillance': 'Government/Surveillance',
        'cryptocurrency': 'Cryptocurrency'
    }
    
    for service_list, cat_name in [(social_media, 'Social Media'), (streaming, 'Streaming'), 
                                    (gaming, 'Gaming'), (shopping, 'Shopping'), 
                                    (news, 'News'), (productivity, 'Productivity'),
                                    (adult, 'Adult'), (gambling, 'Gambling'), 
                                    (vpn_proxy, 'VPN/Proxy'), (bypass_tools, 'Bypass Tools'),
                                    (fake_news, 'Fake News'), (tracking, 'Tracking'),
                                    (government_surveillance, 'Government/Surveillance'),
                                    (cryptocurrency, 'Cryptocurrency')]:
        for service in service_list:
            services[str(service_id)] = {**service, 'category': cat_name}
            service_id += 1
    
    return services


def get_service_domains_for_service(service_key):
    """Get domains for a specific service"""
    services = get_individual_services()
    if service_key in services:
        service = services[service_key]
        return {domain: '0.0.0.0' for domain in service['domains']}
    return {}


def show_category_menu():
    """Show category selection menu"""
    clear_screen()
    categories = [
        ('Social Media', 'Social Media'),
        ('Streaming', 'Streaming'),
        ('Gaming', 'Gaming'),
        ('Shopping', 'Shopping'),
        ('News', 'News'),
        ('Productivity', 'Productivity'),
        ('Adult', 'Adult'),
        ('Gambling', 'Gambling'),
        ('VPN/Proxy', 'VPN/Proxy'),
        ('Bypass Tools', 'Bypass Tools'),
        ('Fake News', 'Fake News'),
        ('Tracking', 'Tracking'),
        ('Government/Surveillance', 'Government/Surveillance'),
        ('Cryptocurrency', 'Cryptocurrency'),
    ]
    
    menu_lines = []
    menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  Block Services - Categories{Colors.ENDC}")
    menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
    menu_lines.append("")
    
    key_colors = [Colors.BRIGHT_GREEN, Colors.BRIGHT_BLUE, Colors.BRIGHT_CYAN, Colors.BRIGHT_YELLOW, 
                 Colors.BRIGHT_MAGENTA, Colors.BRIGHT_RED]
    
    for i, (cat_name, cat_key) in enumerate(categories, 1):
        key_color = key_colors[(i - 1) % len(key_colors)]
        menu_lines.append(f"{key_color}{Colors.BOLD}  {i}.{Colors.ENDC}{Colors.WHITE} {cat_name}{Colors.ENDC}")
    
    menu_lines.append("")
    menu_lines.append("")
    menu_lines.append(f"{Colors.BRIGHT_RED}{Colors.BOLD}  0.{Colors.ENDC}{Colors.BRIGHT_WHITE} Back{Colors.ENDC}")
    
    print()
    print_boxed_menu(menu_lines, width=70)
    print()
    
    return categories


def show_services_in_category(category_name):
    """Show services within a specific category"""
    services = get_individual_services()
    
    category_services = []
    for key, service in services.items():
        if service['category'] == category_name:
            category_services.append((key, service))
    
    category_services.sort(key=lambda x: int(x[0]))
    
    while True:
        clear_screen()
        menu_lines = []
        menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  {category_name} Services{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
        menu_lines.append("")
        
        key_colors = [Colors.BRIGHT_GREEN, Colors.BRIGHT_BLUE, Colors.BRIGHT_CYAN, Colors.BRIGHT_YELLOW, 
                     Colors.BRIGHT_MAGENTA, Colors.BRIGHT_RED]
        
        service_key_map = {}
        
        for i, (service_key, service) in enumerate(category_services, 1):
            is_enabled = False
            hosts_path = get_hosts_file_path()
            if os.path.exists(hosts_path):
                try:
                    service_domains = get_service_domains_for_service(service_key)
                    if service_domains:
                        with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                            hosts_content = f.read()
                            for domain in service_domains.keys():
                                if (f"0.0.0.0 {domain}\n" in hosts_content or 
                                    f"0.0.0.0 {domain}\r" in hosts_content or
                                    f"127.0.0.1 {domain}\n" in hosts_content or
                                    f"127.0.0.1 {domain}\r" in hosts_content or
                                    f"0.0.0.0 {domain} " in hosts_content or
                                    f"127.0.0.1 {domain} " in hosts_content):
                                    is_enabled = True
                                    break
                except:
                    pass
            
            service_key_map[str(i)] = service_key
            
            key_color = key_colors[(i - 1) % len(key_colors)]
            status_text = f"{Colors.BRIGHT_GREEN}{Colors.BOLD}[ON]{Colors.ENDC}" if is_enabled else f"{Colors.BRIGHT_RED}{Colors.BOLD}[OFF]{Colors.ENDC}"
            menu_lines.append(f"{key_color}{Colors.BOLD}  {i}.{Colors.ENDC}{Colors.WHITE} {service['name']} {status_text}{Colors.ENDC}")
        
        menu_lines.append("")
        menu_lines.append(f"{Colors.BRIGHT_YELLOW}{Colors.BOLD}  ALL.{Colors.ENDC}{Colors.WHITE} Toggle All Services{Colors.ENDC}")
        menu_lines.append("")
        menu_lines.append("")
        menu_lines.append(f"{Colors.BRIGHT_RED}{Colors.BOLD}  0.{Colors.ENDC}{Colors.BRIGHT_WHITE} Back{Colors.ENDC}")
        
        print()
        print_boxed_menu(menu_lines, width=70)
        print()
        
        choice = input(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}Enter your choice: {Colors.ENDC}").strip().lower()
        
        if choice == '0':
            return True
        
        elif choice == 'all':
            hosts_path = get_hosts_file_path()
            
            all_enabled = []
            all_disabled = []
            
            for service_key, service in category_services:
                is_enabled = False
                if os.path.exists(hosts_path):
                    try:
                        service_domains = get_service_domains_for_service(service_key)
                        if service_domains:
                            with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                                hosts_content = f.read()
                                for domain in service_domains.keys():
                                    if (f"0.0.0.0 {domain}\n" in hosts_content or 
                                        f"0.0.0.0 {domain}\r" in hosts_content or
                                        f"127.0.0.1 {domain}\n" in hosts_content or
                                        f"127.0.0.1 {domain}\r" in hosts_content or
                                        f"0.0.0.0 {domain} " in hosts_content or
                                        f"127.0.0.1 {domain} " in hosts_content):
                                        is_enabled = True
                                        break
                    except:
                        pass
                
                if is_enabled:
                    all_enabled.append((service_key, service))
                else:
                    all_disabled.append((service_key, service))
            
            if len(all_enabled) == len(category_services):
                new_state = False
                action_text = "disabled"
            else:
                new_state = True
                action_text = "enabled"
            
            print_info(f"{'Disabling' if not new_state else 'Enabling'} all {category_name} services...")
            success_count = 0
            fail_count = 0
            
            all_service_domains = {}
            for service_key, service in category_services:
                service_domains = get_service_domains_for_service(service_key)
                if service_domains:
                    all_service_domains.update(service_domains)
            
            if all_service_domains:
                service_names = ', '.join([s['name'] for _, s in category_services[:3]])
                if len(category_services) > 3:
                    service_names += f" and {len(category_services) - 3} more"
                if apply_service_changes(hosts_path, all_service_domains, new_state, f"All {category_name} services"):
                    success_count = len(category_services)
                    print_success(f"All {category_name} services {action_text} ({success_count} services)")
                else:
                    fail_count = len(category_services)
                    print_warning(f"Failed to update {fail_count} service(s)")
            else:
                print_warning("No domains found for services in this category")
            
            input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
            continue
        
        elif choice in service_key_map:
            service_key = service_key_map[choice]
            service = services[service_key]
            
            service_domains = get_service_domains_for_service(service_key)
            
            if not service_domains:
                print_warning(f"Could not retrieve domains for {service['name']}")
                input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
                continue
            
            hosts_path = get_hosts_file_path()
            current_state = False
            if os.path.exists(hosts_path):
                try:
                    with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                        hosts_content = f.read()
                        for domain in service_domains.keys():
                            if (f"0.0.0.0 {domain}\n" in hosts_content or 
                                f"0.0.0.0 {domain}\r" in hosts_content or
                                f"127.0.0.1 {domain}\n" in hosts_content or
                                f"127.0.0.1 {domain}\r" in hosts_content or
                                f"0.0.0.0 {domain} " in hosts_content or
                                f"127.0.0.1 {domain} " in hosts_content):
                                current_state = True
                                break
                except Exception as e:
                    current_state = False
            
            new_state = not current_state
            
            if apply_service_changes(hosts_path, service_domains, new_state, service['name']):
                status = "enabled" if new_state else "disabled"
                domain_count = len(service_domains)
                action = "added" if new_state else "removed"
                print_success(f"{service['name']} blocking {status} ({domain_count} domains {action})")
            else:
                print_error(f"Failed to update hosts file for {service['name']} blocking")
            
            input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
        
        else:
            print_error("Invalid choice. Please try again.")
            input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")


def manage_service_blocking():
    """Manage individual service blocking (Facebook, Instagram, TikTok, etc.)"""
    global HOSTS_SOURCES
    
    while True:
        categories = show_category_menu()
        choice = input(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}Enter your choice: {Colors.ENDC}").strip().lower()
        
        if choice == '0':
            return True
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(categories):
                category_name = categories[choice_num - 1][1]
                show_services_in_category(category_name)
            else:
                print_error("Invalid choice. Please try again.")
                input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
        except ValueError:
            print_error("Invalid choice. Please try again.")
            input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
    
    while True:
        menu_lines = []
        menu_lines.append(f"{Colors.BRIGHT_MAGENTA}{Colors.BOLD}  XusGuard - Universal Platform Adblock{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_WHITE}{Colors.BOLD}  Block Services{Colors.ENDC}")
        menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
        menu_lines.append("")
        
        service_status = {}
        key_colors = [Colors.BRIGHT_GREEN, Colors.BRIGHT_BLUE, Colors.BRIGHT_CYAN, Colors.BRIGHT_YELLOW, 
                     Colors.BRIGHT_MAGENTA]
        
        for cat_key, category in sorted(service_categories.items()):
            matching_sources = []
            for source_key, source in HOSTS_SOURCES.items():
                source_name = source.get('name', '').lower()
                if any(pattern.lower() in source_name for pattern in category['source_patterns']):
                    matching_sources.append((source_key, source))
            
            is_enabled = False
            if matching_sources:
                hosts_path = get_hosts_file_path()
                if os.path.exists(hosts_path):
                    try:
                        service_domains = get_service_domains(matching_sources)
                        if service_domains:
                            with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                                hosts_content = f.read()
                                for domain in service_domains.keys():
                                    if (f"0.0.0.0 {domain}\n" in hosts_content or 
                                        f"0.0.0.0 {domain}\r" in hosts_content or
                                        f"127.0.0.1 {domain}\n" in hosts_content or
                                        f"127.0.0.1 {domain}\r" in hosts_content or
                                        f"0.0.0.0 {domain} " in hosts_content or
                                        f"127.0.0.1 {domain} " in hosts_content):
                                        is_enabled = True
                                        break
                    except Exception as e:
                        is_enabled = any(source.get('enabled', False) for _, source in matching_sources)
                else:
                    is_enabled = any(source.get('enabled', False) for _, source in matching_sources)
            
            service_status[cat_key] = is_enabled
            
            key_color = key_colors[(int(cat_key) - 1) % len(key_colors)]
            status_text = f"{Colors.BRIGHT_GREEN}{Colors.BOLD}[ON]{Colors.ENDC}" if is_enabled else f"{Colors.BRIGHT_RED}{Colors.BOLD}[OFF]{Colors.ENDC}"
            menu_lines.append(f"{key_color}{Colors.BOLD}  {cat_key}.{Colors.ENDC}{Colors.WHITE} {category['name']} {status_text}{Colors.ENDC}")
            menu_lines.append(f"{Colors.BRIGHT_CYAN}    {category['description']}{Colors.ENDC}")
            if matching_sources:
                menu_lines.append(f"{Colors.WHITE}    Sources: {', '.join([s[1]['name'] for s in matching_sources])}{Colors.ENDC}")
            menu_lines.append("")
        
        menu_lines.append(f"{Colors.BRIGHT_CYAN}  {'─' * 50}{Colors.ENDC}")
        menu_lines.append("")
        menu_lines.append("")
        menu_lines.append(f"{Colors.BRIGHT_RED}{Colors.BOLD}  0.{Colors.ENDC}{Colors.BRIGHT_WHITE} Back{Colors.ENDC}")
        
        print()
        print_boxed_menu(menu_lines, width=70)
        print()
        
        choice = input(f"{Colors.BRIGHT_CYAN}{Colors.BOLD}Enter your choice: {Colors.ENDC}").strip().lower()
        
        if choice == '0':
            if save_sources(HOSTS_SOURCES):
                print_success("Service blocking settings saved")
            return True
        
        elif choice in service_categories:
            category = service_categories[choice]
            matching_sources = []
            for source_key, source in HOSTS_SOURCES.items():
                source_name = source.get('name', '').lower()
                if any(pattern.lower() in source_name for pattern in category['source_patterns']):
                    matching_sources.append((source_key, source))
            
            if not matching_sources:
                print_warning(f"No sources found for {category['name']} blocking")
                input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
                continue
            
            print_info(f"Loading domains for {category['name']} blocking...")
            service_domains = get_service_domains(matching_sources)
            
            if not service_domains:
                print_warning(f"Could not retrieve domains for {category['name']} blocking")
                input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
                continue
            
            hosts_path = get_hosts_file_path()
            current_state = False
            if os.path.exists(hosts_path):
                try:
                    with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                        hosts_content = f.read()
                        for domain in service_domains.keys():
                            if (f"0.0.0.0 {domain}\n" in hosts_content or 
                                f"0.0.0.0 {domain}\r" in hosts_content or
                                f"127.0.0.1 {domain}\n" in hosts_content or
                                f"127.0.0.1 {domain}\r" in hosts_content or
                                f"0.0.0.0 {domain} " in hosts_content or
                                f"127.0.0.1 {domain} " in hosts_content):
                                current_state = True
                                break
                except Exception as e:
                    current_state = any(source.get('enabled', False) for _, source in matching_sources)
            else:
                current_state = any(source.get('enabled', False) for _, source in matching_sources)
            
            new_state = not current_state
            
            if apply_service_changes(hosts_path, service_domains, new_state, category['name']):
                for source_key, source in matching_sources:
                    HOSTS_SOURCES[source_key]['enabled'] = new_state
                
                status = "enabled" if new_state else "disabled"
                domain_count = len(service_domains)
                action = "added" if new_state else "removed"
                print_success(f"{category['name']} blocking {status} ({domain_count} domains {action})")
            else:
                print_error(f"Failed to update hosts file for {category['name']} blocking")
            
            input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")
        
        else:
            print_error("Invalid choice. Please try again.")
            input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")


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


def manage_domain_redirects():
    """Manage domain redirects (redirect domains to specific IP addresses)"""
    hosts_path = get_hosts_file_path()
    
    system_domains = {'localhost', 'broadcasthost', 'local'}
    system_ips = {'127.0.0.1', '0.0.0.0', '::1', '255.255.255.255', 'fe80::1%lo0'}
    
    while True:
        clear_screen()
        
        redirects = {}
        if os.path.exists(hosts_path):
            try:
                with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split()
                            if len(parts) >= 2:
                                ip = parts[0]
                                domain = parts[1].lower()
                                if (ip not in ['0.0.0.0', '127.0.0.1'] and 
                                    domain not in system_domains and 
                                    ip not in system_ips):
                                    redirects[domain] = ip
            except Exception as e:
                print_error(f"Failed to read hosts file: {e}")
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
            filtered_redirects = {d: ip for d, ip in redirects.items() 
                                 if d.lower() not in system_domains and ip not in system_ips}
            redirect_list = sorted(filtered_redirects.items())
            
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
            lines = f.read().splitlines()
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
            print_info(f"   curl -sSL https://raw.githubusercontent.com/EngineXus-dev/XusGuard/refs/tags/v{VERSION}/uniadblock.py -o uniadblock.py")
            print_info("   Elevate only when writing the system hosts file.")
            print_info("\n2. Use the installer script:")
            print_info(f"   curl -sSL https://raw.githubusercontent.com/EngineXus-dev/XusGuard/refs/tags/v{VERSION}/install.sh | bash")
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
        print_info(f"   curl -sSL https://raw.githubusercontent.com/EngineXus-dev/XusGuard/refs/tags/v{VERSION}/uniadblock.py -o uniadblock.py")
        print_info("   Elevate only when writing the system hosts file.")
        print_info("\n2. Use the installer script:")
        print_info(f"   curl -sSL https://raw.githubusercontent.com/EngineXus-dev/XusGuard/refs/tags/v{VERSION}/install.sh | bash")
        sys.exit(1)
    
    HOSTS_SOURCES = load_sources()
    
    backup_dir = get_backup_directory()
    system = platform.system()
    default_filename = f"default_hosts_{system.lower()}.txt"
    default_path = backup_dir / default_filename
    if not default_path.exists():
        save_default_hosts_file()
    
    if not check_root():
        print_warning("Not running with administrator/root privileges.")
        print_warning("You may need elevated privileges to modify the hosts file.")
        response = safe_input(f"{Colors.WARNING}Continue anyway? (y/n): {Colors.ENDC}").strip().lower()
        if response != 'y':
            print_info("Exiting...")
            sys.exit(0)
    
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

