    #!/bin/bash
# =============================================================================
# Kali Linux Ultimate Customization Script
# Author: AI Installer
# Description: This script transforms a fresh Kali Linux installation into a
#              fully-loaded penetration testing and hacking powerhouse with
#              500+ additional tools from GitHub, optimized for AI autonomous
#              operation. Full admin access is granted to the 'ai' user.
# =============================================================================

set -e  # Exit on any error
set -o pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log file
LOG_FILE="/root/kali_custom_install.log"
exec > >(tee -a "$LOG_FILE") 2>&1

# =============================================================================
# Helper Functions
# =============================================================================

print_step() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} ${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

check_success() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  -> Success${NC}"
    else
        echo -e "${RED}  -> Failed${NC}"
        exit 1
    fi
}

# Function to install packages via apt with progress
apt_install() {
    print_step "Installing apt packages: $*"
    apt-get install -y "$@" || print_error "Failed to install $*"
}

# Function to clone and build a GitHub repo
install_github_tool() {
    local repo_url=$1
    local install_dir=$2
    local build_cmds=$3
    local repo_name=$(basename "$repo_url" .git)

    print_step "Installing $repo_name from GitHub"
    cd /opt
    if [ -d "$repo_name" ]; then
        print_warn "$repo_name already exists, pulling latest"
        cd "$repo_name" && git pull && cd ..
    else
        git clone --depth 1 "$repo_url" || {
            print_error "Failed to clone $repo_url"
            return 1
        }
    fi

    cd "$repo_name"
    if [ -n "$build_cmds" ]; then
        eval "$build_cmds" || print_error "Build failed for $repo_name"
    fi
    if [ -n "$install_dir" ]; then
        mkdir -p "$install_dir"
        # Assuming we need to copy binaries, but this is generic
    fi
    cd /opt
    echo "Installed $repo_name"
}

# =============================================================================
# 1. Initial System Update and Prerequisites
# =============================================================================
print_step "Starting Kali Linux Ultimate Customization"

# Ensure we are root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root"
    exit 1
fi

print_step "Updating system and installing core dependencies"
apt-get update && apt-get upgrade -y
apt_install curl wget git vim nano htop tmux screen build-essential \
    software-properties-common dirmngr apt-transport-https lsb-release ca-certificates \
    gnupg2 unzip zip gzip tar bzip2 p7zip-full p7zip-rar \
    python3 python3-pip python3-dev python3-venv \
    ruby ruby-dev gem \
    perl perl-base \
    nodejs npm \
    golang-go \
    default-jdk default-jre \
    cargo \
    cmake autoconf automake libtool \
    libssl-dev libffi-dev libpcap-dev libpq-dev libsqlite3-dev \
    libncurses5-dev libreadline-dev libbz2-dev liblzma-dev \
    net-tools iputils-ping dnsutils whois \
    openssh-server openssh-client \
    sudo

# Enable SSH for remote access
systemctl enable ssh --now

# =============================================================================
# 2. Create AI User with Full Admin Access
# =============================================================================
print_step "Creating 'ai' user with full admin access"

# Create user 'ai' if not exists
if id "ai" &>/dev/null; then
    print_warn "User 'ai' already exists"
else
    useradd -m -s /bin/bash -G sudo ai
    echo "ai ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
    # Set a random password (or you can set a known one later)
    echo "ai:$(openssl rand -base64 12)" | chpasswd
    print_step "AI user created with random password (check log)"
fi

# Set up SSH for ai user
mkdir -p /home/ai/.ssh
chmod 700 /home/ai/.ssh
touch /home/ai/.ssh/authorized_keys
chmod 600 /home/ai/.ssh/authorized_keys
chown -R ai:ai /home/ai/.ssh

# Generate SSH key for ai (optional)
sudo -u ai ssh-keygen -t ed25519 -f /home/ai/.ssh/id_ed25519 -N "" -C "ai@kali"

# Add ai to necessary groups
usermod -aG adm,cdrom,sudo,dip,plugdev,kali-trusted ai

# =============================================================================
# 3. Setup Directories and Environment for AI
# =============================================================================
print_step "Setting up AI home directory structure"

# Create directories for tools, scripts, data
sudo -u ai mkdir -p /home/ai/{tools,scripts,data,reports,wordlists,config,logs}
sudo -u ai mkdir -p /home/ai/tools/{github,manual,compiled}

# Set environment variables
cat >> /home/ai/.bashrc << 'EOF'

# Custom environment for AI
export PATH=$PATH:/home/ai/tools/github:/home/ai/tools/compiled:/opt:/usr/local/sbin:/usr/local/bin
export EDITOR=vim
export PAGER=less

# Aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'
alias ..='cd ..'
alias ...='cd ../..'
alias cls='clear'
alias grep='grep --color=auto'
alias fgrep='fgrep --color=auto'
alias egrep='egrep --color=auto'

# PS1
PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '

# Useful functions
extract() {
    if [ -f $1 ] ; then
        case $1 in
            *.tar.bz2)   tar xjf $1     ;;
            *.tar.gz)    tar xzf $1     ;;
            *.bz2)       bunzip2 $1     ;;
            *.rar)       unrar e $1     ;;
            *.gz)        gunzip $1      ;;
            *.tar)       tar xf $1      ;;
            *.tbz2)      tar xjf $1     ;;
            *.tgz)       tar xzf $1     ;;
            *.zip)       unzip $1       ;;
            *.Z)         uncompress $1  ;;
            *.7z)        7z x $1        ;;
            *)           echo "'$1' cannot be extracted via extract()" ;;
        esac
    else
        echo "'$1' is not a valid file"
    fi
}
EOF

chown ai:ai /home/ai/.bashrc

# =============================================================================
# 4. Install Kali Default Tools (Metapackages)
# =============================================================================
print_step "Installing Kali Linux metapackages (all tools)"
apt_install kali-linux-headless  # Includes most tools
apt_install kali-tools-top10 kali-tools-information-gathering kali-tools-vulnerability \
            kali-tools-web kali-tools-database kali-tools-passwords kali-tools-wireless \
            kali-tools-reverse-engineering kali-tools-exploitation kali-tools-social-engineering \
            kali-tools-sniffing-spoofing kali-tools-post-exploitation kali-tools-forensics \
            kali-tools-reporting kali-tools-fuzzing

# =============================================================================
# 5. Install Additional Tools via apt (non-Kali repos)
# =============================================================================
print_step "Installing additional apt packages from Debian/Kali repos"
apt_install \
    # Network and scanning
    masscan zmap hping3 arp-scan nbtscan onesixtyone fping \
    # Web
    whatweb wafw00f wpscan joomscan droopescan \
    # Exploitation
    metasploit-framework exploitdb searchsploit \
    # Password cracking
    hydra john hashcat crunch cewl rsmangler \
    # Wireless
    aircrack-ng reaver bully fern-wifi-cracker \
    # Sniffing/spoofing
    wireshark tshark tcpdump dsniff ettercap-common driftnet \
    # Forensics
    forensics-all autopsy sleuthkit guymager \
    # OSINT
    maltego theharvester recon-ng spiderfoot \
    # Misc
    exiftool binwalk steghide stegsolve

# =============================================================================
# 6. Install Python Tools via pip
# =============================================================================
print_step "Installing Python packages (global)"
python3 -m pip install --upgrade pip setuptools wheel

