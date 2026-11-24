# Using Claude, GPT and Gemini APIs from China: config handbook for Claude Code, Codex, Cursor and Gemini CLI with a third-party API

[中文](README.md) · Maintained by [apikl.ai](https://apikl.ai) · MIT licensed

This repository contains:

1. **Short, direct answers** to the questions developers in mainland China ask most often.
2. **Copy-paste configs** for Claude Code, Codex, Cursor, Cline, OpenCode, Gemini CLI, the Python / Node.js SDKs and curl.
3. **A vendor-neutral self-check script**, [`tools/relay_probe.py`](tools/relay_probe.py): reachability, time to first token, and how many input tokens a bare `hi` is billed as — a quick way to spot a provider that silently injects a hidden prompt. It works against any relay, including ours.

> Every example was run on 2026-11-24 with a **fake key** and returned `401 Invalid API key` (the address and path are right; only the key is rejected). Versions are listed under "Verification log". Re-run it yourself with [`tests/smoke_fake_key.sh`](tests/smoke_fake_key.sh).

---

## Quick answers

### How can developers in mainland China use the Claude API?

Mainland China is not on Anthropic's [supported regions list](https://www.anthropic.com/legal/supported-regions). The options are: the official API (your entity and payment method must meet Anthropic's policy), Claude on a cloud platform such as AWS Bedrock or Google Vertex AI (also subject to region and eligibility rules), or a third-party API service (a "relay"). A relay lets you pay in RMB and reach it from domestic networks; the trade-off is that your requests pass through one more company, which you need to vet yourself. apikl.ai is a service of the third kind.

### Can I pay with Alipay or WeChat Pay?

