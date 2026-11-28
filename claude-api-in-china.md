# Claude API in China (2026): official API vs. cloud vs. relay, and paying with Alipay or WeChat Pay

[← Back to README](README.en.md) · [Web version](https://apikl.ai/claude-api-in-china) · [中文版](https://docs.apikl.ai/claude-api-cn) · Maintained by [apikl.ai](https://apikl.ai) · Facts checked 2026-11-28

**Short answer:** Anthropic does not offer the Claude API in mainland China or Hong Kong, and the official API only takes credit cards billed in USD. If you are a developer in China and want to pay with **Alipay or WeChat Pay**, the practical route is a third-party API service (often called an *API relay*). With apikl.ai, for example: top up an RMB balance with Alipay / WeChat Pay → create a key in a Claude group → set the base URL to `https://apikl.ai` (Claude Code and the Anthropic SDK, **no** `/v1`) or `https://apikl.ai/v1` (OpenAI-compatible clients such as Cursor or Cline).

---

## Why the official Claude API doesn't work from China

- **Region:** mainland China and Hong Kong are not on Anthropic's [supported countries list](https://www.anthropic.com/supported-countries).
- **Ownership:** since 2025, Anthropic [also bars](https://www.anthropic.com/news/updating-restrictions-of-sales-to-unsupported-regions) companies headquartered in unsupported regions such as China, and entities more than 50% owned by them, wherever they are incorporated or operate.
- **Payment:** the official API is prepaid; standard accounts pay by major credit card and all payments are in USD ([pricing FAQ](https://platform.claude.com/docs/en/about-claude/pricing)). Alipay and WeChat Pay are not accepted.

## Three ways to get Claude API access, compared

| Option | Usable from China? | How you pay | Good fit for |
|---|---|---|---|
| **Anthropic API** | No — mainland China / Hong Kong unsupported | Credit card, USD, prepaid | Individuals and companies in supported regions that are not subject to the ownership rule |
| **Cloud platforms** (AWS Bedrock, Google Cloud Vertex AI, Microsoft Foundry) | Needs an account on that cloud; check that your account region and use case meet both the cloud's and Anthropic's terms first | Whatever the cloud account is billed with, usually postpaid | Teams that already run on that cloud with an overseas entity |
| **Third-party API service / relay** (e.g. apikl.ai) | Reachable from most domestic networks | Alipay, WeChat Pay, card (Stripe), USDT; RMB balance, pay as you go | Individual developers and small teams in China using Claude Code, Cursor, Cline or their own code |

> **Be clear about what a relay is.** A third-party service is not affiliated with Anthropic, and your requests pass through its servers before reaching the upstream model. Start with a small top-up, don't send secrets, personal data or confidential code you can't share, and build in retries and a fallback for production. If your company must contract directly with the model vendor (DPA, SLA, vendor invoices) or data may not pass through any third party, a relay is the wrong choice.

## Using apikl.ai: from Alipay / WeChat Pay to a working call

1. **Sign up and top up** at [apikl.ai](https://apikl.ai) with Alipay, WeChat Pay, a card (Stripe) or USDT. The balance is in RMB, charged by actual usage, no monthly fee; a small first top-up is fine.
2. **Create a key** in the [console](https://apikl.ai/keys) and pick a Claude group (e.g. Claude-Max). A key only reaches the models in its own group — Claude-group keys call Claude, GPT-group keys call GPT. One account can hold many keys sharing one balance. Groups, models and live prices: [model plaza](https://apikl.ai/model-plaza).
3. **Set the base URL:**

   | Where | Base URL | Note |
   |---|---|---|
   | Claude Code, Anthropic SDK | `https://apikl.ai` | **No** `/v1`; the client appends `/v1/messages` |
   | Cursor, Cline, Cherry Studio, OpenAI SDK and other OpenAI-compatible clients | `https://apikl.ai/v1` | Use the Claude model name as-is |
   | If the default line is unreachable | `https://cf.apikl.ai` | Goes through Cloudflare; same paths, only the host changes |

4. **Test it** (replace `sk-your-key`):

```bash
curl https://apikl.ai/v1/messages \
  -H "x-api-key: sk-your-key" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-5-5","max_tokens":1024,"messages":[{"role":"user","content":"Introduce yourself in one sentence."}]}'
```

A JSON reply with text means it works; `401` means the key is wrong or not in a Claude group.

Python, with the official SDK (`pip install anthropic`):

```python
import anthropic

client = anthropic.Anthropic(
    base_url="https://apikl.ai",  # no /v1
    api_key="sk-your-key",
)
msg = client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Introduce yourself in one sentence."}],
)
print(msg.content[0].text)
```

Claude Code (macOS / Linux; on Windows PowerShell use `$env:NAME="value"`):

```bash
export ANTHROPIC_BASE_URL=https://apikl.ai
export ANTHROPIC_AUTH_TOKEN=sk-your-key
claude
```

No Claude Pro / Max subscription and no Anthropic account are needed. Persistent settings: [configs/claude-code](configs/claude-code).

## Which Claude models

| Model | Note |
|---|---|
| `claude-opus-5-5` | Claude Opus 5.5 — strongest, for complex coding and long tasks |
| `claude-sonnet-5-5` | Claude Sonnet 5.5 — balanced speed and price; a good default |
| `claude-fable-5-2` | Claude Fable 5.2 |
| `claude-haiku-5-5` | Claude Haiku 5.5 — fast and low-cost |

Availability and prices differ by group; the [model plaza](https://apikl.ai/model-plaza) is the source of truth.

## Payment, invoices and refunds at apikl.ai

| Item | Details |
|---|---|
| Payment methods | Alipay, WeChat Pay, card (Stripe), USDT |
| Billing | RMB balance, charged per request by input / output / cache tokens; no monthly fee |
| Usage records | Every request's model, tokens and cost are listed in the console |
| Invoices | Company invoices or bank transfer: contact support |
| Refunds | Duplicate charges, payments that didn't reach the balance, and billing errors confirmed by the platform are refunded to the original method or credited back; normal usage isn't refunded. The [terms of service](https://apikl.ai/legal/terms) govern. |

Contact and company details: [About apikl.ai](https://docs.apikl.ai/about) (Chinese).

## How to vet any Claude relay (including us)

- **Top up a little first.**
- **Check billing transparency:** can you see tokens and cost for every request?
- **Look for injected prompts:** send a bare `hi` and see how many input tokens it's billed as — normally a dozen or so; thousands means a hidden prompt is being added. [`tools/relay_probe.py`](tools/relay_probe.py) measures this plus reachability and time to first token against any relay.
- **Check long-running third-party monitors** for uptime and protocol tests.

## FAQ

**Can I use the official Claude API directly from mainland China?**
No. Mainland China and Hong Kong are not supported regions, companies headquartered in China or more than 50% owned by such companies are barred, and the official API only accepts USD credit cards. Developers in China usually go through a third-party API service.

**Is there a Claude API that accepts Alipay or WeChat Pay?**
Not from Anthropic. Many third-party services accept RMB; apikl.ai accepts Alipay, WeChat Pay, cards and USDT, with pay-as-you-go billing and no monthly fee.

**Do I need a VPN or proxy to reach a relay?**
Usually not. apikl.ai is reachable from most domestic networks; if the default line fails, `cf.apikl.ai` (via Cloudflare) works the same way.

**Can one key call both Claude and GPT?**
No. Each key only reaches its own group's models. Create one key per group in the same account; they share the balance.

**Do I need a Claude Pro / Max subscription?**
No. You pay per use with an apikl.ai key; no Anthropic account, subscription or overseas card.

---

*Verification: on 2026-11-26 the curl command and Python snippet above were run unchanged with a fake key (`sk-thisisafakekeyfortesting`, anthropic SDK 2.14.0) and returned `401 Invalid API key` — the address and paths are correct, only the key is rejected. Policy links were checked the same day.*