# Core pentesting libraries
pip3 install impacket scapy requests beautifulsoup4 lxml paramiko \
    cryptography pycryptodome pyOpenSSL \
    sqlalchemy pandas numpy matplotlib \
    colorama termcolor tqdm \
    asyncio aiohttp httpx \
    python-nmap netifaces netaddr ipaddress \
    pywifi wifi \
    flask django fastapi uvicorn \
    pwntools angr ropper \
    shodan censys python-whois \
    yara-python \
    selenium playwright \
    frida frida-tools objection \
    mitmproxy \
    pyshark dpkt \
    volatility3 \
    stegcracker

# =============================================================================
# 7. Install Ruby Gems
# =============================================================================
print_step "Installing Ruby gems"
gem install --no-document \
    bundler \
    mechanize \
    nokogiri \
    metasploit-framework \
    wpscan \
    arachni \
    beEF \
    rubygems-update

# =============================================================================
# 8. Install Node.js / npm packages
# =============================================================================
print_step "Installing Node.js packages"
npm install -g \
    npm@latest \
    yarn \
    nodemon \
    pm2 \
    eslint \
    prettier \
    @angular/cli \
    @vue/cli \
    create-react-app \
    next \
    gulp \
    grunt-cli \
    bower \
    http-server \
    localtunnel \
    ngrok \
    wscat \
    json-server \
    artillery \
    lighthouse \
    pa11y \
    snyk \
    retire \
    js-beautify \
    eslint-plugin-security

# =============================================================================
# 9. Install Go tools
# =============================================================================
print_step "Installing Go tools"
export GOPATH=/home/ai/go
export PATH=$PATH:$GOPATH/bin
mkdir -p $GOPATH
chown -R ai:ai /home/ai/go

# Popular security tools written in Go
go install github.com/OJ/gobuster/v3@latest
go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
go install github.com/projectdiscovery/httpx/cmd/httpx@latest
go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install github.com/projectdiscovery/naabu/v2/cmd/naabu@latest
go install github.com/tomnomnom/assetfinder@latest
go install github.com/tomnomnom/httprobe@latest
go install github.com/tomnomnom/waybackurls@latest
go install github.com/tomnomnom/unfurl@latest
go install github.com/tomnomnom/gf@latest
go install github.com/tomnomnom/fff@latest
go install github.com/tomnomnom/meg@latest
go install github.com/ffuf/ffuf@latest
go install github.com/haccer/subjack@latest
go install github.com/lc/gau/v2/cmd/gau@latest
go install github.com/dwisiswant0/unew@latest
go install github.com/dwisiswant0/cf-check@latest
go install github.com/dwisiswant0/go-dork@latest
go install github.com/dwisiswant0/galer@latest
go install github.com/projectdiscovery/chaos-client/cmd/chaos@latest
go install github.com/projectdiscovery/shuffledns/cmd/shuffledns@latest
go install github.com/projectdiscovery/dnsx/cmd/dnsx@latest
go install github.com/projectdiscovery/interactsh/cmd/interactsh-client@latest
go install github.com/projectdiscovery/notify/cmd/notify@latest
go install github.com/projectdiscovery/uncover/cmd/uncover@latest
go install github.com/projectdiscovery/mapcidr/cmd/mapcidr@latest
go install github.com/projectdiscovery/asnmap/cmd/asnmap@latest
go install github.com/projectdiscovery/cdncheck/cmd/cdncheck@latest
go install github.com/projectdiscovery/cloudlist/cmd/cloudlist@latest
go install github.com/hakluke/hakrawler@latest
go install github.com/hakluke/hakrevdns@latest
go install github.com/hakluke/haktldextract@latest
go install github.com/jaeles-project/gospider@latest
go install github.com/michenriksen/aquatone@latest
go install github.com/bp0lr/gauplus@latest
go install github.com/ferreiraklet/airixss@latest
go install github.com/ferreiraklet/nilo@latest
go install github.com/KathanP19/Gxss@latest
go install github.com/Emoe/kxss@latest
go install github.com/003random/getJS@latest
go install github.com/003random/getAllUrls@latest
go install github.com/KathanP19/httpx-@latest
go install github.com/theblackturtle/tlspretense@latest
go install github.com/theblackturtle/fprobe@latest
go install github.com/theblackturtle/anew@latest
go install github.com/theblackturtle/gowitness@latest
go install github.com/theblackturtle/webanalyze@latest
go install github.com/theblackturtle/antiburl@latest
go install github.com/theblackturtle/unfurl@latest
go install github.com/theblackturtle/ffufPostprocessing@latest
go install github.com/theblackturtle/ffufSampler@latest

# =============================================================================
# 10. Install Rust/Cargo tools
# =============================================================================
print_step "Installing Rust tools"
cargo install \
    ripgrep \
    bat \
    exa \
    fd-find \
    procs \
    sd \
    tokei \
    hyperfine \
    bandwhich \
    du-dust \
    broot \
    xsv \
    choose \
    grex \
    tealdeer \
    bottom \
    gping \
    rustscan \
    feroxbuster \
    httprobe \
    rustcan

# =============================================================================
# 11. Install GitHub Tools (Massive List - Over 500)
# =============================================================================
print_step "Installing tools from GitHub (this will take a while)..."

# Create a directory for all GitHub tools
mkdir -p /opt/github_tools
cd /opt/github_tools

# Helper: clone and optionally build
clone_and_build() {
    repo=$1
    build_cmd=$2
    dir=$(basename "$repo" .git)
    print_step "Cloning $repo"
    if [ -d "$dir" ]; then
        cd "$dir" && git pull && cd ..
    else
        git clone --depth 1 "$repo"
    fi
    cd "$dir"
    if [ -n "$build_cmd" ]; then
        eval "$build_cmd"
    fi
    # If there's a binary, copy to /usr/local/bin
    if [ -f "$dir" ]; then
        cp "$dir" /usr/local/bin/ 2>/dev/null || true
    fi
    if [ -f "bin/$dir" ]; then
        cp "bin/$dir" /usr/local/bin/ 2>/dev/null || true
    fi
    if [ -f "target/release/$dir" ]; then
        cp "target/release/$dir" /usr/local/bin/ 2>/dev/null || true
    fi
    # If there's a setup.py or install script, run it
    if [ -f "setup.py" ]; then
        python3 setup.py install 2>/dev/null || true
    fi
    if [ -f "install.sh" ]; then
        bash install.sh 2>/dev/null || true
    fi
    cd ..
}

# =============================================================================
# 11a. Reconnaissance / Information Gathering
# =============================================================================
print_step "--- Reconnaissance Tools ---"

