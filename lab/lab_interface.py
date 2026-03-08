"""
MirAI_OS Lab — Comprehensive AI Experimentation Interface

The Lab provides a unified workspace for:
- LLM chat experiments
- Autonomous agent runs
- Voice I/O testing
- Context optimizer dashboard
- Embedding explorer
- Prompt engineering tools
- Hardware monitor (Legion Go)
- Kali integration console
- Self-modification interface
- Code execution sandbox
- Fine-tuning experiments
- Model comparison
- Memory/vector store browser
- Codespace SSH terminal
"""
from __future__ import annotations

import asyncio
from typing import Optional


class Lab:
    """
    MirAI_OS Lab — central hub for all AI experiments and tools.

    When running with Gradio, call Lab().launch() to start the web UI.
    All features are also accessible programmatically via their respective
    async methods.
    """

    def __init__(self) -> None:
        from config.settings import settings  # noqa: PLC0415
        self.settings = settings
        self._demo = None  # Gradio Blocks instance

    # ------------------------------------------------------------------
    # Programmatic API
    # ------------------------------------------------------------------

    async def chat(self, message: str, history: list | None = None) -> str:
        """Run a single LLM chat turn."""
        from core.llm_engine import LLMEngine  # noqa: PLC0415
        async with LLMEngine() as engine:
            return await engine.chat(message, history=history)

    async def run_agent(self, task: str) -> str:
        """Execute an autonomous agent task."""
        from core.agent_flow import AgentFlow  # noqa: PLC0415
        agent = AgentFlow()
        return await agent.run(task)

    async def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text."""
        from voice.voice_io import VoiceIO  # noqa: PLC0415
        v = VoiceIO()
        return await v.transcribe(audio_path)

    async def speak(self, text: str, output_path: Optional[str] = None) -> Optional[str]:
        """Convert text to speech."""
        from voice.voice_io import VoiceIO  # noqa: PLC0415
        v = VoiceIO()
        return await v.speak(text, output_path)

    def hardware_status(self) -> dict:
        """Return current hardware status dict."""
        from core.context_optimizer import optimizer  # noqa: PLC0415
        snap = optimizer.get_snapshot()
        budget = optimizer.get_budget()
        return {
            "platform": snap.platform,
            "ram_total_gb": snap.ram_total_gb,
            "ram_available_gb": snap.ram_available_gb,
            "ram_used_pct": snap.ram_used_pct,
            "gpu": snap.gpu_name,
            "gpu_vram_mb": snap.gpu_vram_mb,
            "is_legion_go": snap.is_legion_go,
            "budget_max_tokens": budget.max_tokens,
            "budget_batch_size": budget.batch_size,
            "budget_gpu_layers": budget.gpu_layers,
        }

    # ------------------------------------------------------------------
    # Gradio Web UI
    # ------------------------------------------------------------------

    def _build_gradio(self):
        """Build the Gradio Blocks demo with all lab tabs."""
        try:
            import gradio as gr  # noqa: PLC0415
        except ImportError:
            raise ImportError(
                "gradio is required for the Lab web UI. Install it with: pip install gradio"
            )

        from core.context_optimizer import optimizer  # noqa: PLC0415
        from core.llm_engine import LLMEngine  # noqa: PLC0415
        from core.agent_flow import AgentFlow  # noqa: PLC0415

        # ---- Helpers ----

        def _hw_text() -> str:
            return optimizer.summary()

        async def _chat_fn(message: str, history: list) -> tuple[list, str]:
            async with LLMEngine() as engine:
                reply = await engine.chat(message, history=[
                    {"role": r, "content": c}
                    for pair in history
                    for r, c in [("user", pair[0]), ("assistant", pair[1])]
                ])
            history.append([message, reply])
            return history, ""

        async def _agent_fn(task: str) -> str:
            agent = AgentFlow()
            return await agent.run(task)

        async def _speak_fn(text: str) -> Optional[str]:
            from voice.voice_io import VoiceIO  # noqa: PLC0415
            v = VoiceIO()
            return await v.speak(text)

        async def _transcribe_fn(audio) -> str:
            if audio is None:
                return ""
            from voice.voice_io import VoiceIO  # noqa: PLC0415
            v = VoiceIO()
            return await v.transcribe(audio)

        def _self_mod_fn(instruction: str) -> str:
            from system.self_modification import SelfModification  # noqa: PLC0415
            sm = SelfModification()
            return sm.apply_instruction(instruction)

        def _kali_fn(command: str) -> str:
            from system.kali_integration import KaliIntegration  # noqa: PLC0415
            ki = KaliIntegration()
            return ki.run_command(command)

        async def _code_sandbox_fn(code: str) -> str:
            from core.agent_flow import _tool_python  # noqa: PLC0415
            return await _tool_python(code)

        def _model_compare_fn(prompt: str, model_a: str, model_b: str) -> tuple[str, str]:
            async def _run() -> tuple[str, str]:
                async with LLMEngine(model=model_a) as ea, LLMEngine(model=model_b) as eb:
                    a, b = await asyncio.gather(
                        ea.chat(prompt), eb.chat(prompt)
                    )
                return a, b
            return asyncio.run(_run())

        # ---- Build UI ----

        with gr.Blocks(
            title="MirAI_OS Lab",
            theme=gr.themes.Soft(),
            css="""
                .mirai-header { font-size: 2rem; font-weight: bold; color: #7c3aed; }
                .tab-label { font-weight: 600; }
            """,
        ) as demo:
            gr.HTML(
                '<div class="mirai-header">🧠 MirAI_OS Lab</div>'
                '<p>Advanced AI experimentation platform — optimised for Legion Go</p>'
            )

            with gr.Tabs():

                # ── Tab 1: Chat ──────────────────────────────────────
                with gr.Tab("💬 Chat"):
                    chatbot = gr.Chatbot(label="MirAI Chat", height=400)
                    with gr.Row():
                        chat_input = gr.Textbox(
                            placeholder="Talk to MirAI…", scale=8, show_label=False
                        )
                        chat_send = gr.Button("Send", scale=1, variant="primary")
                    chat_send.click(
                        _chat_fn, [chat_input, chatbot], [chatbot, chat_input]
                    )
                    chat_input.submit(
                        _chat_fn, [chat_input, chatbot], [chatbot, chat_input]
                    )

                # ── Tab 2: Autonomous Agent ──────────────────────────
                with gr.Tab("🤖 Agent"):
                    agent_task = gr.Textbox(
                        label="Task",
                        placeholder="Describe a multi-step task for the agent…",
                        lines=3,
                    )
                    agent_run_btn = gr.Button("▶ Run Agent", variant="primary")
                    agent_output = gr.Textbox(label="Result", lines=10, interactive=False)
                    agent_run_btn.click(_agent_fn, agent_task, agent_output)

                # ── Tab 3: Voice I/O ─────────────────────────────────
                with gr.Tab("🎙 Voice I/O"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### Speech-to-Text")
                            audio_input = gr.Audio(
                                sources=["microphone", "upload"],
                                type="filepath",
                                label="Record or upload audio",
                            )
                            stt_btn = gr.Button("Transcribe")
                            stt_output = gr.Textbox(label="Transcript", interactive=False)
                            stt_btn.click(_transcribe_fn, audio_input, stt_output)

                        with gr.Column():
                            gr.Markdown("### Text-to-Speech (Sesame CSM)")
                            tts_input = gr.Textbox(
                                label="Text", placeholder="Enter text to speak…"
                            )
                            tts_btn = gr.Button("Speak")
                            tts_output = gr.Audio(label="Audio output")
                            tts_btn.click(_speak_fn, tts_input, tts_output)

                # ── Tab 4: Hardware Monitor ──────────────────────────
                with gr.Tab("🖥 Hardware Monitor"):
                    hw_display = gr.Textbox(
                        label="System Status",
                        value=_hw_text,
                        lines=8,
                        interactive=False,
                    )
                    refresh_btn = gr.Button("🔄 Refresh")
                    refresh_btn.click(_hw_text, outputs=hw_display)

                    gr.Markdown("### Legion Go AI Budget")
                    budget_json = gr.JSON(value=self.hardware_status)
                    refresh_btn.click(self.hardware_status, outputs=budget_json)

                # ── Tab 5: Code Sandbox ──────────────────────────────
                with gr.Tab("🐍 Code Sandbox"):
                    gr.Markdown(
                        "Execute Python code in a local sandbox. "
                        "Assign `result` to capture a return value."
                    )
                    code_input = gr.Code(
                        language="python",
                        label="Python Code",
                        value='result = sum(range(100))\nprint(f"Sum: {result}")',
                    )
                    code_run_btn = gr.Button("▶ Run", variant="primary")
                    code_output = gr.Textbox(label="Output", lines=6, interactive=False)
                    code_run_btn.click(_code_sandbox_fn, code_input, code_output)

                # ── Tab 6: Prompt Engineering ────────────────────────
                with gr.Tab("✍ Prompt Engineering"):
                    gr.Markdown("Craft and test system prompts with live preview.")
                    with gr.Row():
                        sys_prompt = gr.Textbox(
                            label="System Prompt",
                            lines=5,
                            value="You are a helpful AI assistant.",
                        )
                        user_prompt = gr.Textbox(
                            label="User Message",
                            lines=5,
                            placeholder="Enter your message…",
                        )
                    pe_run_btn = gr.Button("▶ Test Prompt", variant="primary")
                    pe_output = gr.Textbox(label="Response", lines=8, interactive=False)

                    async def _pe_fn(sys_p: str, user_p: str) -> str:
                        async with LLMEngine(system_prompt=sys_p) as engine:
                            return await engine.chat(user_p)

                    pe_run_btn.click(_pe_fn, [sys_prompt, user_prompt], pe_output)

                # ── Tab 7: Model Comparison ──────────────────────────
                with gr.Tab("⚖ Model Comparison"):
                    gr.Markdown("Compare two models side-by-side.")
                    with gr.Row():
                        mc_model_a = gr.Textbox(
                            label="Model A",
                            value="mistralai/mistral-7b-instruct",
                        )
                        mc_model_b = gr.Textbox(
                            label="Model B",
                            value="openai/gpt-4o-mini",
                        )
                    mc_prompt = gr.Textbox(
                        label="Prompt",
                        placeholder="Enter a prompt to compare…",
                        lines=3,
                    )
                    mc_run_btn = gr.Button("▶ Compare", variant="primary")
                    with gr.Row():
                        mc_out_a = gr.Textbox(label="Model A Response", lines=8, interactive=False)
                        mc_out_b = gr.Textbox(label="Model B Response", lines=8, interactive=False)
                    mc_run_btn.click(
                        _model_compare_fn,
                        [mc_prompt, mc_model_a, mc_model_b],
                        [mc_out_a, mc_out_b],
                    )

                # ── Tab 8: Self-Modification ─────────────────────────
                with gr.Tab("🔧 Self-Modification"):
                    gr.Markdown(
                        "⚠️ **Advanced** — instruct MirAI to modify its own codebase."
                    )
                    sm_instruction = gr.Textbox(
                        label="Modification Instruction",
                        placeholder="e.g. Add a new tool to the agent that fetches URLs",
                        lines=4,
                    )
                    sm_run_btn = gr.Button("Apply Modification", variant="stop")
                    sm_output = gr.Textbox(label="Result", lines=6, interactive=False)
                    sm_run_btn.click(_self_mod_fn, sm_instruction, sm_output)

                # ── Tab 9: Kali Integration ──────────────────────────
                with gr.Tab("💀 Kali Console"):
                    gr.Markdown(
                        "Run commands on a connected Kali Linux instance via SSH.\n\n"
                        "⚠️ Configure `KALI_SSH_*` in `.env` first."
                    )
                    kali_cmd = gr.Textbox(
                        label="Command",
                        placeholder="e.g. nmap -sV 192.168.1.1",
                    )
                    kali_run_btn = gr.Button("▶ Execute", variant="stop")
                    kali_output = gr.Textbox(
                        label="Output", lines=10, interactive=False
                    )
                    kali_run_btn.click(_kali_fn, kali_cmd, kali_output)

                # ── Tab 10: Codespace SSH ────────────────────────────
                with gr.Tab("🔌 Codespace SSH"):
                    gr.Markdown(
                        "Connect to a GitHub Codespace via SSH.\n\n"
                        "Configure `CODESPACE_SSH_*` in `.env`."
                    )

                    def _ssh_fn(cmd: str) -> str:
                        from system.codespace_ssh import CodespaceSSH  # noqa: PLC0415
                        ssh = CodespaceSSH()
                        return ssh.run(cmd)

                    ssh_cmd = gr.Textbox(
                        label="Command", placeholder="e.g. ls -la /workspace"
                    )
                    ssh_run_btn = gr.Button("▶ Run", variant="primary")
                    ssh_output = gr.Textbox(
                        label="Output", lines=10, interactive=False
                    )
                    ssh_run_btn.click(_ssh_fn, ssh_cmd, ssh_output)

        return demo

    def launch(
        self,
        share: bool = False,
        port: Optional[int] = None,
        server_name: str = "0.0.0.0",
    ) -> None:
        """Launch the Lab Gradio web interface."""
        self._demo = self._build_gradio()
        self._demo.launch(
            server_name=server_name,
            server_port=port or self.settings.lab_port,
            share=share,
            show_api=False,
        )
