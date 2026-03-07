"""
MirAI OS — Kali Linux Tool Wrappers
Full access to Kali's penetration testing arsenal.
"Every tool in this lab is a weapon against SERN's network fortress."
"""
from __future__ import annotations

import asyncio
import logging
import shlex
from dataclasses import dataclass, field
from typing import Optional

from core.config import cfg

logger = logging.getLogger("mirai.tools.kali")

MAX_OUTPUT = 1024 * 512  # 512KB


@dataclass
class KaliResult:
    tool: str
    command: str
    stdout: str
    stderr: str
    exit_code: int
    success: bool
    duration_ms: int = 0

    @property
    def output(self) -> str:
        out = self.stdout
        if self.stderr:
            out += f"\n[STDERR]\n{self.stderr[:2000]}"
        return out


# ── Tool registry ─────────────────────────────────────────────────────────────

KALI_TOOLS = {
    # Information Gathering
    "nmap": {
        "desc": "Network scanner and port scanner",
        "binary": "nmap",
        "category": "information_gathering",
        "example": "nmap -sV -sC -O {target}",
    },
    "whois": {
        "desc": "Domain/IP ownership lookup",
        "binary": "whois",
        "category": "information_gathering",
        "example": "whois {target}",
    },
    "dig": {
        "desc": "DNS lookup tool",
        "binary": "dig",
        "category": "information_gathering",
        "example": "dig {target} ANY",
    },
    "theHarvester": {
        "desc": "Email and subdomain harvesting",
        "binary": "theHarvester",
        "category": "information_gathering",
        "example": "theHarvester -d {target} -b google",
    },
    "subfinder": {
        "desc": "Subdomain discovery",
        "binary": "subfinder",
        "category": "information_gathering",
        "example": "subfinder -d {target}",
    },
    "nikto": {
        "desc": "Web server vulnerability scanner",
        "binary": "nikto",
        "category": "web_applications",
        "example": "nikto -h {target}",
    },
    "gobuster": {
        "desc": "Directory/file and DNS brute-forcer",
        "binary": "gobuster",
        "category": "web_applications",
        "example": "gobuster dir -u {target} -w /usr/share/wordlists/dirb/common.txt",
    },
    "sqlmap": {
        "desc": "SQL injection detection and exploitation",
        "binary": "sqlmap",
        "category": "web_applications",
        "example": "sqlmap -u {target} --dbs",
    },
    "hydra": {
        "desc": "Online password brute-forcer",
        "binary": "hydra",
        "category": "password_attacks",
        "example": "hydra -l {user} -P {wordlist} {target} {service}",
    },
    "john": {
        "desc": "John the Ripper — offline password cracker",
        "binary": "john",
        "category": "password_attacks",
        "example": "john --wordlist={wordlist} {hashfile}",
    },
    "hashcat": {
        "desc": "GPU-accelerated password recovery",
        "binary": "hashcat",
        "category": "password_attacks",
        "example": "hashcat -m {mode} {hashfile} {wordlist}",
    },
    "aircrack-ng": {
        "desc": "Wireless security auditing suite",
        "binary": "aircrack-ng",
        "category": "wireless",
        "example": "aircrack-ng {capfile} -w {wordlist}",
    },
    "metasploit": {
        "desc": "Exploitation framework (msfconsole)",
        "binary": "msfconsole",
        "category": "exploitation",
        "example": "msfconsole -q -x '{commands}'",
    },
    "msfvenom": {
        "desc": "Payload generator",
        "binary": "msfvenom",
        "category": "exploitation",
        "example": "msfvenom -p {payload} LHOST={lhost} LPORT={lport} -f {format}",
    },
    "wireshark": {
        "desc": "Network protocol analyzer (tshark CLI)",
        "binary": "tshark",
        "category": "sniffing_spoofing",
        "example": "tshark -i {interface} -c 100",
    },
    "tcpdump": {
        "desc": "Packet capture tool",
        "binary": "tcpdump",
        "category": "sniffing_spoofing",
        "example": "tcpdump -i {interface} -w /tmp/capture.pcap",
    },
    "burpsuite": {
        "desc": "Web security testing (CLI headless proxy)",
        "binary": "burpsuite",
        "category": "web_applications",
        "example": "burpsuite --project-file={project}",
    },
    "netcat": {
        "desc": "TCP/UDP connection tool",
        "binary": "nc",
        "category": "post_exploitation",
        "example": "nc -lvnp {port}",
    },
    "curl": {
        "desc": "HTTP request tool",
        "binary": "curl",
        "category": "web_applications",
        "example": "curl -I {target}",
    },
    "binwalk": {
        "desc": "Firmware analysis tool",
        "binary": "binwalk",
        "category": "reverse_engineering",
        "example": "binwalk -e {file}",
    },
    "strings": {
        "desc": "Extract strings from binary",
        "binary": "strings",
        "category": "reverse_engineering",
        "example": "strings {file}",
    },
    "volatility": {
        "desc": "Memory forensics framework",
        "binary": "vol",
        "category": "forensics",
        "example": "vol -f {memfile} windows.pslist",
    },
}