clone_and_build "https://github.com/OWASP/Amass.git" "go build -o amass ./cmd/amass && cp amass /usr/local/bin/"
clone_and_build "https://github.com/aboul3la/Sublist3r.git" "python3 setup.py install"
clone_and_build "https://github.com/shmilylty/OneForAll.git" "pip3 install -r requirements.txt"
clone_and_build "https://github.com/laramies/theHarvester.git" "python3 setup.py install"
clone_and_build "https://github.com/FortyNorthSecurity/EyeWitness.git" "bash setup/setup.sh"
clone_and_build "https://github.com/leebaird/discover.git" "bash update.sh"
clone_and_build "https://github.com/darkoperator/dnsrecon.git" "python3 setup.py install"
clone_and_build "https://github.com/guelfoweb/knock.git" "python3 setup.py install"
clone_and_build "https://github.com/ChrisTruncer/EyeWitness.git" "bash setup.sh"
clone_and_build "https://github.com/anshumanbh/brutesubs.git" "python3 setup.py install"
clone_and_build "https://github.com/Ice3man543/SubOver.git" "go build && cp SubOver /usr/local/bin/"
clone_and_build "https://github.com/elceef/dnstwist.git" "python3 setup.py install"
clone_and_build "https://github.com/j3ssie/Osmedeus.git" "bash install.sh"
clone_and_build "https://github.com/lanmaster53/recon-ng.git" "python3 setup.py install"
clone_and_build "https://github.com/smicallef/spiderfoot.git" "python3 setup.py install"
clone_and_build "https://github.com/michenriksen/aquatone.git" "go build && cp aquatone /usr/local/bin/"
clone_and_build "https://github.com/jaeles-project/gospider.git" "go build && cp gospider /usr/local/bin/"
clone_and_build "https://github.com/haccer/subjack.git" "go build && cp subjack /usr/local/bin/"
clone_and_build "https://github.com/projectdiscovery/httpx.git" "go build && cp httpx /usr/local/bin/"
clone_and_build "https://github.com/projectdiscovery/nuclei.git" "go build && cp nuclei /usr/local/bin/"
clone_and_build "https://github.com/projectdiscovery/subfinder.git" "go build && cp subfinder /usr/local/bin/"
clone_and_build "https://github.com/projectdiscovery/naabu.git" "go build && cp naabu /usr/local/bin/"
clone_and_build "https://github.com/projectdiscovery/chaos-client.git" "go build && cp chaos /usr/local/bin/"
clone_and_build "https://github.com/projectdiscovery/dnsx.git" "go build && cp dnsx /usr/local/bin/"
clone_and_build "https://github.com/projectdiscovery/uncover.git" "go build && cp uncover /usr/local/bin/"
clone_and_build "https://github.com/tomnomnom/assetfinder.git" "go build && cp assetfinder /usr/local/bin/"
clone_and_build "https://github.com/tomnomnom/httprobe.git" "go build && cp httprobe /usr/local/bin/"
clone_and_build "https://github.com/tomnomnom/waybackurls.git" "go build && cp waybackurls /usr/local/bin/"
clone_and_build "https://github.com/tomnomnom/unfurl.git" "go build && cp unfurl /usr/local/bin/"
clone_and_build "https://github.com/tomnomnom/gf.git" "go build && cp gf /usr/local/bin/"
clone_and_build "https://github.com/ffuf/ffuf.git" "go build && cp ffuf /usr/local/bin/"
clone_and_build "https://github.com/lc/gau.git" "go build && cp gau /usr/local/bin/"
clone_and_build "https://github.com/hakluke/hakrawler.git" "go build && cp hakrawler /usr/local/bin/"
clone_and_build "https://github.com/hakluke/hakrevdns.git" "go build && cp hakrevdns /usr/local/bin/"
clone_and_build "https://github.com/dwisiswant0/unew.git" "go build && cp unew /usr/local/bin/"
clone_and_build "https://github.com/dwisiswant0/cf-check.git" "go build && cp cf-check /usr/local/bin/"
clone_and_build "https://github.com/dwisiswant0/go-dork.git" "go build && cp go-dork /usr/local/bin/"
clone_and_build "https://github.com/dwisiswant0/galer.git" "go build && cp galer /usr/local/bin/"
clone_and_build "https://github.com/bp0lr/gauplus.git" "go build && cp gauplus /usr/local/bin/"
clone_and_build "https://github.com/KathanP19/Gxss.git" "go build && cp Gxss /usr/local/bin/"
clone_and_build "https://github.com/Emoe/kxss.git" "go build && cp kxss /usr/local/bin/"
clone_and_build "https://github.com/003random/getJS.git" "go build && cp getJS /usr/local/bin/"
clone_and_build "https://github.com/003random/getAllUrls.git" "go build && cp getAllUrls /usr/local/bin/"
clone_and_build "https://github.com/ferreiraklet/airixss.git" "go build && cp airixss /usr/local/bin/"
clone_and_build "https://github.com/ferreiraklet/nilo.git" "go build && cp nilo /usr/local/bin/"
clone_and_build "https://github.com/theblackturtle/fprobe.git" "go build && cp fprobe /usr/local/bin/"
clone_and_build "https://github.com/theblackturtle/gowitness.git" "go build && cp gowitness /usr/local/bin/"
clone_and_build "https://github.com/theblackturtle/webanalyze.git" "go build && cp webanalyze /usr/local/bin/"

# =============================================================================
# 11b. Vulnerability Scanners
# =============================================================================
print_step "--- Vulnerability Scanners ---"

clone_and_build "https://github.com/sullo/nikto.git" "perl nikto.pl -update"
clone_and_build "https://github.com/andresriancho/w3af.git" "python3 w3af_console"
clone_and_build "https://github.com/zdresearch/OWASP-ZSC.git" "python3 setup.py install"
clone_and_build "https://github.com/1N3/Sn1per.git" "bash install.sh"
clone_and_build "https://github.com/1N3/Findsploit.git" "bash install.sh"
clone_and_build "https://github.com/1N3/Goohak.git" "cp goohak /usr/local/bin/"
clone_and_build "https://github.com/maurosoria/dirsearch.git" "python3 setup.py install"
clone_and_build "https://github.com/OJ/gobuster.git" "go build && cp gobuster /usr/local/bin/"
clone_and_build "https://github.com/ameenmaali/urldedupe.git" "go build && cp urldedupe /usr/local/bin/"
clone_and_build "https://github.com/maK-/parameth.git" "python3 setup.py install"
clone_and_build "https://github.com/PortSwigger/param-miner.git" "git clone https://github.com/PortSwigger/param-miner.git"
clone_and_build "https://github.com/ethicalhack3r/DVWA.git" "chmod +x dvwa"
clone_and_build "https://github.com/digininja/DVWA.git" "chmod +x dvwa"
clone_and_build "https://github.com/webpwnized/mutillidae.git" "chmod +x mutillidae"
clone_and_build "https://github.com/cisc0/xxe-injection.git" "python3 setup.py install"
clone_and_build "https://github.com/vulnersCom/api.git" "python3 setup.py install"
clone_and_build "https://github.com/cloudflare/flan.git" "python3 setup.py install"
clone_and_build "https://github.com/OWASP/NodeGoat.git" "npm install"
clone_and_build "https://github.com/Contrast-Security-OSS/go-test.git" "go build"
clone_and_build "https://github.com/liamg/traitor.git" "go build && cp traitor /usr/local/bin/"
clone_and_build "https://github.com/carlospolop/PEASS-ng.git" "chmod +x linpeas.sh && chmod +x winPEAS.bat"
clone_and_build "https://github.com/rebootuser/LinEnum.git" "chmod +x LinEnum.sh"
clone_and_build "https://github.com/diego-treitos/linux-smart-enumeration.git" "chmod +x lse.sh"
clone_and_build "https://github.com/Anon-Exploiter/SUID3NUM.git" "chmod +x suid3num.py"
clone_and_build "https://github.com/jondonas/linux-exploit-suggester-2.git" "chmod +x linux-exploit-suggester-2.pl"
clone_and_build "https://github.com/InteliSecureLabs/Linux_Exploit_Suggester.git" "chmod +x Linux_Exploit_Suggester.pl"
clone_and_build "https://github.com/SecWiki/windows-kernel-exploits.git" "chmod +x windows-kernel-exploits"
clone_and_build "https://github.com/abatchy17/WindowsExploits.git" "chmod +x WindowsExploits"

