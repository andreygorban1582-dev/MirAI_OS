FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive

# ─── Core security tools + XFCE desktop ──────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        nmap \
        gobuster \
        dirb \
        dirbuster \
        nuclei \
        nikto \
        sqlmap \
        hydra \
        john \
        hashcat \
        aircrack-ng \
        metasploit-framework \
        wireshark \
        tcpdump \
        netcat-traditional \
        curl \
        wget \
        git \
        python3 \
        python3-pip \
        ruby \
        perl \
        # XFCE desktop environment
        xfce4 \
        xfce4-goodies \
        xterm \
        dbus-x11 \
        # VNC server
        tigervnc-standalone-server \
        tigervnc-tools \
        novnc \
        websockify \
        # Docker-in-Docker
        docker.io \
        # misc
        sudo \
        procps \
        net-tools \
        iputils-ping \
        file \
        vim \
    && rm -rf /var/lib/apt/lists/*

# ─── Install Go tools (nuclei, subfinder, amass) ─────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends golang-go && \
    rm -rf /var/lib/apt/lists/* && \
    go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest 2>/dev/null || true && \
    go install github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest 2>/dev/null || true

# ─── VNC / noVNC setup ───────────────────────────────────────────────────────
RUN mkdir -p /root/.vnc && \
    echo "#!/bin/bash\nxrdb \$HOME/.Xresources\nstartxfce4 &" > /root/.vnc/xstartup && \
    chmod +x /root/.vnc/xstartup

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5901 6901

ENTRYPOINT ["/entrypoint.sh"]
