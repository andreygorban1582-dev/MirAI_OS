"""
MirAI_OS  –  Hello World example mod
Shows the Mod 2 lifecycle API.
"""

MOD_NAME    = "hello_world"
MOD_VERSION = "1.0.0"


def setup(bot, llm, ctx):
    print(f"[{MOD_NAME}] setup called")


def on_startup(ctx):
    print(f"[{MOD_NAME}] startup – mode: {ctx.get('mode', 'unknown')}")


def on_shutdown(ctx):
    print(f"[{MOD_NAME}] shutdown")


def on_message(message: str, ctx: dict):
    if message.strip().lower() == "ping":
        return "pong (from hello_world mod)"
    return None  # pass through to LLM