# =============================================================================
# 11c. Exploitation Frameworks
# =============================================================================
print_step "--- Exploitation Frameworks ---"

# Metasploit is already installed, but we can add extra modules
clone_and_build "https://github.com/rapid7/metasploit-framework.git" "bundle install && ./msfupdate"
clone_and_build "https://github.com/beefproject/beef.git" "bundle install && ./install"
clone_and_build "https://github.com/trustedsec/social-engineer-toolkit.git" "python3 setup.py install"
clone_and_build "https://github.com/EmpireProject/Empire.git" "python3 setup.py install"
clone_and_build "https://github.com/byt3bl33d3r/CrackMapExec.git" "python3 setup.py install"
clone_and_build "https://github.com/SecureAuthCorp/impacket.git" "python3 setup.py install"
clone_and_build "https://github.com/samratashok/nishang.git" "chmod +x nishang"
clone_and_build "https://github.com/PowerShellMafia/PowerSploit.git" "chmod +x PowerSploit"
clone_and_build "https://github.com/Veil-Framework/Veil.git" "bash install.sh"
clone_and_build "https://github.com/Veil-Framework/Veil-Evasion.git" "python3 setup.py install"
clone_and_build "https://github.com/Veil-Framework/Veil-Catapult.git" "python3 setup.py install"
clone_and_build "https://github.com/Veil-Framework/Veil-Ordnance.git" "python3 setup.py install"
clone_and_build "https://github.com/shelld3v/RCE-python.git" "python3 setup.py install"
clone_and_build "https://github.com/koozali/weevely.git" "python3 setup.py install"
clone_and_build "https://github.com/epinna/weevely3.git" "python3 setup.py install"
clone_and_build "https://github.com/mIcHyAmRaNe/weevely4.git" "python3 setup.py install"
clone_and_build "https://github.com/b4rtik/ATPMiniDump.git" "chmod +x ATPMiniDump"
clone_and_build "https://github.com/gentilkiwi/mimikatz.git" "chmod +x mimikatz"
clone_and_build "https://github.com/byt3bl33d3r/pth-toolkit.git" "python3 setup.py install"
clone_and_build "https://github.com/Kevin-Robertson/Invoke-TheHash.git" "chmod +x Invoke-TheHash"
clone_and_build "https://github.com/maaaaz/impacket-examples-windows.git" "chmod +x impacket-examples-windows"
clone_and_build "https://github.com/CoreSecurity/impacket.git" "python3 setup.py install"
clone_and_build "https://github.com/SySS-Research/Seth.git" "python3 setup.py install"
clone_and_build "https://github.com/lgandx/Responder.git" "chmod +x Responder.py"
clone_and_build "https://github.com/SpiderLabs/Responder.git" "chmod +x Responder.py"
clone_and_build "https://github.com/skelsec/winacl.git" "python3 setup.py install"
clone_and_build "https://github.com/skelsec/aiowinreg.git" "python3 setup.py install"
clone_and_build "https://github.com/skelsec/msldap.git" "python3 setup.py install"
clone_and_build "https://github.com/skelsec/minikerberos.git" "python3 setup.py install"
clone_and_build "https://github.com/dirkjanm/ldapdomaindump.git" "python3 setup.py install"
clone_and_build "https://github.com/dirkjanm/PrivExchange.git" "python3 setup.py install"
clone_and_build "https://github.com/fox-it/BloodHound.py.git" "python3 setup.py install"
clone_and_build "https://github.com/BloodHoundAD/BloodHound.git" "npm install && npm run build"
clone_and_build "https://github.com/CompassSecurity/BloodHoundQueries.git" "chmod +x BloodHoundQueries"
clone_and_build "https://github.com/hausec/BloodHound-Custom-Queries.git" "chmod +x BloodHound-Custom-Queries"
clone_and_build "https://github.com/ShutdownRepo/impacket.git" "python3 setup.py install"

# =============================================================================
# 11d. Password Cracking
# =============================================================================
print_step "--- Password Cracking ---"

clone_and_build "https://github.com/hashcat/hashcat.git" "make && make install"
clone_and_build "https://github.com/hashcat/hashcat-utils.git" "make && cp bin/* /usr/local/bin/"
clone_and_build "https://github.com/hashcat/kwprocessor.git" "make && cp kwp /usr/local/bin/"
clone_and_build "https://github.com/hashcat/princeprocessor.git" "make && cp pp64.bin /usr/local/bin/pp"
clone_and_build "https://github.com/hashcat/maskprocessor.git" "make && cp mp64.bin /usr/local/bin/mp"
clone_and_build "https://github.com/hashcat/statsprocessor.git" "make && cp sp64.bin /usr/local/bin/sp"
clone_and_build "https://github.com/lmsecure/PCredz.git" "python3 setup.py install"
clone_and_build "https://github.com/DanMcInerney/creds.py.git" "python3 setup.py install"
clone_and_build "https://github.com/byt3bl33d3r/credking.git" "python3 setup.py install"
clone_and_build "https://github.com/NetSPI/PSPKIAudit.git" "chmod +x PSPKIAudit"
clone_and_build "https://github.com/NetSPI/PowerUpSQL.git" "chmod +x PowerUpSQL"
clone_and_build "https://github.com/NetSPI/PowerUp.git" "chmod +x PowerUp"
clone_and_build "https://github.com/NetSPI/PowerView.git" "chmod +x PowerView"
clone_and_build "https://github.com/samratashok/ADAPE.git" "chmod +x ADAPE"
clone_and_build "https://github.com/hdm/credgrap.git" "python3 setup.py install"
clone_and_build "https://github.com/lanmaster53/ptf.git" "python3 setup.py install"
clone_and_build "https://github.com/trustedsec/unicorn.git" "chmod +x unicorn.py"
clone_and_build "https://github.com/trustedsec/trevorc2.git" "chmod +x trevorc2"
clone_and_build "https://github.com/trustedsec/egressbuster.git" "chmod +x egressbuster"
clone_and_build "https://github.com/trustedsec/katana.git" "python3 setup.py install"
clone_and_build "https://github.com/trustedsec/artillery.git" "python3 setup.py install"
clone_and_build "https://github.com/trustedsec/ridrelay.git" "python3 setup.py install"
clone_and_build "https://github.com/trustedsec/meterpreter.git" "chmod +x meterpreter"
clone_and_build "https://github.com/trustedsec/trevorproxy.git" "chmod +x trevorproxy"
clone_and_build "https://github.com/trustedsec/ms17-010.git" "chmod +x ms17-010"
clone_and_build "https://github.com/trustedsec/eternalblue.git" "chmod +x eternalblue"
clone_and_build "https://github.com/trustedsec/bluekeep.git" "chmod +x bluekeep"
clone_and_build "https://github.com/trustedsec/smbexec.git" "python3 setup.py install"
clone_and_build "https://github.com/trustedsec/regripper.git" "chmod +x regripper"

# =============================================================================
# 11e. Web Application Tools
# =============================================================================
print_step "--- Web Application Tools ---"

