"""
MirAI OS — Self-Modification Agent
Allows MirAI to add capabilities, inject code, manage keys,
and modify its own GitHub repository.
"Future Gadget #8 upgrades itself. This is the choice of Steins Gate."
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from agents.base_agent import AgentTask, AgentResult, BaseAgent, Tool, ToolResult
from core.config import cfg

logger = logging.getLogger("mirai.agent.self_modify")

ROOT = Path(__file__).parent.parent
CAPABILITIES_DIR = ROOT / "data" / "capabilities"


class SelfModifyAgent(BaseAgent):
    name = "self_modify_agent"
    description = "Modify MirAI's own codebase, inject new capabilities, manage API keys and SSH keys, commit to GitHub"

    def _register_tools(self) -> None:
        self.register_tool(Tool("inject_capability", "Add a new Python capability file", self._inject_capability))
        self.register_tool(Tool("add_api_key", "Add a new API key to .env", self._add_api_key))
        self.register_tool(Tool("add_ssh_key", "Save a new SSH key for node access", self._add_ssh_key))
        self.register_tool(Tool("commit_and_push", "Commit current changes to GitHub", self._commit_push))
        self.register_tool(Tool("pull_latest", "Pull latest changes from GitHub", self._pull_latest))
        self.register_tool(Tool("list_capabilities", "List all injected capabilities", self._list_capabilities))
        self.register_tool(Tool("load_capability", "Dynamically load an injected capability", self._load_capability))
        self.register_tool(Tool("update_config", "Update a settings.yaml value", self._update_config))

    async def execute(self, task: AgentTask) -> AgentResult:
        action = task.params.get("action", "inject_capability")
        result = await self.run_tool(action, **task.params)
        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            success=result.success,
            output=result.output,
            error=result.error,
            duration_ms=result.duration_ms,
        )

    async def _inject_capability(self, name: str = "", code: str = "", description: str = "", **_) -> ToolResult:
        """Save a new Python module to data/capabilities/ and register it."""
        CAPABILITIES_DIR.mkdir(parents=True, exist_ok=True)
        if not name:
            return ToolResult(success=False, output="", error="Capability name required")

        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        cap_file = CAPABILITIES_DIR / f"{safe_name}.py"

        header = f'''"""
MirAI OS — Injected Capability: {name}
Description: {description}
Auto-injected by self_modify_agent.
"""
'''
        cap_file.write_text(header + "\n" + code)

        # Create __init__.py if missing
        init = CAPABILITIES_DIR / "__init__.py"
        if not init.exists():
            init.write_text("# MirAI OS — Injected capabilities package\n")

        return ToolResult(
            success=True,
            output=f"Capability '{name}' saved to {cap_file}\nReady to load with load_capability.",
        )

    async def _add_api_key(self, key_name: str = "", key_value: str = "", **_) -> ToolResult:
        """Append a new API key to .env file."""
        env_path = ROOT / ".env"
        if not env_path.exists():
            # Create from template
            template = ROOT / "config" / ".env.example"
            if template.exists():
                import shutil
                shutil.copy(template, env_path)
            else:
                env_path.write_text("")

        # Check if key already exists
        content = env_path.read_text()
        if f"{key_name}=" in content:
            # Update existing
            lines = content.splitlines()
            new_lines = []
            for line in lines:
                if line.startswith(f"{key_name}="):
                    new_lines.append(f"{key_name}={key_value}")
                else:
                    new_lines.append(line)
            env_path.write_text("\n".join(new_lines) + "\n")
            action = "Updated"
        else:
            # Append new key
            with open(env_path, "a") as f:
                f.write(f"\n# Added by MirAI self-modification\n{key_name}={key_value}\n")
            action = "Added"

        # Reload env
        from dotenv import load_dotenv
        load_dotenv(env_path, override=True)

        return ToolResult(
            success=True,
            output=f"{action} API key: {key_name} (value masked for security)",
        )

    async def _add_ssh_key(self, key_name: str = "", key_content: str = "", node_id: str = "", **_) -> ToolResult:
        """Save an SSH private key to ~/.ssh/"""
        ssh_dir = Path.home() / ".ssh"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        key_path = ssh_dir / (key_name or f"mirai_{node_id}_key")
        key_path.write_text(key_content)
        key_path.chmod(0o600)

        return ToolResult(
            success=True,
            output=f"SSH key saved: {key_path}\nUse this path when adding a node.",
        )

    async def _commit_push(self, message: str = "MirAI OS self-update", **_) -> ToolResult:
        """Commit all changes and push to GitHub."""
        try:
            import subprocess
            cmds = [
                ["git", "-C", str(ROOT), "add", "-A"],
                ["git", "-C", str(ROOT), "commit", "-m", message, "--author=MirAI-OS <mirai@futurelab>"],
                ["git", "-C", str(ROOT), "push", "-u", "origin", "HEAD"],
            ]
            output_lines = []
            for cmd in cmds:
                result = subprocess.run(cmd, capture_output=True, text=True)
                output_lines.append(f"$ {' '.join(cmd[3:])}")
                if result.stdout:
                    output_lines.append(result.stdout.strip())
                if result.returncode != 0 and result.stderr:
                    if "nothing to commit" in result.stderr.lower():
                        output_lines.append("(nothing to commit)")
                        continue
                    return ToolResult(success=False, output="\n".join(output_lines), error=result.stderr)

            return ToolResult(success=True, output="\n".join(output_lines))
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _pull_latest(self, **_) -> ToolResult:
        try:
            import subprocess
            result = subprocess.run(
                ["git", "-C", str(ROOT), "pull", "origin", "main"],
                capture_output=True, text=True,
            )
            return ToolResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _list_capabilities(self, **_) -> ToolResult:
        CAPABILITIES_DIR.mkdir(parents=True, exist_ok=True)
        caps = [f for f in CAPABILITIES_DIR.glob("*.py") if f.name != "__init__.py"]
        if not caps:
            return ToolResult(success=True, output="No injected capabilities yet.")
        lines = [f"▸ {c.stem} ({c.stat().st_size} bytes)" for c in sorted(caps)]
        return ToolResult(success=True, output="\n".join(lines))

    async def _load_capability(self, name: str = "", **_) -> ToolResult:
        """Dynamically import an injected capability module."""
        import importlib.util
        cap_file = CAPABILITIES_DIR / f"{name}.py"
        if not cap_file.exists():
            return ToolResult(success=False, output="", error=f"Capability '{name}' not found")
        try:
            spec = importlib.util.spec_from_file_location(f"capabilities.{name}", cap_file)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return ToolResult(success=True, output=f"Capability '{name}' loaded successfully", data=mod)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _update_config(self, key_path: str = "", value: str = "", **_) -> ToolResult:
        """Update a dot-path key in settings.yaml. E.g. key_path='llm.temperature' value='0.9'"""
        try:
            import yaml
            cfg_file = ROOT / "config" / "settings.yaml"
            with open(cfg_file) as f:
                data = yaml.safe_load(f)

            keys = key_path.split(".")
            node = data
            for k in keys[:-1]:
                node = node.setdefault(k, {})
            node[keys[-1]] = yaml.safe_load(value)

            with open(cfg_file, "w") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

            return ToolResult(success=True, output=f"Config updated: {key_path} = {value}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
