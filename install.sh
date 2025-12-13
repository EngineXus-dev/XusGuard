#!/bin/bash
# Uni-Adblock - One-Command Installer & Runner
# Downloads and runs Uni-Adblock from GitHub

# Don't exit on error - we handle errors manually
set +e

SCRIPT_URL="https://raw.githubusercontent.com/InfoSecREDD/Uni-Adblock/refs/tags/v1.1.2/uniadblock.py"
SOURCES_URL="https://raw.githubusercontent.com/InfoSecREDD/Uni-Adblock/refs/tags/v1.1.2/sources.json"

echo "🚀 Uni-Adblock - One-Command Installer"
echo "========================================"
echo ""

# Function to check Python version
check_python_version() {
    local python_cmd="$1"
    if command -v "$python_cmd" &> /dev/null; then
        local version=$("$python_cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        local major=$(echo "$version" | cut -d. -f1)
        if [ "$major" -ge 3 ]; then
            return 0
        fi
    fi
    return 1
}

# Function to install Python 3
install_python3() {
    echo "📦 Python 3 not found. Attempting to install..."
    
    # Detect OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "🍎 Detected macOS"
        if command -v brew &> /dev/null; then
            echo "📦 Installing Python 3 via Homebrew..."
            brew install python3 || {
                echo "❌ Failed to install Python 3 via Homebrew"
                echo "   Please install manually: brew install python3"
                return 1
            }
        else
            echo "⚠️  Homebrew not found. Please install Python 3 manually:"
            echo "   1. Install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            echo "   2. Install Python: brew install python3"
            echo "   Or download from: https://www.python.org/downloads/"
            return 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux - detect distribution
        if [ -f /etc/debian_version ]; then
            # Debian/Ubuntu
            echo "🐧 Detected Debian/Ubuntu Linux"
            echo "📦 Installing Python 3 via apt..."
            if [ "$EUID" -eq 0 ]; then
                apt-get update && apt-get install -y python3 python3-pip
            else
                sudo apt-get update && sudo apt-get install -y python3 python3-pip || {
                    echo "❌ Failed to install Python 3. Please run with sudo or install manually:"
                    echo "   sudo apt-get update && sudo apt-get install -y python3 python3-pip"
                    return 1
                }
            fi
        elif [ -f /etc/redhat-release ]; then
            # RedHat/CentOS/Fedora
            echo "🐧 Detected RedHat/CentOS/Fedora Linux"
            if command -v dnf &> /dev/null; then
                echo "📦 Installing Python 3 via dnf..."
                if [ "$EUID" -eq 0 ]; then
                    dnf install -y python3 python3-pip
                else
                    sudo dnf install -y python3 python3-pip || {
                        echo "❌ Failed to install Python 3. Please run with sudo or install manually:"
                        echo "   sudo dnf install -y python3 python3-pip"
                        return 1
                    }
                fi
            elif command -v yum &> /dev/null; then
                echo "📦 Installing Python 3 via yum..."
                if [ "$EUID" -eq 0 ]; then
                    yum install -y python3 python3-pip
                else
                    sudo yum install -y python3 python3-pip || {
                        echo "❌ Failed to install Python 3. Please run with sudo or install manually:"
                        echo "   sudo yum install -y python3 python3-pip"
                        return 1
                    }
                fi
            fi
        elif [ -f /etc/arch-release ]; then
            # Arch Linux
            echo "🐧 Detected Arch Linux"
            echo "📦 Installing Python 3 via pacman..."
            if [ "$EUID" -eq 0 ]; then
                pacman -Sy --noconfirm python python-pip
            else
                sudo pacman -Sy --noconfirm python python-pip || {
                    echo "❌ Failed to install Python 3. Please run with sudo or install manually:"
                    echo "   sudo pacman -Sy --noconfirm python python-pip"
                    return 1
                }
            fi
        elif command -v zypper &> /dev/null; then
            # openSUSE
            echo "🐧 Detected openSUSE"
            echo "📦 Installing Python 3 via zypper..."
            if [ "$EUID" -eq 0 ]; then
                zypper install -y python3 python3-pip
            else
                sudo zypper install -y python3 python3-pip || {
                    echo "❌ Failed to install Python 3. Please run with sudo or install manually:"
                    echo "   sudo zypper install -y python3 python3-pip"
                    return 1
                }
            fi
        else
            echo "⚠️  Unsupported Linux distribution. Please install Python 3 manually:"
            echo "   Visit: https://www.python.org/downloads/"
            return 1
        fi
    else
        echo "⚠️  Unsupported operating system. Please install Python 3 manually:"
        echo "   Visit: https://www.python.org/downloads/"
        return 1
    fi
    
    # Verify installation
    if check_python_version python3; then
        echo "✓ Python 3 installed successfully"
        return 0
    else
        echo "❌ Python 3 installation completed but verification failed"
        return 1
    fi
}

# Check for Python 3
PYTHON_CMD=""
if check_python_version python3; then
    PYTHON_CMD="python3"
elif check_python_version python; then
    PYTHON_CMD="python"
else
    # Try to install Python 3
    if ! install_python3; then
        echo ""
        echo "❌ Python 3 is required but could not be installed automatically"
        echo "   Please install Python 3 manually and run this script again"
        echo "   Visit: https://www.python.org/downloads/"
        exit 1
    fi
    # Check again after installation
    if check_python_version python3; then
        PYTHON_CMD="python3"
    elif check_python_version python; then
        PYTHON_CMD="python"
    else
        echo "❌ Python 3 installation failed"
        exit 1
    fi
fi

echo "✓ Found Python: $($PYTHON_CMD --version)"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo "📥 Downloading Uni-Adblock..."
set -e  # Re-enable exit on error for downloads
curl -sSL "$SCRIPT_URL" -o "$TEMP_DIR/uniadblock.py" || {
    echo "❌ Failed to download uniadblock.py"
    exit 1
}
set +e  # Disable again for rest of script

echo "📥 Downloading sources.json..."
curl -sSL "$SOURCES_URL" -o "$TEMP_DIR/sources.json" || {
    echo "⚠️  Warning: Failed to download sources.json (script will create default)"
}

# Make script executable
chmod +x "$TEMP_DIR/uniadblock.py"

echo "✓ Download complete"
echo ""

# Check if running as root/sudo
# Ensure stdin is connected to terminal if available (for interactive input)
# When piping curl to bash, stdin is consumed, so we try to use /dev/tty if available
if [ -c /dev/tty ] 2>/dev/null; then
    # Try to use /dev/tty for interactive input
    if [ "$EUID" -eq 0 ]; then
        echo "🔐 Running with root privileges"
        "$PYTHON_CMD" "$TEMP_DIR/uniadblock.py" < /dev/tty
    else
        echo "⚠️  Note: You may need sudo privileges to modify hosts file"
        echo "   If you encounter permission errors, run with sudo:"
        echo "   sudo bash -c \"\$(curl -sSL https://raw.githubusercontent.com/InfoSecREDD/Uni-Adblock/refs/tags/v1.1.2/install.sh)\""
        echo ""
        "$PYTHON_CMD" "$TEMP_DIR/uniadblock.py" < /dev/tty
    fi
else
    # No TTY available, run normally (Python script will handle non-interactive mode gracefully)
    if [ "$EUID" -eq 0 ]; then
        echo "🔐 Running with root privileges"
        "$PYTHON_CMD" "$TEMP_DIR/uniadblock.py"
    else
        echo "⚠️  Note: You may need sudo privileges to modify hosts file"
        echo "   If you encounter permission errors, run with sudo:"
        echo "   sudo bash -c \"\$(curl -sSL https://raw.githubusercontent.com/InfoSecREDD/Uni-Adblock/refs/tags/v1.1.2/install.sh)\""
        echo ""
        "$PYTHON_CMD" "$TEMP_DIR/uniadblock.py"
    fi
fi