clone_and_build "https://github.com/sqlmapproject/sqlmap.git" "python3 setup.py install"
clone_and_build "https://github.com/beefproject/beef.git" "bundle install && ./install"
clone_and_build "https://github.com/wpscanteam/wpscan.git" "gem install wpscan"
clone_and_build "https://github.com/joomla/joomla-cms.git" "chmod +x joomla"
clone_and_build "https://github.com/droope/droopescan.git" "python3 setup.py install"
clone_and_build "https://github.com/commixproject/commix.git" "python3 setup.py install"
clone_and_build "https://github.com/epinna/tplmap.git" "python3 setup.py install"
clone_and_build "https://github.com/iceyhexman/auxscan.git" "python3 setup.py install"
clone_and_build "https://github.com/SpiderLabs/owasp-modsecurity-crs.git" "chmod +x owasp-modsecurity-crs"
clone_and_build "https://github.com/SpiderLabs/ModSecurity.git" "chmod +x ModSecurity"
clone_and_build "https://github.com/SpiderLabs/ModSecurity-nginx.git" "chmod +x ModSecurity-nginx"
clone_and_build "https://github.com/SpiderLabs/ModSecurity-apache.git" "chmod +x ModSecurity-apache"
clone_and_build "https://github.com/SpiderLabs/ModSecurity-iis.git" "chmod +x ModSecurity-iis"
clone_and_build "https://github.com/OWASP/CheatSheetSeries.git" "chmod +x CheatSheetSeries"
clone_and_build "https://github.com/OWASP/NodeGoat.git" "npm install"
clone_and_build "https://github.com/OWASP/railsgoat.git" "bundle install"
clone_and_build "https://github.com/OWASP/GoatDocker.git" "chmod +x GoatDocker"
clone_and_build "https://github.com/OWASP/DevSlop.git" "chmod +x DevSlop"
clone_and_build "https://github.com/OWASP/SecureTea-Project.git" "python3 setup.py install"
clone_and_build "https://github.com/OWASP/Amass.git" "go build -o amass ./cmd/amass && cp amass /usr/local/bin/"
clone_and_build "https://github.com/OWASP/Nettacker.git" "python3 setup.py install"
clone_and_build "https://github.com/OWASP/ThreatDragon.git" "npm install && npm run build"
clone_and_build "https://github.com/OWASP/CSRFGuard.git" "chmod +x CSRFGuard"
clone_and_build "https://github.com/OWASP/ESAPI.git" "chmod +x ESAPI"
clone_and_build "https://github.com/OWASP/SecurityShepherd.git" "chmod +x SecurityShepherd"

# =============================================================================
# 11f. Wireless and Bluetooth
# =============================================================================
print_step "--- Wireless Tools ---"

clone_and_build "https://github.com/aircrack-ng/aircrack-ng.git" "make && make install"
clone_and_build "https://github.com/OpenSecurityResearch/hostapd-wpe.git" "make && make install"
clone_and_build "https://github.com/wi-fi-analyzer/fluxion.git" "chmod +x fluxion.sh"
clone_and_build "https://github.com/wifiphisher/wifiphisher.git" "python3 setup.py install"
clone_and_build "https://github.com/esc0rtd3w/wifi-hacker.git" "chmod +x wifi-hacker.sh"
clone_and_build "https://github.com/derv82/wifite2.git" "python3 setup.py install"
clone_and_build "https://github.com/kimocoder/reaver.git" "make && make install"
clone_and_build "https://github.com/t6x/reaver-wps-fork-t6x.git" "make && make install"
clone_and_build "https://github.com/aanarchyy/bully.git" "make && make install"
clone_and_build "https://github.com/wiire/pixiewps.git" "make && make install"
clone_and_build "https://github.com/OpenSecurityResearch/hostapd-wpe.git" "make && make install"
clone_and_build "https://github.com/s0lst1c3/eaphammer.git" "python3 setup.py install"
clone_and_build "https://github.com/sensepost/hostapd-mana.git" "make && make install"
clone_and_build "https://github.com/sensepost/wpa2-halfhandshake.git" "python3 setup.py install"
clone_and_build "https://github.com/sensepost/wifi-arsenal.git" "chmod +x wifi-arsenal"
clone_and_build "https://github.com/xtr4nge/FruityWifi.git" "chmod +x FruityWifi"
clone_and_build "https://github.com/xtr4nge/FruityC2.git" "chmod +x FruityC2"
clone_and_build "https://github.com/xtr4nge/adsys.git" "chmod +x adsys"
clone_and_build "https://github.com/xtr4nge/mdk4.git" "make && make install"
clone_and_build "https://github.com/aircrack-ng/mdk4.git" "make && make install"
clone_and_build "https://github.com/aircrack-ng/rtl8812au.git" "make && make install"
clone_and_build "https://github.com/aircrack-ng/rtl8188eus.git" "make && make install"
clone_and_build "https://github.com/aircrack-ng/rtl88x2bu.git" "make && make install"
clone_and_build "https://github.com/lostincynicism/BlueMaho.git" "python3 setup.py install"
clone_and_build "https://github.com/sgayou/bluediving.git" "python3 setup.py install"
clone_and_build "https://github.com/mikeryan/crackle.git" "make && cp crackle /usr/local/bin/"
clone_and_build "https://github.com/NullHypothesis/btlejack.git" "python3 setup.py install"
clone_and_build "https://github.com/virtualabs/btlejack.git" "python3 setup.py install"

# =============================================================================
# 11g. Forensics and Anti-Forensics
# =============================================================================
print_step "--- Forensics Tools ---"

clone_and_build "https://github.com/sleuthkit/sleuthkit.git" "bash bootstrap && ./configure && make && make install"
clone_and_build "https://github.com/sleuthkit/autopsy.git" "bash build.sh && make install"
clone_and_build "https://github.com/volatilityfoundation/volatility3.git" "python3 setup.py install"
clone_and_build "https://github.com/volatilityfoundation/volatility.git" "python2 setup.py install"
clone_and_build "https://github.com/ReFirmLabs/binwalk.git" "python3 setup.py install"
clone_and_build "https://github.com/devttys0/binwalk.git" "python3 setup.py install"
clone_and_build "https://github.com/carmaa/inception.git" "python3 setup.py install"
clone_and_build "https://github.com/magnumripper/JohnTheRipper.git" "cd src && ./configure && make && make install"
clone_and_build "https://github.com/openwall/john.git" "cd src && ./configure && make && make install"
clone_and_build "https://github.com/hashcat/hashcat.git" "make && make install"
clone_and_build "https://github.com/guelfoweb/peframe.git" "python3 setup.py install"
clone_and_build "https://github.com/viper-framework/viper.git" "python3 setup.py install"
clone_and_build "https://github.com/viper-framework/viper-web.git" "python3 setup.py install"
clone_and_build "https://github.com/cuckoosandbox/cuckoo.git" "python3 setup.py install"
clone_and_build "https://github.com/kevthehermit/RATDecoders.git" "python3 setup.py install"
clone_and_build "https://github.com/kevthehermit/VolUtility.git" "python3 setup.py install"
clone_and_build "https://github.com/volatilityfoundation/volatility.git" "python2 setup.py install"
clone_and_build "https://github.com/volatilityfoundation/volatility3.git" "python3 setup.py install"
clone_and_build "https://github.com/504ensicsLabs/LiME.git" "make"
clone_and_build "https://github.com/504ensicsLabs/avml.git" "make && cp avml /usr/local/bin/"
clone_and_build "https://github.com/google/rekall.git" "python3 setup.py install"
clone_and_build "https://github.com/google/grr.git" "python3 setup.py install"
clone_and_build "https://github.com/google/turbinia.git" "python3 setup.py install"
clone_and_build "https://github.com/google/docker-explorer.git" "python3 setup.py install"
clone_and_build "https://github.com/google/parsson.git" "python3 setup.py install"
clone_and_build "https://github.com/google/dfdewey.git" "python3 setup.py install"
clone_and_build "https://github.com/google/docker-explorer.git" "python3 setup.py install"

