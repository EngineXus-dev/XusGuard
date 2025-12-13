# Uni-Adblock

**Version 1.1.1**

A cross-platform ad blocker for macOS, Linux, and Windows that blocks ads by modifying your system's hosts file. The tool downloads and merges hosts files from multiple trusted sources to create a comprehensive ad-blocking solution.

**Created by: InfoSecREDD**

## Features

- 🌍 **Cross-platform**: Works on macOS, Linux, and Windows
- 📦 **Single File**: Everything in one self-contained Python script
- 🔧 **Auto-Venv**: Automatically creates and manages its own virtual environment
- 🎯 **Interactive Menu**: Easy-to-use command-line interface
- 🔄 **Multiple Sources**: Downloads from 25+ trusted ad-blocking hosts file sources
- 🔀 **Smart Merging**: Automatically deduplicates and merges entries from multiple sources
- 💾 **Backup & Restore**: Automatically backs up your original hosts file with timestamps
- 🛡️ **Safe**: Only modifies hosts file with proper backups
- 📊 **Statistics**: Real-time statistics showing blocked domains and source status
- 🎛️ **Source Management**: Enable/disable sources, add custom sources via JSON
- 🚫 **Service Blocking**: Block individual services (Social Media, Streaming, Gaming, etc.)
- 🔀 **Domain Redirects**: Redirect domains to specific IP addresses or other domains
- 🌐 **DNS Flush**: Built-in DNS cache flushing for all platforms
- 📁 **Individual Source Files**: Each source saved as its own file for easy management

## Requirements

- Python 3.6 or higher *(will be automatically installed if missing)*
- Administrator/Root privileges (to modify hosts file)
- Internet connection (for downloading hosts files and Python if needed)

## Installation

### One-Command Installation (Recommended)

Run Uni-Adblock directly from GitHub with a single command - no manual downloads needed!

**✨ Automatic Python Installation:** The installer scripts will automatically detect and install Python 3 if it's missing on your system!

**📦 Single-File Installers:** The installers automatically download from GitHub and handle Python installation!

**macOS/Linux (One-liner):**
```bash
curl -sSL https://raw.githubusercontent.com/InfoSecREDD/Uni-Adblock/refs/tags/v1.1.1/install.sh | bash
```

**macOS/Linux (Download installer first):**
```bash
curl -sSL https://raw.githubusercontent.com/InfoSecREDD/Uni-Adblock/refs/tags/v1.1.1/install.sh -o install.sh
chmod +x install.sh
sudo ./install.sh
```

