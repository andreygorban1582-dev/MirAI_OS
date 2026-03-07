"""
MirAI OS — SSH Agent
Connects to remote nodes (GitHub Codespaces, servers) via SSH.
Executes commands, transfers files, and manages distributed tasks.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from agents.base_agent import AgentTask, AgentResult, BaseAgent, Tool, ToolResult
from core.config import cfg

logger = logging.getLogger("mirai.agent.ssh")


class SSHConnection:
    """Single SSH connection to a remote node."""

    def __init__(self, host: str, port: int, user: str, key_path: Optional[str] = None, password: Optional[str] = None) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.key_path = key_path
        self.password = password
        self._client = None

    def connect(self) -> None:
        import paramiko
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        kwargs = {
            "hostname": self.host,
            "port": self.port,
            "username": self.user,
            "timeout": 30,
        }
        if self.key_path:
            kwargs["key_filename"] = str(Path(self.key_path).expanduser())
        elif self.password:
            kwargs["password"] = self.password
        self._client.connect(**kwargs)

    def exec(self, command: str, timeout: int = 120) -> tuple[str, str, int]:
        """Execute command. Returns (stdout, stderr, exit_code)."""
        if not self._client:
            self.connect()
        stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")[:500000]
        err = stderr.read().decode("utf-8", errors="replace")[:50000]
        code = stdout.channel.recv_exit_status()
        return out, err, code

    def put_file(self, local_path: str, remote_path: str) -> None:
        sftp = self._client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()

    def get_file(self, remote_path: str, local_path: str) -> None:
        sftp = self._client.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None


class SSHAgent(BaseAgent):
    name = "ssh_agent"
    description = "Execute commands and manage files on remote SSH nodes (Codespaces, servers)"

    def __init__(self) -> None:
        self._connections: dict[str, SSHConnection] = {}
        super().__init__()

    def _register_tools(self) -> None:
        self.register_tool(Tool("exec_remote", "Execute a command on a remote node", self._exec_remote))
        self.register_tool(Tool("upload_file", "Upload a file to a remote node", self._upload_file))
        self.register_tool(Tool("download_file", "Download a file from a remote node", self._download_file))
        self.register_tool(Tool("connect_node", "Connect to a named node from config", self._connect_node))
        self.register_tool(Tool("add_node", "Dynamically add a new SSH node", self._add_node))
        self.register_tool(Tool("list_nodes", "List all configured remote nodes", self._list_nodes))
        self.register_tool(Tool("disconnect_node", "Disconnect from a node", self._disconnect_node))

    async def execute(self, task: AgentTask) -> AgentResult:
        action = task.params.get("action", "exec_remote")
        result = await self.run_tool(action, **task.params)
        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            success=result.success,
            output=result.output,
            error=result.error,
            duration_ms=result.duration_ms,
        )

    def _get_or_connect(self, node_id: str) -> SSHConnection:
        if node_id in self._connections:
            return self._connections[node_id]
        node = cfg.get_node(node_id)
        if not node:
            raise ValueError(f"Node '{node_id}' not found in config")
        if not node.get("host"):
            raise ValueError(f"Node '{node_id}' has no host configured")
        conn = SSHConnection(
            host=node["host"],
            port=int(node.get("port", 22)),
            user=node.get("user", "root"),
            key_path=node.get("ssh_key"),
        )
        conn.connect()
        self._connections[node_id] = conn
        return conn

    async def _exec_remote(self, node_id: str = "codespace-1", command: str = "echo hello", timeout: int = 120, **_) -> ToolResult:
        try:
            conn = await asyncio.to_thread(self._get_or_connect, node_id)
            stdout, stderr, code = await asyncio.to_thread(conn.exec, command, timeout)
            output = stdout
            if stderr:
                output += f"\nSTDERR:\n{stderr}"
            return ToolResult(success=(code == 0), output=output, data={"exit_code": code})
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _upload_file(self, node_id: str = "", local_path: str = "", remote_path: str = "", **_) -> ToolResult:
        try:
            conn = await asyncio.to_thread(self._get_or_connect, node_id)
            await asyncio.to_thread(conn.put_file, local_path, remote_path)
            return ToolResult(success=True, output=f"Uploaded {local_path} → {node_id}:{remote_path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _download_file(self, node_id: str = "", remote_path: str = "", local_path: str = "", **_) -> ToolResult:
        try:
            conn = await asyncio.to_thread(self._get_or_connect, node_id)
            await asyncio.to_thread(conn.get_file, remote_path, local_path)
            return ToolResult(success=True, output=f"Downloaded {node_id}:{remote_path} → {local_path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _connect_node(self, node_id: str = "", **_) -> ToolResult:
        try:
            conn = await asyncio.to_thread(self._get_or_connect, node_id)
            return ToolResult(success=True, output=f"Connected to {node_id}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _add_node(self, node_id: str = "", host: str = "", port: int = 22, user: str = "root", ssh_key: str = "", **_) -> ToolResult:
        """Dynamically register a new SSH node."""
        try:
            conn = SSHConnection(host=host, port=port, user=user, key_path=ssh_key or None)
            await asyncio.to_thread(conn.connect)
            self._connections[node_id] = conn

            # Persist to nodes.yaml
            import yaml
            nodes_path = Path(__file__).parent.parent / "config" / "nodes.yaml"
            with open(nodes_path) as f:
                data = yaml.safe_load(f)
            data.setdefault("nodes", []).append({
                "id": node_id,
                "label": f"Dynamic Node: {node_id}",
                "host": host,
                "port": port,
                "user": user,
                "ssh_key": ssh_key or None,
                "role": "worker",
                "capabilities": ["code_execution"],
                "status": "active",
            })
            with open(nodes_path, "w") as f:
                yaml.dump(data, f)

            return ToolResult(success=True, output=f"Node {node_id} ({host}) added and connected!")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _list_nodes(self, **_) -> ToolResult:
        lines = []
        for node in cfg.nodes:
            status = "CONNECTED" if node["id"] in self._connections else node.get("status", "inactive").upper()
            lines.append(f"▸ {node['id']} [{status}] — {node.get('label', node['id'])}")
        return ToolResult(success=True, output="\n".join(lines) or "No nodes configured")

    async def _disconnect_node(self, node_id: str = "", **_) -> ToolResult:
        if node_id in self._connections:
            self._connections[node_id].close()
            del self._connections[node_id]
            return ToolResult(success=True, output=f"Disconnected from {node_id}")
        return ToolResult(success=False, output="", error=f"Not connected to {node_id}")