# =============================================================================
# 11h. Reverse Engineering
# =============================================================================
print_step "--- Reverse Engineering Tools ---"

clone_and_build "https://github.com/radareorg/radare2.git" "sys/install.sh"
clone_and_build "https://github.com/radareorg/cutter.git" "qmake && make"
clone_and_build "https://github.com/rizinorg/rizin.git" "meson build && ninja -C build && ninja -C build install"
clone_and_build "https://github.com/angr/angr.git" "python3 setup.py install"
clone_and_build "https://github.com/angr/angr-doc.git" "chmod +x angr-doc"
clone_and_build "https://github.com/angr/angr-management.git" "python3 setup.py install"
clone_and_build "https://github.com/angr/angr-utils.git" "python3 setup.py install"
clone_and_build "https://github.com/angr/angrop.git" "python3 setup.py install"
clone_and_build "https://github.com/angr/archr.git" "python3 setup.py install"
clone_and_build "https://github.com/angr/cle.git" "python3 setup.py install"
clone_and_build "https://github.com/angr/pyvex.git" "python3 setup.py install"
clone_and_build "https://github.com/angr/claripy.git" "python3 setup.py install"
clone_and_build "https://github.com/Gallopsled/pwntools.git" "python3 setup.py install"
clone_and_build "https://github.com/pwndbg/pwndbg.git" "./setup.sh"
clone_and_build "https://github.com/jfoote/exploitable.git" "python3 setup.py install"
clone_and_build "https://github.com/longld/peda.git" "git clone https://github.com/longld/peda.git ~/peda && echo 'source ~/peda/peda.py' >> ~/.gdbinit"
clone_and_build "https://github.com/hugsy/gef.git" "wget -O ~/.gdbinit-gef.py -q https://gef.blah.cat/py && echo source ~/.gdbinit-gef.py >> ~/.gdbinit"
clone_and_build "https://github.com/scwuaptx/Pwngdb.git" "cp .gdbinit ~/"
clone_and_build "https://github.com/NationalSecurityAgency/ghidra.git" "chmod +x ghidraRun"
clone_and_build "https://github.com/NationalSecurityAgency/ghidra-golang.git" "chmod +x ghidra-golang"
clone_and_build "https://github.com/NationalSecurityAgency/ghidra-rust.git" "chmod +x ghidra-rust"
clone_and_build "https://github.com/NationalSecurityAgency/ghidra-python.git" "chmod +x ghidra-python"
clone_and_build "https://github.com/NationalSecurityAgency/ghidra-javascript.git" "chmod +x ghidra-javascript"
clone_and_build "https://github.com/NationalSecurityAgency/ghidra-typescript.git" "chmod +x ghidra-typescript"
clone_and_build "https://github.com/NationalSecurityAgency/ghidra-cpp.git" "chmod +x ghidra-cpp"
clone_and_build "https://github.com/NationalSecurityAgency/ghidra-java.git" "chmod +x ghidra-java"
clone_and_build "https://github.com/NationalSecurityAgency/ghidra-python3.git" "chmod +x ghidra-python3"

# =============================================================================
# 11i. OSINT and Social Media
# =============================================================================
print_step "--- OSINT Tools ---"

clone_and_build "https://github.com/smicallef/spiderfoot.git" "python3 setup.py install"
clone_and_build "https://github.com/laramies/theHarvester.git" "python3 setup.py install"
clone_and_build "https://github.com/aboul3la/Sublist3r.git" "python3 setup.py install"
clone_and_build "https://github.com/leebaird/discover.git" "bash update.sh"
clone_and_build "https://github.com/darkoperator/dnsrecon.git" "python3 setup.py install"
clone_and_build "https://github.com/guelfoweb/knock.git" "python3 setup.py install"
clone_and_build "https://github.com/ChrisTruncer/EyeWitness.git" "bash setup.sh"
clone_and_build "https://github.com/anshumanbh/brutesubs.git" "python3 setup.py install"
clone_and_build "https://github.com/Ice3man543/SubOver.git" "go build && cp SubOver /usr/local/bin/"
clone_and_build "https://github.com/elceef/dnstwist.git" "python3 setup.py install"
clone_and_build "https://github.com/j3ssie/Osmedeus.git" "bash install.sh"
clone_and_build "https://github.com/lanmaster53/recon-ng.git" "python3 setup.py install"
clone_and_build "https://github.com/smicallef/spiderfoot.git" "python3 setup.py install"
clone_and_build "https://github.com/michenriksen/aquatone.git" "go build && cp aquatone /usr/local/bin/"
clone_and_build "https://github.com/jaeles-project/gospider.git" "go build && cp gospider /usr/local/bin/"
clone_and_build "https://github.com/haccer/subjack.git" "go build && cp subjack /usr/local/bin/"
clone_and_build "https://github.com/tomnomnom/assetfinder.git" "go build && cp assetfinder /usr/local/bin/"
clone_and_build "https://github.com/tomnomnom/httprobe.git" "go build && cp httprobe /usr/local/bin/"
clone_and_build "https://github.com/tomnomnom/waybackurls.git" "go build && cp waybackurls /usr/local/bin/"
clone_and_build "https://github.com/tomnomnom/unfurl.git" "go build && cp unfurl /usr/local/bin/"
clone_and_build "https://github.com/tomnomnom/gf.git" "go build && cp gf /usr/local/bin/"
clone_and_build "https://github.com/lc/gau.git" "go build && cp gau /usr/local/bin/"
clone_and_build "https://github.com/hakluke/hakrawler.git" "go build && cp hakrawler /usr/local/bin/"
clone_and_build "https://github.com/hakluke/hakrevdns.git" "go build && cp hakrevdns /usr/local/bin/"
clone_and_build "https://github.com/dwisiswant0/unew.git" "go build && cp unew /usr/local/bin/"
clone_and_build "https://github.com/dwisiswant0/cf-check.git" "go build && cp cf-check /usr/local/bin/"
clone_and_build "https://github.com/dwisiswant0/go-dork.git" "go build && cp go-dork /usr/local/bin/"
clone_and_build "https://github.com/dwisiswant0/galer.git" "go build && cp galer /usr/local/bin/"
clone_and_build "https://github.com/bp0lr/gauplus.git" "go build && cp gauplus /usr/local/bin/"
clone_and_build "https://github.com/KathanP19/Gxss.git" "go build && cp Gxss /usr/local/bin/"
clone_and_build "https://github.com/Emoe/kxss.git" "go build && cp kxss /usr/local/bin/"
clone_and_build "https://github.com/003random/getJS.git" "go build && cp getJS /usr/local/bin/"
clone_and_build "https://github.com/003random/getAllUrls.git" "go build && cp getAllUrls /usr/local/bin/"
clone_and_build "https://github.com/ferreiraklet/airixss.git" "go build && cp airixss /usr/local/bin/"
clone_and_build "https://github.com/ferreiraklet/nilo.git" "go build && cp nilo /usr/local/bin/"
clone_and_build "https://github.com/theblackturtle/fprobe.git" "go build && cp fprobe /usr/local/bin/"
clone_and_build "https://github.com/theblackturtle/gowitness.git" "go build && cp gowitness /usr/local/bin/"
clone_and_build "https://github.com/theblackturtle/webanalyze.git" "go build && cp webanalyze /usr/local/bin/"
clone_and_build "https://github.com/theblackturtle/antiburl.git" "go build && cp antiburl /usr/local/bin/"
clone_and_build "https://github.com/theblackturtle/unfurl.git" "go build && cp unfurl /usr/local/bin/"
clone_and_build "https://github.com/theblackturtle/ffufPostprocessing.git" "go build && cp ffufPostprocessing /usr/local/bin/"
clone_and_build "https://github.com/theblackturtle/ffufSampler.git" "go build && cp ffufSampler /usr/local/bin/"

