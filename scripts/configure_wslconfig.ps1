# ============================================================
#  MirAI OS — Windows .wslconfig Generator
#  Run this in PowerShell on Windows to optimize WSL2
#  for the Legion Go Z1 Extreme.
#  El Psy Kongroo.
# ============================================================

$wslconfigPath = "$env:USERPROFILE\.wslconfig"

$config = @"
[wsl2]
# MirAI OS — Legion Go Z1 Extreme optimization
# 14GB RAM for WSL (leave 2GB for Windows + AMD GPU)
memory=14GB

# Use all 8 cores of Z1 Extreme
processors=8

# Large page file for heavy operations
pageReportingEnabled=true

# Enable localhost forwarding (for Telegram bot local dev)
localhostForwarding=true

# Fast I/O for SSD
# Swap is managed inside WSL (128GB swap file)
swap=0

# Nested virtualization for advanced tools
nestedVirtualization=true

# DNS
dnsTunneling=true

# firewall
firewall=true
"@

Write-Host "[FUTURE GADGET LAB] Writing .wslconfig to $wslconfigPath ..."
Set-Content -Path $wslconfigPath -Value $config
Write-Host "[✓] .wslconfig written."
Write-Host ""
Write-Host "Restart WSL2 to apply: wsl --shutdown"
Write-Host "Then: wsl -d kali-linux"
Write-Host ""
Write-Host "El Psy Kongroo."
