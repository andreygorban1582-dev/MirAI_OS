#!/bin/bash
set -e

VNC_PASSWORD="${VNC_PASSWORD:-mirai_vnc_change}"
DISPLAY=":1"

# Set VNC password
mkdir -p /root/.vnc
echo "${VNC_PASSWORD}" | vncpasswd -f > /root/.vnc/passwd
chmod 600 /root/.vnc/passwd

# Kill any existing VNC session
vncserver -kill ${DISPLAY} 2>/dev/null || true
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1 2>/dev/null || true

# Start VNC server
vncserver ${DISPLAY} \
    -geometry 1920x1080 \
    -depth 24 \
    -SecurityTypes VncAuth \
    -PasswordFile /root/.vnc/passwd

# Start noVNC websocket proxy
websockify --web=/usr/share/novnc/ 0.0.0.0:6901 localhost:5901 &

# Start Docker daemon (DinD)
if [ -S /var/run/docker.sock ]; then
    echo "[kali] Using host Docker socket"
else
    dockerd &
    sleep 2
fi

echo "[kali] VNC ready on :5901, noVNC on :6901"
echo "[kali] Password: ${VNC_PASSWORD}"

# Keep container running
tail -f /dev/null