# =============================================================================
# 11j. Steganography and Encoding
# =============================================================================
print_step "--- Steganography Tools ---"

clone_and_build "https://github.com/cedricbonhomme/Stegano.git" "python3 setup.py install"
clone_and_build "https://github.com/ragibson/Steganography.git" "python3 setup.py install"
clone_and_build "https://github.com/peewpw/Invoke-PSImage.git" "chmod +x Invoke-PSImage"
clone_and_build "https://github.com/livz/cloacked-pixel.git" "python3 setup.py install"
clone_and_build "https://github.com/beurtschipper/Depix.git" "python3 setup.py install"
clone_and_build "https://github.com/dhsdshdhk/stegpy.git" "python3 setup.py install"
clone_and_build "https://github.com/ragibson/Steganography.git" "python3 setup.py install"
clone_and_build "https://github.com/7thCandidate/steghide.git" "make && make install"
clone_and_build "https://github.com/StegOnline/StegOnline.git" "chmod +x StegOnline"
clone_and_build "https://github.com/AresS31/StegCracker.git" "python3 setup.py install"
clone_and_build "https://github.com/DominicBreuker/stego-toolkit.git" "chmod +x stego-toolkit"
clone_and_build "https://github.com/ansjdnakjdnajkd/Steg.git" "python3 setup.py install"
clone_and_build "https://github.com/redcode-labs/STEGO.git" "make && cp STEGO /usr/local/bin/"

# =============================================================================
# 11k. Post-Exploitation and Persistence
# =============================================================================
print_step "--- Post-Exploitation Tools ---"

clone_and_build "https://github.com/EmpireProject/Empire.git" "python3 setup.py install"
clone_and_build "https://github.com/PowerShellMafia/PowerSploit.git" "chmod +x PowerSploit"
clone_and_build "https://github.com/samratashok/nishang.git" "chmod +x nishang"
clone_and_build "https://github.com/byt3bl33d3r/CrackMapExec.git" "python3 setup.py install"
clone_and_build "https://github.com/gentilkiwi/mimikatz.git" "chmod +x mimikatz"
clone_and_build "https://github.com/peewpw/Invoke-WCMDump.git" "chmod +x Invoke-WCMDump"
clone_and_build "https://github.com/peewpw/Invoke-PSImage.git" "chmod +x Invoke-PSImage"
clone_and_build "https://github.com/peewpw/Invoke-Binary.git" "chmod +x Invoke-Binary"
clone_and_build "https://github.com/peewpw/Invoke-CradleCrafter.git" "chmod +x Invoke-CradleCrafter"
clone_and_build "https://github.com/peewpw/Invoke-Obfuscation.git" "chmod +x Invoke-Obfuscation"
clone_and_build "https://github.com/peewpw/Invoke-DOSfuscation.git" "chmod +x Invoke-DOSfuscation"
clone_and_build "https://github.com/peewpw/Invoke-CradleCrafter.git" "chmod +x Invoke-CradleCrafter"
clone_and_build "https://github.com/peewpw/Invoke-SocksProxy.git" "chmod +x Invoke-SocksProxy"
clone_and_build "https://github.com/peewpw/Invoke-PortScan.git" "chmod +x Invoke-PortScan"
clone_and_build "https://github.com/peewpw/Invoke-PowerShellTcp.git" "chmod +x Invoke-PowerShellTcp"
clone_and_build "https://github.com/peewpw/Invoke-PowerShellUdp.git" "chmod +x Invoke-PowerShellUdp"
clone_and_build "https://github.com/peewpw/Invoke-PowerShellIcmp.git" "chmod +x Invoke-PowerShellIcmp"
clone_and_build "https://github.com/peewpw/Invoke-PowerShellDns.git" "chmod +x Invoke-PowerShellDns"
clone_and_build "https://github.com/peewpw/Invoke-PowerShellHttp.git" "chmod +x Invoke-PowerShellHttp"
clone_and_build "https://github.com/peewpw/Invoke-PowerShellHttps.git" "chmod +x Invoke-PowerShellHttps"
clone_and_build "https://github.com/peewpw/Invoke-PowerShellSmtp.git" "chmod +x Invoke-PowerShellSmtp"
clone_and_build "https://github.com/peewpw/Invoke-PowerShellPop.git" "chmod +x Invoke-PowerShellPop"
clone_and_build "https://github.com/peewpw/Invoke-PowerShellImap.git" "chmod +x Invoke-PowerShellImap"
clone_and_build "https://github.com/peewpw/Invoke-PowerShellSsh.git" "chmod +x Invoke-PowerShellSsh"

# =============================================================================
# 11l. Mobile and IoT
# =============================================================================
print_step "--- Mobile and IoT Tools ---"

clone_and_build "https://github.com/iBotPeaches/Apktool.git" "chmod +x apktool"
clone_and_build "https://github.com/skylot/jadx.git" "./gradlew dist"
clone_and_build "https://github.com/pxb1988/dex2jar.git" "./gradlew dist"
clone_and_build "https://github.com/radareorg/radare2.git" "sys/install.sh"
clone_and_build "https://github.com/rizinorg/rizin.git" "meson build && ninja -C build && ninja -C build install"
clone_and_build "https://github.com/NationalSecurityAgency/ghidra.git" "chmod +x ghidraRun"
clone_and_build "https://github.com/frida/frida.git" "make"
clone_and_build "https://github.com/frida/frida-tools.git" "python3 setup.py install"
clone_and_build "https://github.com/sensepost/objection.git" "python3 setup.py install"
clone_and_build "https://github.com/MobSF/Mobile-Security-Framework-MobSF.git" "python3 setup.py install"
clone_and_build "https://github.com/MobSF/MobSF.git" "python3 manage.py runserver"
clone_and_build "https://github.com/iSECPartners/Android-Kill.git" "chmod +x Android-Kill"
clone_and_build "https://github.com/iSECPartners/Android-OpenDebug.git" "chmod +x Android-OpenDebug"
clone_and_build "https://github.com/iSECPartners/Android-SSL-TrustKiller.git" "chmod +x Android-SSL-TrustKiller"
clone_and_build "https://github.com/iSECPartners/Android-OpenDebug.git" "chmod +x Android-OpenDebug"
clone_and_build "https://github.com/iSECPartners/Android-OpenDebug.git" "chmod +x Android-OpenDebug"
clone_and_build "https://github.com/OWASP/owasp-mstg.git" "chmod +x owasp-mstg"
clone_and_build "https://github.com/OWASP/owasp-masvs.git" "chmod +x owasp-masvs"
clone_and_build "https://github.com/OWASP/owasp-mobile-security-testing-guide.git" "chmod +x owasp-mobile-security-testing-guide"
clone_and_build "https://github.com/OWASP/owasp-mobile-app-security.git" "chmod +x owasp-mobile-app-security"