class KaliToolRunner:
    """Execute Kali Linux tools safely with output capture."""

    def __init__(self) -> None:
        self.allowed_categories = cfg.kali_tools.get("allowed_categories", list(set(
            t["category"] for t in KALI_TOOLS.values()
        )))
        self.max_lines = int(cfg.kali_tools.get("output_max_lines", 500))

    def list_tools(self, category: Optional[str] = None) -> list[dict]:
        tools = []
        for name, info in KALI_TOOLS.items():
            if category and info["category"] != category:
                continue
            if info["category"] not in self.allowed_categories:
                continue
            tools.append({"name": name, **info})
        return tools

    def is_allowed(self, tool_name: str) -> bool:
        tool = KALI_TOOLS.get(tool_name)
        return tool is not None and tool["category"] in self.allowed_categories

    def is_available(self, tool_name: str) -> bool:
        import shutil
        tool = KALI_TOOLS.get(tool_name)
        if not tool:
            return False
        return shutil.which(tool["binary"]) is not None

    async def run(self, tool_name: str, args: str, timeout: int = 120) -> KaliResult:
        """Run a Kali tool with given arguments."""
        import time
        start = time.monotonic()

        if not self.is_allowed(tool_name):
            return KaliResult(
                tool=tool_name, command="",
                stdout="", stderr=f"Tool '{tool_name}' is not in allowed categories",
                exit_code=-1, success=False,
            )

        tool_info = KALI_TOOLS.get(tool_name, {})
        binary = tool_info.get("binary", tool_name)

        # Build full command
        if args.strip():
            full_cmd = f"{binary} {args}"
        else:
            full_cmd = binary

        logger.info(f"[KALI] Running: {full_cmd}")

        try:
            proc = await asyncio.create_subprocess_shell(
                full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return KaliResult(
                    tool=tool_name, command=full_cmd,
                    stdout="", stderr=f"Timeout after {timeout}s",
                    exit_code=-1, success=False,
                    duration_ms=int((time.monotonic() - start) * 1000),
                )

            stdout = stdout_b[:MAX_OUTPUT].decode("utf-8", errors="replace")
            stderr = stderr_b[:50000].decode("utf-8", errors="replace")

            # Truncate to max lines
            stdout_lines = stdout.splitlines()
            if len(stdout_lines) > self.max_lines:
                stdout = "\n".join(stdout_lines[:self.max_lines])
                stdout += f"\n[... {len(stdout_lines) - self.max_lines} more lines truncated ...]"

            return KaliResult(
                tool=tool_name,
                command=full_cmd,
                stdout=stdout,
                stderr=stderr,
                exit_code=proc.returncode,
                success=proc.returncode == 0,
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        except FileNotFoundError:
            return KaliResult(
                tool=tool_name, command=full_cmd,
                stdout="", stderr=f"Tool '{binary}' not found. Install with: sudo apt-get install {tool_name}",
                exit_code=127, success=False,
            )
        except Exception as e:
            return KaliResult(
                tool=tool_name, command=full_cmd,
                stdout="", stderr=str(e),
                exit_code=-1, success=False,
            )

    async def run_raw(self, command: str, timeout: int = 120) -> KaliResult:
        """Run any arbitrary shell command (full Kali access)."""
        import time
        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            stdout = stdout_b[:MAX_OUTPUT].decode("utf-8", errors="replace")
            stderr = stderr_b[:50000].decode("utf-8", errors="replace")
            return KaliResult(
                tool="raw",
                command=command,
                stdout=stdout,
                stderr=stderr,
                exit_code=proc.returncode,
                success=proc.returncode == 0,
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except asyncio.TimeoutError:
            return KaliResult(
                tool="raw", command=command,
                stdout="", stderr=f"Timeout after {timeout}s",
                exit_code=-1, success=False,
            )


# Global singleton
kali = KaliToolRunner()