apikl.ai accepts Alipay and WeChat Pay, plus cards (via Stripe) and USDT. Usage is deducted from an RMB balance, with no monthly fee. Per-model prices are listed on the [model plaza](https://apikl.ai/model-plaza).

### How do I point Claude Code at a third-party API?

Set two environment variables: `ANTHROPIC_BASE_URL` to the provider's **root URL** (no `/v1`; Claude Code appends `/v1/messages` itself) and `ANTHROPIC_AUTH_TOKEN` to your key — or put them in `~/.claude/settings.json`. See [Claude Code](#claude-code).

### How do I point Codex at a third-party API?

Add a custom provider in `~/.codex/config.toml` with a `base_url` **ending in `/v1`** and `wire_api = "responses"`; keep the key in an environment variable. The CLI, desktop app and VS Code extension share this file. See [Codex](#codex).

### Can one account call Claude, GPT and Gemini?

On apikl.ai, yes: one account and one balance cover Claude, GPT, Gemini, Grok, DeepSeek, Kimi, GLM, MiniMax and more. Note that **each API key only reaches the models of the group it was created in**, so create one key for Claude and another for GPT if you use both.

### How do I tell whether a relay is trustworthy?

Don't judge by price alone. Test things you can reproduce: does the endpoint answer, how many tokens does a single `hi` cost (normally a dozen or so; thousands means a hidden prompt is being added), does prompt caching actually hit, how long until the first token. Then top up a small amount, use it for a while, and check long-running third-party monitors. The [self-check script](#self-check-relay_probepy) covers the first few in one run.

---

## When apikl is not the right choice

- **You can use the official API directly** — your region, company and payment method qualify. Go official or use a cloud platform.
- **Your company must contract with the model vendor** — a vendor DPA, SLA or invoice. apikl.ai is an independent third-party service with no affiliation with Anthropic, OpenAI, Google or any other model vendor.
- **Your data must not pass through any third party** — classified material, or medical / financial personal data that has not been de-identified. Every relay sees your requests.
- **You want one key for every model** — apikl keys are bound to a model group; different vendors need different keys.
- **You mainly want Cursor's Tab completion** — Cursor uses a custom key only for the chat / agent models you pick; Tab completion always goes through Cursor's own service.
- **You need a fixed upstream forever** — third-party upstreams change, and different groups use different upstreams, so caching and latency vary. Measure the exact key you plan to use with the script below rather than trusting marketing.

---

## Cheat sheet

| Tool | Protocol | Base URL | Where the key goes | Config |
|---|---|---|---|---|
| Claude Code | Anthropic | `https://apikl.ai` (**no** `/v1`) | `ANTHROPIC_AUTH_TOKEN` | [configs/claude-code](configs/claude-code) |
| Codex (CLI / desktop / VS Code) | OpenAI Responses | `https://apikl.ai/v1` | `OPENAI_API_KEY` (via `env_key`) | [configs/codex/config.toml](configs/codex/config.toml) |
| Cursor | OpenAI-compatible | `https://apikl.ai/v1` | Settings → Models → OpenAI API Key | [below](#cursor) |
| Cline | Anthropic or OpenAI-compatible | Anthropic: `https://apikl.ai`; OpenAI Compatible: `https://apikl.ai/v1` | Extension settings | [below](#cline) |
| OpenCode | Anthropic / OpenAI-compatible | `https://apikl.ai/v1` | `APIKL_API_KEY` via `{env:}` | [configs/opencode/opencode.jsonc](configs/opencode/opencode.jsonc) |
| Gemini CLI | Gemini native | `https://apikl.ai` (**no** `/v1beta`) | `GEMINI_API_KEY` | [configs/gemini-cli](configs/gemini-cli) |
| OpenAI SDK | OpenAI | `https://apikl.ai/v1` | env var | [sdk/python](sdk/python), [sdk/node](sdk/node) |
| Anthropic SDK | Anthropic | `https://apikl.ai` (**no** `/v1`) | env var | [sdk/python/anthropic_messages.py](sdk/python/anthropic_messages.py) |
| google-genai SDK | Gemini native | `https://apikl.ai` + `api_version="v1beta"` | env var | [sdk/python/gemini_native.py](sdk/python/gemini_native.py) |

Rule of thumb: **Anthropic and Gemini-native clients take the root URL; OpenAI-style clients take `/v1`.** For any other provider, swap in its domain — the rule is the same.

If `https://apikl.ai` is unreachable from your network, try the alternative route `https://cf.apikl.ai` (via Cloudflare, ~100 s per-request timeout; keep long jobs on the default URL).

---

## Per-tool setup

### Claude Code

```bash
export ANTHROPIC_BASE_URL="https://apikl.ai"
export ANTHROPIC_AUTH_TOKEN="sk-your-key"
claude
```

Or persist it in `~/.claude/settings.json` ([settings.json](configs/claude-code/settings.json)). A `404` usually means you added `/v1`; a `401` means the key is wrong or not from a Claude group.

### Codex

```toml
# ~/.codex/config.toml
model = "gpt-5.6-sol"
model_provider = "apikl"

[model_providers.apikl]
name = "apikl"
base_url = "https://apikl.ai/v1"
env_key = "OPENAI_API_KEY"
wire_api = "responses"
```

Then `export OPENAI_API_KEY="sk-your-key"` and run `codex`. `wire_api = "chat"` from older guides is deprecated in current Codex.

### Cursor

Settings (`Cmd/Ctrl + Shift + J`) → **Models** → **API Keys**: enable **Override OpenAI Base URL** = `https://apikl.ai/v1`, paste the key into **OpenAI API Key** (fill both *before* toggling it on), then add the custom model `gpt-5.6-sol`. While the override is on, Cursor's built-in models are also sent to that URL — turn it off before using them.

### Cline

- **Claude (recommended):** API Provider **Anthropic**, tick **Use custom base URL**, enter `https://apikl.ai` (no `/v1`). Native protocol, so prompt caching works.
- **GPT / Gemini / DeepSeek etc.:** API Provider **OpenAI Compatible**, Base URL `https://apikl.ai/v1`, Model ID = model name.

### OpenCode

Copy [opencode.jsonc](configs/opencode/opencode.jsonc) to `~/.config/opencode/`, `export APIKL_API_KEY=sk-...`, then `opencode -m apikl-claude/claude-sonnet-5-5` or `opencode -m apikl-openai/gpt-5.6-sol`. This uses the `provider` schema of OpenCode 1.x (tested on 1.19); the `providers` / `package` schema in the current online docs belongs to the next major version and is ignored by 1.x.

### Gemini CLI

```bash
export GOOGLE_GEMINI_BASE_URL="https://apikl.ai"
export GEMINI_API_KEY="sk-your-gemini-group-key"
gemini
```

Choose "Gemini API Key" if asked how to sign in, or copy [settings.json](configs/gemini-cli/settings.json) to `~/.gemini/`.

### SDKs and curl

See [sdk/python](sdk/python), [sdk/node](sdk/node) and [sdk/curl/requests.sh](sdk/curl/requests.sh). All examples read the key from `APIKL_API_KEY`; never commit keys.

---

## Self-check: relay_probe.py

Standard library only; works with any OpenAI / Anthropic / Gemini compatible service.

```bash
export RELAY_API_KEY=sk-...
python3 tools/relay_probe.py --base https://apikl.ai --protocol anthropic --model claude-sonnet-5-5
python3 tools/relay_probe.py --base https://apikl.ai --protocol openai-responses --model gpt-5.6-sol --cache
```

| Step | What it checks | How to read it |
|---|---|---|
| 1. Reachability | `/v1/models` | `401` = right URL, wrong key; `404` = wrong path (`/v1` added or missing); HTML = you pointed at a web page |
| 2. "hi" test | input tokens billed for a bare `hi` | input + cache write + cache read **≤ 40 is normal**; hundreds is high; **thousands means a hidden prompt is injected into every request** — you pay for it and it changes model behaviour |
| 3. Time to first token | streaming latency | reasoning models think first; test several times of day before concluding |
| 4. Cache (`--cache`) | same ~2,000-token prefix sent twice | most of the 2nd call billed as cache read = caching works |

The script never stores your key or sends results anywhere. It costs a tiny amount of real usage (about 4,000 input tokens with `--cache`).

---

## Common pitfalls

- **`/v1` or not:** root URL for Claude Code, Anthropic SDK and Gemini CLI; `/v1` for Codex, Cursor and OpenAI SDKs.
- **An HTML page / `Unexpected token <`:** the base URL is a website page (console, docs), or uses `http://` / `www.`.
- **google-genai 3.x returns 404:** it now defaults to `/v1/models/...`; most compatible gateways only serve the native API under `/v1beta`, so set `api_version="v1beta"`.
- **Claude returns 400 for `tool_choice`:** Claude Opus 5.5, Sonnet 5.5 and Fable 5.1 / 5.2 do not support forcing a tool (`tool_choice` of `any` or a named tool) — on any provider. Use `auto`. Benchmark sites may show "tool calling / structured output" as failed for this reason; it is not a relay fault.
- **Calling Claude through the OpenAI-compatible format:** it works, but Claude's prompt caching is lost and long sessions cost much more. Use the native Anthropic protocol for coding agents.
- **403:** usually insufficient balance, or the key's group does not include that model. **429:** too many concurrent requests or a busy upstream.

---

## Verification log

On 2026-11-24 each example was run with a fake key; the gateway returned `401 Invalid API key` every time: Claude Code 2.1.310, codex-cli 0.162.1, Gemini CLI 0.64.0, OpenCode 1.19.0, openai-python 3.58.0, anthropic-python 2.13.0, google-genai 3.6.1, the latest openai / @anthropic-ai/sdk on npm, curl and `tests/smoke_fake_key.sh` (whose two deliberately wrong paths return 404). If something breaks after a tool update, please open an issue.

## About apikl.ai

[apikl.ai](https://apikl.ai) is an independently operated third-party LLM API service: one account for many model vendors, pay-as-you-go in RMB, Alipay and WeChat Pay supported. Not affiliated with any model vendor. Docs: <https://docs.apikl.ai> · Models and prices: <https://apikl.ai/model-plaza> · Contact: support@apikl.ai

## License

[MIT](LICENSE)