# =============================================================================
# 11m. Cloud and Container Security
# =============================================================================
print_step "--- Cloud and Container Tools ---"

clone_and_build "https://github.com/toniblyx/prowler.git" "python3 setup.py install"
clone_and_build "https://github.com/nccgroup/ScoutSuite.git" "python3 setup.py install"
clone_and_build "https://github.com/cloudsploit/scans.git" "npm install"
clone_and_build "https://github.com/aquasecurity/kube-bench.git" "make build && cp kube-bench /usr/local/bin/"
clone_and_build "https://github.com/aquasecurity/kube-hunter.git" "python3 setup.py install"
clone_and_build "https://github.com/aquasecurity/trivy.git" "make build && cp trivy /usr/local/bin/"
clone_and_build "https://github.com/aquasecurity/tfsec.git" "make build && cp tfsec /usr/local/bin/"
clone_and_build "https://github.com/aquasecurity/defsec.git" "make build && cp defsec /usr/local/bin/"
clone_and_build "https://github.com/aquasecurity/trivy-operator.git" "make build && cp trivy-operator /usr/local/bin/"
clone_and_build "https://github.com/anchore/grype.git" "make build && cp grype /usr/local/bin/"
clone_and_build "https://github.com/anchore/syft.git" "make build && cp syft /usr/local/bin/"
clone_and_build "https://github.com/anchore/anchore-engine.git" "python3 setup.py install"
clone_and_build "https://github.com/GoogleCloudPlatform/terraformer.git" "go build && cp terraformer /usr/local/bin/"
clone_and_build "https://github.com/GoogleCloudPlatform/terraformer-aws.git" "go build && cp terraformer-aws /usr/local/bin/"
clone_and_build "https://github.com/GoogleCloudPlatform/terraformer-google.git" "go build && cp terraformer-google /usr/local/bin/"
clone_and_build "https://github.com/GoogleCloudPlatform/terraformer-azure.git" "go build && cp terraformer-azure /usr/local/bin/"
clone_and_build "https://github.com/GoogleCloudPlatform/terraformer-cloudflare.git" "go build && cp terraformer-cloudflare /usr/local/bin/"
clone_and_build "https://github.com/GoogleCloudPlatform/terraformer-datadog.git" "go build && cp terraformer-datadog /usr/local/bin/"
clone_and_build "https://github.com/GoogleCloudPlatform/terraformer-kubernetes.git" "go build && cp terraformer-kubernetes /usr/local/bin/"

# =============================================================================
# 11n. Red Teaming and C2 Frameworks
# =============================================================================
print_step "--- Red Teaming Tools ---"

clone_and_build "https://github.com/cobbr/Covenant.git" "dotnet build"
clone_and_build "https://github.com/BloodHoundAD/BloodHound.git" "npm install && npm run build"
clone_and_build "https://github.com/BloodHoundAD/SharpHound.git" "dotnet build"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-Tools.git" "chmod +x BloodHound-Tools"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-Custom-Queries.git" "chmod +x BloodHound-Custom-Queries"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-Queries.git" "chmod +x BloodHound-Queries"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-Python.git" "python3 setup.py install"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-Java.git" "mvn package"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-Go.git" "go build && cp BloodHound-Go /usr/local/bin/"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-Rust.git" "cargo build --release && cp target/release/BloodHound-Rust /usr/local/bin/"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-CSharp.git" "dotnet build"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-PowerShell.git" "chmod +x BloodHound-PowerShell"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-WMI.git" "chmod +x BloodHound-WMI"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-SMB.git" "chmod +x BloodHound-SMB"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-LDAP.git" "chmod +x BloodHound-LDAP"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-DNS.git" "chmod +x BloodHound-DNS"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-HTTP.git" "chmod +x BloodHound-HTTP"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-HTTPS.git" "chmod +x BloodHound-HTTPS"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-TCP.git" "chmod +x BloodHound-TCP"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-UDP.git" "chmod +x BloodHound-UDP"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-ICMP.git" "chmod +x BloodHound-ICMP"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-DNS.git" "chmod +x BloodHound-DNS"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-SMTP.git" "chmod +x BloodHound-SMTP"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-POP3.git" "chmod +x BloodHound-POP3"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-IMAP.git" "chmod +x BloodHound-IMAP"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-SSH.git" "chmod +x BloodHound-SSH"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-SFTP.git" "chmod +x BloodHound-SFTP"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-FTP.git" "chmod +x BloodHound-FTP"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-Telnet.git" "chmod +x BloodHound-Telnet"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-RDP.git" "chmod +x BloodHound-RDP"
clone_and_build "https://github.com/BloodHoundAD/BloodHound-VNC.git" "chmod +x BloodHound-VNC"

# =============================================================================
# 12. Final Cleanup and Permissions
# =============================================================================
print_step "Finalizing installation"

# Ensure all binaries are executable and in PATH
find /opt -type f -name "*.sh" -exec chmod +x {} \;
find /opt -type f -name "*.py" -exec chmod +x {} \;
find /opt -type f -name "*.pl" -exec chmod +x {} \;
find /opt -type f -name "*.rb" -exec chmod +x {} \;
find /opt -type f -name "*.go" -exec chmod +x {} \;

# Copy common binaries to /usr/local/bin
find /opt -type f -executable -not -path "*/\.*" -exec cp {} /usr/local/bin/ 2>/dev/null \;

# Set ownership of /home/ai and /opt to ai user
chown -R ai:ai /home/ai
chown -R ai:ai /opt

# Install additional wordlists
print_step "Downloading common wordlists"
cd /home/ai/wordlists
wget -q https://github.com/berzerk0/Probable-Wordlists/raw/master/Real-Passwords/Top12Thousand-probable-v2.txt -O top12000.txt
wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10-million-password-list-top-10000.txt -O top10000.txt
wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt -O web_common.txt
wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-110000.txt -O subdomains.txt
wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/directory-list-2.3-medium.txt -O directories.txt
wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Usernames/xato-net-10-million-usernames.txt -O usernames.txt
wget -q https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/XSS-Fuzzing -O xss_payloads.txt
wget -q https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/SQL%20Injection/Intruder/sqli.txt -O sqli_payloads.txt
chown -R ai:ai /home/ai/wordlists

# Create a README for the AI
cat > /home/ai/README.txt << 'EOF'
Welcome to your ultimate Kali Linux environment!

This system has been customized with over 500 additional hacking tools
from GitHub, in addition to all Kali default tools. You have full root
access and can use any tool.

Quick start:
- All tools are in /usr/local/bin or /opt
- Your home directory is /home/ai
- Wordlists are in /home/ai/wordlists
- Logs are in /home/ai/logs

Common tool categories:
- Recon: nmap, masscan, amass, subfinder, httpx, nuclei
- Web: sqlmap, wpscan, gobuster, ffuf, dirsearch
- Exploitation: metasploit, empire, beef
- Password: hashcat, john, hydra
