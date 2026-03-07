"""
MirAI OS — Compute Node Manager
Manages the distributed network of Legion Go + GitHub Codespaces nodes.
Handles task distribution, health checks, and dynamic node registration.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from core.config import cfg

logger = logging.getLogger("mirai.network.nodes")


@dataclass
class NodeHealth:
    node_id: str
    online: bool
    latency_ms: float = 0.0
    last_check: float = field(default_factory=time.time)
    cpu_load: Optional[float] = None
    mem_free_mb: Optional[float] = None


class NodeManager:
    """Tracks health and distributes tasks across compute nodes."""

    def __init__(self) -> None:
        self._health: dict[str, NodeHealth] = {}
        self._ssh_agent = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    def _get_ssh(self):
        if self._ssh_agent is None:
            from agents.ssh_agent import SSHAgent
            self._ssh_agent = SSHAgent()
        return self._ssh_agent

    async def start_heartbeat(self, interval: int = 30) -> None:
        """Start periodic health checks on all nodes."""
        async def _loop():
            while True:
                await self.check_all_nodes()
                await asyncio.sleep(interval)
        self._heartbeat_task = asyncio.create_task(_loop())
        logger.info("Node heartbeat started.")

    async def check_node(self, node_id: str) -> NodeHealth:
        node = cfg.get_node(node_id)
        if not node:
            return NodeHealth(node_id=node_id, online=False)

        if node["host"] in ("localhost", "", None):
            # Local node — always online
            health = NodeHealth(node_id=node_id, online=True, latency_ms=0.0)
            self._health[node_id] = health
            return health

        start = time.monotonic()
        try:
            ssh = self._get_ssh()
            result = await asyncio.wait_for(
                ssh.run_tool("exec_remote", node_id=node_id, command="echo ok && free -m | awk 'NR==2{print $4}'"),
                timeout=10,
            )
            latency = (time.monotonic() - start) * 1000

            lines = (result.output or "").strip().splitlines()
            mem_free = float(lines[1]) if len(lines) > 1 else None

            health = NodeHealth(
                node_id=node_id,
                online=result.success,
                latency_ms=latency,
                mem_free_mb=mem_free,
            )
        except Exception as e:
            logger.warning(f"Node {node_id} health check failed: {e}")
            health = NodeHealth(node_id=node_id, online=False)

        self._health[node_id] = health
        return health

    async def check_all_nodes(self) -> dict[str, NodeHealth]:
        remote_nodes = [n for n in cfg.nodes if n.get("host") not in ("localhost", "", None)]
        tasks = [self.check_node(n["id"]) for n in remote_nodes]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Local node always healthy
        self._health["legion-go"] = NodeHealth(node_id="legion-go", online=True)
        return {r.node_id: r for r in results if isinstance(r, NodeHealth)}

    def get_best_node(self, capability: str) -> Optional[str]:
        """Return the healthiest node with the given capability."""
        candidates = []
        for node in cfg.nodes:
            if capability not in node.get("capabilities", []):
                continue
            health = self._health.get(node["id"])
            if health and health.online:
                candidates.append((health.latency_ms, node["id"]))
        if not candidates:
            return None
        return sorted(candidates)[0][1]  # lowest latency

    async def run_on_node(self, node_id: str, command: str, timeout: int = 120) -> tuple[bool, str]:
        """Run a shell command on a specific node."""
        if node_id == "legion-go":
            from tools.kali_tools import kali
            result = await kali.run_raw(command)
            return result.success, result.output or result.stderr

        ssh = self._get_ssh()
        result = await ssh.run_tool(
            "exec_remote",
            node_id=node_id,
            command=command,
            timeout=timeout,
        )
        return result.success, result.output or ""

    async def distribute_task(self, command: str, capability: str = "code_execution", timeout: int = 120) -> tuple[bool, str, str]:
        """Find best node and run command. Returns (success, output, node_used)."""
        node_id = self.get_best_node(capability) or "legion-go"
        logger.info(f"Distributing task to {node_id}: {command[:60]}")
        success, output = await self.run_on_node(node_id, command, timeout)
        return success, output, node_id

    def status_summary(self) -> list[dict]:
        result = []
        for node in cfg.nodes:
            health = self._health.get(node["id"])
            result.append({
                "id": node["id"],
                "label": node.get("label", node["id"]),
                "online": health.online if health else False,
                "latency_ms": health.latency_ms if health else None,
            })
        return result

    async def register_codespace(self, node_id: str, host: str, ssh_key_path: str, user: str = "codespace") -> bool:
        """Register a GitHub Codespace as a compute node."""
        try:
            # Update config
            import yaml
            from pathlib import Path
            nodes_path = Path(__file__).parent.parent / "config" / "nodes.yaml"
            with open(nodes_path) as f:
                data = yaml.safe_load(f)

            # Update or add node
            for node in data.get("nodes", []):
                if node["id"] == node_id:
                    node["host"] = host
                    node["ssh_key"] = ssh_key_path
                    node["user"] = user
                    node["status"] = "active"
                    break
            else:
                data.setdefault("nodes", []).append({
                    "id": node_id,
                    "label": f"Codespace: {node_id}",
                    "host": host,
                    "port": 22,
                    "user": user,
                    "ssh_key": ssh_key_path,
                    "role": "worker",
                    "capabilities": ["code_execution", "web_browsing"],
                    "status": "active",
                })

            with open(nodes_path, "w") as f:
                yaml.dump(data, f)

            # Reload config
            cfg.__init__()

            # Test connection
            health = await self.check_node(node_id)
            logger.info(f"Codespace {node_id} registered. Online: {health.online}")
            return health.online
        except Exception as e:
            logger.error(f"Codespace registration failed: {e}")
            return False


# Global singleton
node_manager = NodeManager()
