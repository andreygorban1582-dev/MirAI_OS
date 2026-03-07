"""
MirAI OS — Web Agent
Full web browsing, scraping, form filling, and automation via Playwright.
"""
from __future__ import annotations

import logging
from typing import Optional

from agents.base_agent import AgentTask, AgentResult, BaseAgent, Tool, ToolResult

logger = logging.getLogger("mirai.agent.web")


class WebAgent(BaseAgent):
    name = "web_agent"
    description = "Browse the web, scrape pages, fill forms, search the internet, and automate web tasks"

    def __init__(self) -> None:
        self._browser = None
        self._page = None
        super().__init__()

    def _register_tools(self) -> None:
        self.register_tool(Tool("navigate", "Navigate to a URL", self._navigate))
        self.register_tool(Tool("get_text", "Get visible text content of current page", self._get_text))
        self.register_tool(Tool("get_html", "Get full HTML of current page", self._get_html))
        self.register_tool(Tool("click", "Click an element by selector", self._click))
        self.register_tool(Tool("fill_form", "Fill a form field", self._fill_form))
        self.register_tool(Tool("screenshot", "Take a screenshot of current page", self._screenshot))
        self.register_tool(Tool("search", "Search the web with DuckDuckGo", self._search))
        self.register_tool(Tool("fetch_json", "Fetch JSON from a URL (API calls)", self._fetch_json))
        self.register_tool(Tool("evaluate_js", "Execute JavaScript on current page", self._eval_js))
        self.register_tool(Tool("close", "Close the browser", self._close))

    async def _ensure_browser(self) -> None:
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright
                pw = await async_playwright().start()
                self._browser = await pw.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                self._page = await self._browser.new_page()
                # Set realistic user agent
                await self._page.set_extra_http_headers({
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
                })
            except Exception as e:
                logger.error(f"Browser init failed: {e}")
                raise

    async def execute(self, task: AgentTask) -> AgentResult:
        action = task.params.get("action", "search")
        target = task.params.get("target", task.description)
        result = await self.run_tool(action, target=target, **task.params)
        return AgentResult(
            task_id=task.task_id,
            agent_name=self.name,
            success=result.success,
            output=result.output,
            error=result.error,
            duration_ms=result.duration_ms,
        )

    async def _navigate(self, target: str = "", **_) -> ToolResult:
        try:
            await self._ensure_browser()
            await self._page.goto(target, timeout=30000, wait_until="domcontentloaded")
            title = await self._page.title()
            return ToolResult(success=True, output=f"Navigated to: {target}\nTitle: {title}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _get_text(self, **_) -> ToolResult:
        try:
            await self._ensure_browser()
            text = await self._page.evaluate("() => document.body.innerText")
            return ToolResult(success=True, output=text[:20000])
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _get_html(self, **_) -> ToolResult:
        try:
            await self._ensure_browser()
            html = await self._page.content()
            return ToolResult(success=True, output=html[:50000])
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _click(self, target: str = "", **_) -> ToolResult:
        try:
            await self._ensure_browser()
            await self._page.click(target, timeout=10000)
            return ToolResult(success=True, output=f"Clicked: {target}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _fill_form(self, target: str = "", value: str = "", **_) -> ToolResult:
        try:
            await self._ensure_browser()
            await self._page.fill(target, value)
            return ToolResult(success=True, output=f"Filled {target} with value")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _screenshot(self, target: str = "/tmp/mirai_screenshot.png", **_) -> ToolResult:
        try:
            await self._ensure_browser()
            await self._page.screenshot(path=target, full_page=True)
            return ToolResult(success=True, output=f"Screenshot saved: {target}", data=target)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _search(self, target: str = "", **_) -> ToolResult:
        try:
            import urllib.parse
            query = urllib.parse.quote_plus(target)
            url = f"https://html.duckduckgo.com/html/?q={query}"
            await self._ensure_browser()
            await self._page.goto(url, timeout=30000)
            # Extract search results
            results = await self._page.evaluate("""() => {
                const items = document.querySelectorAll('.result');
                return Array.from(items).slice(0, 10).map(el => {
                    const title = el.querySelector('.result__title')?.innerText || '';
                    const snippet = el.querySelector('.result__snippet')?.innerText || '';
                    const link = el.querySelector('a.result__url')?.href || '';
                    return {title, snippet, link};
                });
            }""")
            output = "\n\n".join(
                f"**{r['title']}**\n{r['snippet']}\n{r['link']}"
                for r in results if r.get("title")
            )
            return ToolResult(success=True, output=output or "No results found", data=results)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _fetch_json(self, target: str = "", **_) -> ToolResult:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(target)
                resp.raise_for_status()
                return ToolResult(success=True, output=resp.text[:50000], data=resp.json())
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _eval_js(self, target: str = "", code: str = "", **_) -> ToolResult:
        try:
            await self._ensure_browser()
            script = code or target
            result = await self._page.evaluate(script)
            return ToolResult(success=True, output=str(result))
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    async def _close(self, **_) -> ToolResult:
        if self._browser:
            await self._browser.close()
            self._browser = None
            self._page = None
        return ToolResult(success=True, output="Browser closed")