**macOS/Linux (Ultra-simple - direct run):**
```bash
curl -sSL https://raw.githubusercontent.com/InfoSecREDD/Uni-Adblock/refs/tags/v1.1.1/uniadblock.py | sudo python3
```
*(Note: This method won't download sources.json, but the script will create a default one)*

**Windows:**
```cmd
powershell -Command "Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/InfoSecREDD/Uni-Adblock/refs/tags/v1.1.1/install.bat' -OutFile 'install.bat'; .\install.bat"
```

Or download `install.bat` and double-click it (Run as Administrator).


### Manual Installation

Simply download the `uniadblock.py` file and `sources.json` file - that's all you need!

## Usage

### Quick Start

**macOS/Linux:**
```bash
chmod +x uniadblock.py
sudo python3 uniadblock.py
```

**Windows:**
```cmd
python uniadblock.py
```
(Run as Administrator)

The script will automatically:
- Create a virtual environment in a `venv` folder (if needed)
- Install required dependencies (`certifi` for SSL certificate handling)
- Present you with an interactive menu

**Note:** The script requires administrator/root privileges to modify the hosts file.

### Main Menu Options

1. **Install AdBlock** - Download and install hosts files from enabled sources
2. **Update AdBlock Hosts Files** - Download and cache hosts files from enabled sources
3. **View current hosts file** - Display the current hosts file contents
4. **Backup current hosts file** - Create a timestamped backup of your hosts file
5. **Restore from backup** - Restore hosts file from a previous backup
6. **Restore OS default hosts file** - Restore the original OS default hosts file
7. **Manage sources (Enable/Disable)** - Enable or disable specific ad-blocking sources
8. **View available sources** - List all available hosts file sources
9. **Add new source** - Add a custom hosts file source
10. **Remove source** - Remove a custom hosts file source
11. **Flush DNS cache** - Clear DNS cache (works on macOS, Linux, and Windows)
12. **Block services** - Block individual services by category (Social Media, Streaming, Gaming, etc.)
13. **Redirect domains** - Redirect domains to specific IP addresses or other domains
0. **Exit** - Exit the program

## Source Management

Sources are managed via `sources.json`. The script comes with 24+ pre-configured sources including:

- Steven Black's Unified Hosts
- AdAway Default Blocklist
- OISD Blocklist
- Goodbye Ads
- 1Hosts
- AdGuard DNS
- Disconnect.me
- And many more...

You can:
- Enable/disable sources via the menu
- Add custom sources with your own URLs
- Remove sources you don't need
- All sources are stored in JSON format for easy editing

## Service Blocking

The script includes extensive service blocking capabilities organized by category:

- **Social Media** (30+ services): Facebook, Instagram, Twitter/X, TikTok, Snapchat, LinkedIn, Reddit, Discord, WhatsApp, Telegram, YouTube, Twitch, Tumblr, VK, WeChat, Signal, Mastodon, Truth Social, Parler, Gab, MeWe, Clubhouse, and more
- **Streaming** (25+ services): Netflix, Disney+, Hulu, Amazon Prime Video, HBO Max, Spotify, Apple Music, SoundCloud, Pandora, Deezer, Tidal, Apple TV+, Paramount+, Peacock, Crunchyroll, Funimation, Vudu, FuboTV, Sling TV, YouTube TV, Pluto TV, Tubi, Crackle, Vimeo, Dailymotion, and more
- **Gaming** (30+ services): Steam, Epic Games, Xbox Live, PlayStation Network, Nintendo, Roblox, Minecraft, EA Origin, Battle.net, Ubisoft, GOG, Riot Games, Valorant, Fortnite, PUBG, Call of Duty, Apex Legends, Overwatch, World of Warcraft, Counter-Strike, Dota 2, Team Fortress 2, Among Us, Fall Guys, Genshin Impact, GTA Online, FIFA, Madden NFL, NBA 2K, and more
- **Shopping** (25+ services): Amazon, eBay, AliExpress, Wish, Etsy, Walmart, Target, Best Buy, Costco, Home Depot, Lowe's, Macy's, Nordstrom, Zappos, ASOS, Shein, Temu, Wayfair, Overstock, Newegg, Shopify, WooCommerce, Magento, BigCommerce, Square, and more
- **News** (30+ services): CNN, BBC, Fox News, The New York Times, The Guardian, The Washington Post, USA Today, Wall Street Journal, Reuters, Associated Press, NPR, ABC News, CBS News, NBC News, MSNBC, CNBC, Bloomberg, Forbes, Time, Newsweek, The Economist, Politico, The Hill, Breitbart, Daily Mail, The Telegraph, The Times, Al Jazeera, RT (Russia Today), Xinhua, and more
- **Productivity** (25+ services): Google Drive, Dropbox, OneDrive, iCloud, Zoom, Microsoft Teams, Slack, Microsoft Office, Google Workspace, Notion, Evernote, Trello, Asana, Monday.com, Basecamp, Jira, Confluence, GitHub, GitLab, Bitbucket, Figma, Adobe Creative Cloud, Canva, Grammarly, LastPass, and more
- **Adult** (20+ services): Pornhub, OnlyFans, XVideos, xHamster, RedTube, YouPorn, Tube8, SpankWire, PornMD, Beeg, TnaFlix, 4Tube, and more
- **Gambling** (25+ services): Bet365, DraftKings, FanDuel, PokerStars, 888 Casino, Betfair, William Hill, Ladbrokes, Coral, Paddy Power, Betway, Unibet, Bwin, BetMGM, Caesars, Bovada, Bodog, Intertops, BetOnline, MyBookie, SportsBetting, GTBets, BetUS, XBet, Slots.lv, and more
- **VPN/Proxy** (50+ services): NordVPN, ExpressVPN, Surfshark, CyberGhost, Private Internet Access (PIA), ProtonVPN, IPVanish, Hotspot Shield, TunnelBear, Windscribe, VyprVPN, PureVPN, Mullvad, IVPN, Tor Browser, OpenVPN, WireGuard, Shadowsocks, V2Ray, Clash, ProxyScrape, ProxyRack, Smartproxy, Bright Data, Oxylabs, IPRoyal, and more
- **Bypass Tools** (10+ services): ProxySite, Hide.me Proxy, KProxy, Hidester, 4everproxy, CroxyProxy, Proxyium, Whoer.net, Unblock Games 66, Unblock Games 77, Unblock Games 99, Unblock Games 911, and more
- **Fake News** (40+ verified misinformation outlets): InfoWars, Natural News, The Gateway Pundit, WorldNetDaily (WND), Your News Wire / NewsPunch, Liberty Writers News, Before It's News, Real Raw News, National Report, Activist Post, Collective Evolution, Disclose TV, Global Research, Veterans Today, Zero Hedge, 21st Century Wire, The Free Thought Project, Health Impact News, Intellihub, End Times Headlines, Freedom Outpost, WhatDoesItMean, True Pundit, DC Clothesline, Now8News, Political Ears, The Political Insider, TruthFeed, GotNews, Big League Politics, Conservative Treehouse, Eagle Rising, GOP The Daily Dose, Gulag Bound, The Right Stuff, Unz Review, VDARE, Bare Naked Islam, Jihad Watch, FrontPage Magazine, Renew America, Right Wing News, LifeSiteNews, The Epoch Times, The New American, American Thinker, Western Journal, US Uncut, and more
- **Tracking** (60+ services): Google Analytics, Google Tag Manager, Google AdSense, Google DoubleClick, Google AdWords, Google Marketing Platform, Google Firebase Analytics, Google Optimize, Facebook Pixel, Facebook Analytics, Meta Pixel, Adobe Analytics, Adobe Audience Manager, Adobe Experience Cloud, Adobe Target, Microsoft Clarity, Microsoft Advertising, Mixpanel, Segment, Amplitude, Heap Analytics, Hotjar, FullStory, LogRocket, Sentry, New Relic, Datadog, Matomo, Plausible Analytics, Amazon Associates, Criteo, The Trade Desk, MediaMath, AppNexus, OpenX, Rubicon Project, PubMatic, Index Exchange, Sovrn, AdRoll, Lotame, Quantcast, ScoreCard Research, Nielsen, ComScore, Chartbeat, Parse.ly, Acxiom, Experian, Equifax, TransUnion, Epsilon, Oracle Data Cloud, Twitter Analytics, LinkedIn Insight Tag, Pinterest Tag, TikTok Pixel, Snapchat Pixel, Mailchimp, Constant Contact, SendGrid, Campaign Monitor, Crazy Egg, Mouseflow, Smartlook, Lucky Orange, Optimizely, VWO, Yandex Metrica, Baidu Analytics, and more
- **Government/Surveillance** (30+ entities): NSA (National Security Agency), CIA (Central Intelligence Agency), FBI (Federal Bureau of Investigation), DHS (Department of Homeland Security), CISA, DEA (Drug Enforcement Administration), ATF (Bureau of Alcohol, Tobacco, Firearms), US Secret Service, NRO (National Reconnaissance Office), NGA (National Geospatial-Intelligence Agency), DIA (Defense Intelligence Agency), US Cyber Command, US Marshals Service, ICE (Immigration and Customs Enforcement), CBP (Customs and Border Protection), TSA (Transportation Security Administration), GCHQ (Government Communications Headquarters), MI5 (Security Service), MI6 (Secret Intelligence Service), NCA (National Crime Agency), CSIS (Canadian Security Intelligence Service), CSE (Communications Security Establishment), RCMP (Royal Canadian Mounted Police), ASIO (Australian Security Intelligence Organisation), ASIS (Australian Secret Intelligence Service), ASD (Australian Signals Directorate), BND (German Federal Intelligence Service), DGSE (French External Security Directorate), AIVD (Dutch General Intelligence and Security Service), SIS (Swedish Security Service), Mossad (Israeli Intelligence), FSB (Russian Federal Security Service), MSS (Chinese Ministry of State Security), Interpol, Europol, Frontex, Qaznet Trust Network (Kazakhstan Surveillance CA), Root CA of Kazakhstan, and more

  > **Note**: The Government/Surveillance category is included primarily for informational and educational purposes. The likelihood of these agencies using their public-facing domains to access your personal computer is extremely low, as intelligence operations typically employ more sophisticated methods and infrastructure. This category serves as a reference for those interested in understanding surveillance infrastructure rather than providing practical security benefits. Aka - For the LOL's.

Each service can be individually toggled on or off, and each category includes an "All" option to toggle all services in that category at once.

## Domain Redirects

You can redirect domains to specific IP addresses or other domains:

- Redirect a domain to an IP address (e.g., `example.com` → `192.168.1.1`)
- Redirect a domain to another domain (e.g., `example.com` → `target.com`) - the script will automatically resolve the target domain to its IP address
- System entries (localhost, broadcasthost) are automatically hidden from the redirect list

## How It Works

1. The script downloads hosts files from enabled sources
2. Each source is saved as its own file in `hosts_sources/` directory
3. Parses and extracts valid ad-blocking entries (127.0.0.1 and 0.0.0.0)
4. Merges entries from all enabled sources and deduplicates
5. Creates a backup of your current hosts file (timestamped)
6. Installs the merged hosts file to your system
7. Provides DNS cache flushing for immediate effect

## Statistics

The main menu displays real-time statistics:

- **Domains to be Blocked**: Number of unique domains from enabled cached sources
- **Current blocked domains**: Number of unique domains currently in your hosts file
- **Enabled sources**: Number of sources currently enabled
- **Cached sources**: Number of source files downloaded and cached

## Backup Files

The script automatically creates timestamped backups of your hosts file in the `hosts_backups/` directory. Backup files are named with the format: `hosts_YYYYMMDD_HHMMSS.adblock_backup`

You can restore from any backup using option 5 in the menu.

## Source Files

Downloaded hosts files are saved individually in the `hosts_sources/` directory. Each source is saved with a simplified filename (e.g., `steven_black_s_unified_hosts.hosts`). This allows you to:

- See which sources are cached
- Manually review individual source files
- Track which sources have been downloaded

## DNS Cache Flushing

The script includes a built-in DNS cache flush option (menu option 11) that works on all platforms:

- **macOS**: Uses `dscacheutil -flushcache` and `killall -HUP mDNSResponder`
- **Linux**: Uses `systemd-resolve --flush-caches` or `service network-manager restart`
- **Windows**: Uses `ipconfig /flushdns`

## Security Note

This script requires administrator/root privileges to modify the system hosts file. Always review the code before running with elevated privileges.

## Troubleshooting

### Permission Denied Error

Make sure you're running the script with administrator/root privileges:
- **macOS/Linux**: Use `sudo python3 uniadblock.py`
- **Windows**: Right-click and "Run as Administrator"

### Virtual Environment Issues

If you encounter issues with the virtual environment, simply delete the `venv` folder and run the script again. It will recreate it automatically.

### DNS Not Updating

After installing, use the built-in DNS flush option (menu option 11). Some applications may need to be restarted.

### SSL Certificate Errors

The script automatically handles SSL certificate issues by attempting to install `certifi` and falling back to unverified connections if needed. This ensures downloads work even with certificate problems.

### Sources Not Downloading

- Check your internet connection
- Verify the source URL is accessible
- Some sources may be temporarily unavailable
- Check the script output for specific error messages

## File Structure

```
adblock/
├── uniadblock.py       # Main script (single file)
├── sources.json        # Source configuration (JSON)
├── install.sh          # One-command installer (macOS/Linux) - downloads from GitHub, auto-installs Python
├── install.bat         # One-command installer (Windows) - downloads from GitHub, auto-installs Python
├── venv/               # Virtual environment (auto-created)
├── hosts_backups/      # Timestamped backups (auto-created)
└── hosts_sources/     # Individual source files (auto-created)
```

## License

This project is provided as-is for educational and personal use.

## Disclaimer

This tool modifies your system hosts file. While it creates backups, use at your own risk. Some websites may break if they rely on blocked domains for functionality. Always test after installation and restore from backup if needed.
