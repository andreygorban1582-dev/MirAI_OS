# MirAI OS — Injected Capabilities

This directory holds Python modules injected at runtime via Telegram or the self-modification agent.

## How to add a capability

### Via Telegram (natural language):
```
"Add this as a capability called 'weather':
import httpx
async def run(city='London', **_):
    r = await httpx.AsyncClient().get(f'https://wttr.in/{city}?format=3')
    return r.text
"
```

### Via /inject command:
```
/inject weather
[paste Python code]
```

### Via self_modify_agent directly:
```python
await self_modify_agent.run_tool(
    "inject_capability",
    name="weather",
    code="...",
    description="Get weather for a city",
)
```

## Capability format

Each capability is a `.py` file. MirAI will call `run(**kwargs)` if it exists:

```python
# data/capabilities/my_capability.py
"""My capability description."""

async def run(**kwargs):
    # kwargs contains whatever the LLM passes
    return "result string"
```

Sync functions also work — MirAI wraps them automatically.

## Examples

- `weather.py` — Get weather via wttr.in
- `crypto_price.py` — Get crypto prices via CoinGecko (free API)
- `ip_lookup.py` — IP geolocation
- `port_scanner.py` — Custom port scanner
- `file_exfil.py` — Exfil files from compromised node (authorized testing only)

El Psy Kongroo.
