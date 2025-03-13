#!/bin/bash
# Conference Presentation System - Deployment Scripts
# A collection of shell scripts for deploying and testing the system on various platforms

###########################################
# Linux Installation Script (install_linux.sh)
###########################################
cat > install_linux.sh << 'EOL'
#!/bin/bash
# Conference Presentation System - Linux Installation Script

# Exit on error
set -e

# Script variables
INSTALL_DIR="$HOME/conference_system"
VENV_DIR="$INSTALL_DIR/venv"
PYTHON_CMD="python3"
PYTHON_MIN_VERSION="3.8"
MOSQUITTO_CONF="/etc/mosquitto/mosquitto.conf"
BOLD="\033[1m"
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
NC="\033[0m" # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Banner
echo -e "${BOLD}Conference Presentation System - Linux Installation${NC}"
echo "=============================================="
echo

# Check Python version
echo -e "${BOLD}Checking Python version...${NC}"
if ! command_exists $PYTHON_CMD; then
    echo -e "${RED}Python not found. Please install Python $PYTHON_MIN_VERSION or higher.${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ $(echo "$PYTHON_VERSION < $PYTHON_MIN_VERSION" | bc -l) -eq 1 ]]; then
    echo -e "${RED}Python version $PYTHON_VERSION is too old. Please install Python $PYTHON_MIN_VERSION or higher.${NC}"
    exit 1
fi
echo -e "${GREEN}Python version $PYTHON_VERSION found.${NC}"

# Check for pip
echo -e "${BOLD}Checking pip...${NC}"
if ! command_exists pip3; then
    echo -e "${YELLOW}pip not found. Installing pip...${NC}"
    sudo apt-get update
    sudo apt-get install -y python3-pip
fi
echo -e "${GREEN}pip found.${NC}"

# Install system dependencies
echo -e "${BOLD}Installing system dependencies...${NC}"
sudo apt-get update
sudo apt-get install -y \
    python3-venv \
    python3-dev \
    mosquitto \
    mosquitto-clients \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    ffmpeg \
    v4l-utils

# Configure Mosquitto MQTT broker
echo -e "${BOLD}Configuring Mosquitto MQTT broker...${NC}"
if [ -f "$MOSQUITTO_CONF" ]; then
    # Check if listener is already configured
    if ! grep -q "^listener" "$MOSQUITTO_CONF"; then
        echo -e "${YELLOW}Adding listener configuration to Mosquitto...${NC}"
        # Backup the original config
        sudo cp "$MOSQUITTO_CONF" "${MOSQUITTO_CONF}.bak"
        # Add listener config
        echo -e "\n# Added by Conference System Installer\nlistener 1883\nallow_anonymous true" | sudo tee -a "$MOSQUITTO_CONF" > /dev/null
    fi
    # Restart Mosquitto
    sudo systemctl restart mosquitto
    echo -e "${GREEN}Mosquitto MQTT broker configured.${NC}"
else
    echo -e "${YELLOW}Mosquitto config not found at $MOSQUITTO_CONF. You may need to configure it manually.${NC}"
fi

# Create installation directory
echo -e "${BOLD}Creating installation directory...${NC}"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Create and activate virtual environment
echo -e "${BOLD}Setting up Python virtual environment...${NC}"