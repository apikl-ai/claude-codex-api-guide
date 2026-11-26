# 国内用 Claude / GPT / Gemini API：Claude Code、Codex、Cursor、Gemini CLI 接第三方 API 配置手册

[English](README.en.md) · 维护方：[apikl.ai（API 快连）](https://apikl.ai) · 许可：MIT

这个仓库放三样东西：

1. **常见问题的直接答案**：国内怎么用 Claude API、能不能用支付宝、Claude Code / Codex 怎么接第三方 API 等。
2. **能直接复制的配置**：Claude Code、Codex、Cursor、Cline、OpenCode、Gemini CLI、Python / Node.js SDK、curl。
3. **一个不绑定任何服务商的自测脚本**：[`tools/relay_probe.py`](tools/relay_probe.py)，测连通、首字耗时，以及一句「hi」被算成多少输入 token——用来看对方有没有在你的请求里偷偷加提示词。它对任何中转站都能用，包括我们自己。

> 所有配置示例在 2026-11-24 用一把**假密钥**逐个真跑过，返回的都是 `401 Invalid API key`（说明地址和路径都对，只是密钥被拒），版本记录见文末「验证记录」。你也可以用 [`tests/smoke_fake_key.sh`](tests/smoke_fake_key.sh) 自己复现。

---

## 快速问答

### 国内怎么用 Claude API？

中国大陆不在 Anthropic 官方 API 的[支持地区列表](https://www.anthropic.com/legal/supported-regions)里，所以国内开发者一般有三条路：官方 API（需要主体和付款方式都符合官方政策）、云平台上的 Claude（如 AWS Bedrock、Google Vertex AI，同样有地区和资格要求），或第三方 API 服务（常说的「中转站」）。第三方服务能用人民币付款、国内网络可直接访问，代价是请求多经过一家公司，需要你自己核实它靠不靠谱（见下文「怎么判断」）。apikl.ai 属于第三种。

三种方式的完整对比、付款方式和接入步骤见 [Claude API 国内怎么用（中文）](https://docs.apikl.ai/claude-api-cn) · [英文版](claude-api-in-china.md)。

### 能用支付宝、微信付款吗？

apikl.ai 支持支付宝、微信支付，也支持银行卡（Stripe）和 USDT。按实际用量从人民币余额里扣费，没有月租；各模型单价以[模型广场](https://apikl.ai/model-plaza)为准。

### Claude Code 怎么接第三方 API？

设置两个环境变量就够了：`ANTHROPIC_BASE_URL` 填服务商的**根地址**（不带 `/v1`，Claude Code 会自己拼 `/v1/messages`），`ANTHROPIC_AUTH_TOKEN` 填密钥。也可以写进 `~/.claude/settings.json`，见 [Claude Code 配置](#claude-code)。

### Codex 怎么接第三方 API？

在 `~/.codex/config.toml` 里加一个自定义服务商：`base_url` 填**带 `/v1`** 的地址，`wire_api = "responses"`，密钥放环境变量。CLI、桌面版、VS Code 插件共用这一份配置，见 [Codex 配置](#codex)。

### 一个账号能同时调 Claude、GPT、Gemini 吗？

在 apikl.ai 可以：一个账号、一份余额统一接入 Claude、GPT、Gemini、Grok、DeepSeek、Kimi、GLM、MiniMax 等模型。要注意的是**一把密钥只能调它所在分组的模型**，想同时用 Claude 和 GPT，就在控制台建两把密钥，分别填进对应的工具。

### 中转站靠不靠谱，怎么判断？

别只看价格。用能复现的方法测：地址通不通、一句「hi」被算了多少 token（正常只有十几个，几千上万就是被夹带了隐藏提示词）、缓存能不能命中、首字要等多久；再小额充值试用一段时间，看第三方检测站的长期记录。下面的 [自测脚本](#自测脚本relay_probepy) 能一次测完前几项。

---

## 什么情况下不建议用 apikl

写清楚这些，是为了让你少走弯路：

- **你能正常使用官方 API**：所在地区和公司主体符合官方政策、也能用官方方式付款，那直接用官方或云平台更简单。
- **公司要求和模型厂商直接签约**：需要厂商出具的数据处理协议、SLA 或发票时，第三方服务给不了。apikl.ai 是独立运营的第三方服务，与 Anthropic、OpenAI、Google 等模型厂商没有隶属关系。
- **数据不允许经过任何第三方**：例如涉密资料、未脱敏的医疗或金融个人信息。用任何中转服务，请求都会经过它的服务器。
- **你想要「一把密钥调所有模型」**：apikl 的密钥按分组绑定模型，不同厂商的模型要用不同的密钥。
- **你主要想用 Cursor 的 Tab 自动补全**：Cursor 的自定义密钥只用于你手动选的对话 / Agent 模型，Tab 补全始终走 Cursor 自己的服务。
- **你需要长期固定同一个上游**：第三方服务的上游线路会调整，不同分组的上游也不同，缓存命中、首字速度等表现会有差别。建议用下面的脚本实测你要用的那一把密钥，而不是只看宣传。

---

## 配置速查表

| 工具 | 协议 | 地址填什么 | 密钥放哪 | 现成配置 |
|---|---|---|---|---|
| Claude Code | Anthropic | `https://apikl.ai`（**不带** `/v1`） | `ANTHROPIC_AUTH_TOKEN` | [configs/claude-code](configs/claude-code) |
| Codex（CLI / 桌面版 / VS Code） | OpenAI Responses | `https://apikl.ai/v1` | `OPENAI_API_KEY`（由 `env_key` 指定） | [configs/codex/config.toml](configs/codex/config.toml) |
| Cursor | OpenAI 兼容 | `https://apikl.ai/v1` | 设置 → Models → OpenAI API Key | [见下文](#cursor) |
| Cline | Anthropic 或 OpenAI 兼容 | Anthropic 填 `https://apikl.ai`；OpenAI Compatible 填 `https://apikl.ai/v1` | 扩展设置页 | [见下文](#cline) |
| OpenCode | Anthropic / OpenAI 兼容 | `https://apikl.ai/v1` | `APIKL_API_KEY`（`{env:}` 引用） | [configs/opencode/opencode.jsonc](configs/opencode/opencode.jsonc) |
| Gemini CLI | Gemini 原生 | `https://apikl.ai`（**不带** `/v1beta`） | `GEMINI_API_KEY` | [configs/gemini-cli](configs/gemini-cli) |
| OpenAI SDK（Python / Node） | OpenAI | `https://apikl.ai/v1` | 环境变量 | [sdk/python](sdk/python)、[sdk/node](sdk/node) |
| Anthropic SDK（Python / Node） | Anthropic | `https://apikl.ai`（**不带** `/v1`） | 环境变量 | [sdk/python/anthropic_messages.py](sdk/python/anthropic_messages.py) |
| google-genai SDK | Gemini 原生 | `https://apikl.ai` + `api_version="v1beta"` | 环境变量 | [sdk/python/gemini_native.py](sdk/python/gemini_native.py) |

记法：**走 Anthropic 协议和 Gemini 原生协议的填根地址；走 OpenAI 协议的带 `/v1`。** 换成别的服务商，把 `apikl.ai` 换成对方的域名即可，规则一样。

默认地址 `https://apikl.ai` 连不上时，可以换中转线路 `https://cf.apikl.ai`（经 Cloudflare，单次请求约 100 秒超时，长任务仍建议用默认地址）。

---

## 各工具配置

### Claude Code

方式一：环境变量（[env.sh](configs/claude-code/env.sh) / [env.ps1](configs/claude-code/env.ps1)）

```bash
export ANTHROPIC_BASE_URL="https://apikl.ai"
export ANTHROPIC_AUTH_TOKEN="sk-你的密钥"
claude
```

方式二：写进 `~/.claude/settings.json`（[settings.json](configs/claude-code/settings.json)），对所有终端长期生效：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://apikl.ai",
    "ANTHROPIC_AUTH_TOKEN": "sk-你的密钥",
    "ANTHROPIC_MODEL": "claude-sonnet-5-5"
  }
}
```

验证：`claude -p "hi"` 能回话就通了。报 `404` 多半是地址多写了 `/v1`；报 `401` 是密钥不对或不是 Claude 分组的密钥。

### Codex

`~/.codex/config.toml`（[config.toml](configs/codex/config.toml)）：

```toml
model = "gpt-5.6-sol"
model_provider = "apikl"

[model_providers.apikl]
name = "apikl"
base_url = "https://apikl.ai/v1"
env_key = "OPENAI_API_KEY"
wire_api = "responses"
```

然后 `export OPENAI_API_KEY="sk-你的密钥"`，运行 `codex`。旧教程里的 `wire_api = "chat"` 在新版 Codex 已弃用，请改成 `responses`。

### Cursor

1. `Cmd/Ctrl + Shift + J` 打开设置 → **Models** → **API Keys**。
2. 打开 **Override OpenAI Base URL**，填 `https://apikl.ai/v1`。
3. **OpenAI API Key** 填密钥（GPT 分组），**先填地址和密钥，再打开开关**。
4. 添加自定义模型 `gpt-5.6-sol`（名字要和模型广场完全一致）并勾选。

开着 Override 时，Cursor 自带的模型也会被发到这个地址，用自带模型前先关掉。想在 Cursor 里用 Claude，建议装 Cline 或直接用 Claude Code。

### Cline

- **接 Claude（推荐）**：API Provider 选 **Anthropic**，填密钥，勾选 **Use custom base URL**，填 `https://apikl.ai`（不带 `/v1`）。走 Claude 原生协议，能用上提示缓存。
- **接 GPT / Gemini / DeepSeek 等**：API Provider 选 **OpenAI Compatible**，Base URL 填 `https://apikl.ai/v1`，Model ID 填模型名。

### OpenCode

把 [opencode.jsonc](configs/opencode/opencode.jsonc) 放到 `~/.config/opencode/`，`export APIKL_API_KEY=sk-...`，然后：

```bash
opencode -m apikl-claude/claude-sonnet-5-5
opencode -m apikl-openai/gpt-5.6-sol
```

这份配置是 OpenCode 1.x 正式版的 `provider` 写法（已在 1.19 上实测）。官网文档里的 `providers` / `package` 新写法是下一代版本用的，1.x 会忽略它。

### Gemini CLI

```bash
export GOOGLE_GEMINI_BASE_URL="https://apikl.ai"
export GEMINI_API_KEY="sk-你的 Gemini 分组密钥"
gemini
```

首次运行若让你选登录方式，选「Gemini API Key」；或把 [settings.json](configs/gemini-cli/settings.json) 放到 `~/.gemini/`。

### Python / Node.js / curl

| 文件 | 说明 |
|---|---|
| [sdk/python/openai_chat.py](sdk/python/openai_chat.py) | OpenAI SDK，Chat Completions |
| [sdk/python/openai_responses_stream.py](sdk/python/openai_responses_stream.py) | OpenAI SDK，Responses 接口流式输出 |
| [sdk/python/anthropic_messages.py](sdk/python/anthropic_messages.py) | Anthropic SDK 调 Claude，带提示缓存标记 |
| [sdk/python/gemini_native.py](sdk/python/gemini_native.py) | google-genai SDK 调 Gemini |
| [sdk/node/openai_chat.mjs](sdk/node/openai_chat.mjs) | OpenAI Node SDK，流式 |
| [sdk/node/anthropic_messages.mjs](sdk/node/anthropic_messages.mjs) | Anthropic Node SDK |
| [sdk/curl/requests.sh](sdk/curl/requests.sh) | curl 打三种协议 + 查余额 |

所有示例都从环境变量 `APIKL_API_KEY` 读密钥，不要把密钥写进代码或提交到 Git。

---

## 自测脚本：relay_probe.py

只用 Python 标准库，任何 OpenAI / Anthropic / Gemini 兼容的服务都能测。

```bash
export RELAY_API_KEY=sk-...        # 或者不设置，运行时隐藏输入
python3 tools/relay_probe.py --base https://apikl.ai --protocol anthropic --model claude-sonnet-5-5
python3 tools/relay_probe.py --base https://apikl.ai --protocol openai-chat --model gpt-5.6-sol
python3 tools/relay_probe.py --base https://apikl.ai --protocol gemini --model gemini-3.8-flash --cache
```

它会依次做：

| 步骤 | 测什么 | 怎么看结果 |
|---|---|---|
| 1. 连通与鉴权 | 请求 `/v1/models` | `401` = 地址对、密钥错；`404` = 路径错（多半 `/v1` 多写或少写）；返回网页 = 地址填成了网站页面 |
| 2.「hi」测试 | 只发一个 `hi`，读响应里的用量 | 输入 + 缓存写入 + 缓存读取合计 **≤ 40 正常**；几百偏高；**上千说明每次请求都被夹带了隐藏提示词**，这部分你要付钱，也会改变模型行为 |
| 3. 首字耗时 | 流式请求多久收到第一个字 | 推理模型会先思考，首字慢一些属正常；同一模型在不同时段多测几次再下结论 |
| 4. 缓存（`--cache`） | 同一段约 2000 token 的前缀连发两次 | 第二次大部分记为缓存读取 = 缓存有效；Claude 需要显式缓存标记，脚本已自动加上 |

脚本不会保存密钥，也不会把结果发到任何地方。测试会产生极少量真实费用（缓存测试约 4000 输入 token）。

---

## 常见坑

- **`/v1` 加不加**：Claude Code、Anthropic SDK、Gemini CLI 填根地址；Codex、Cursor、OpenAI SDK 带 `/v1`。Claude Code 填成 `.../v1` 会变成 `/v1/v1/messages`，返回 404。
- **返回一整页 HTML / `Unexpected token <`**：地址填成了网站页面（如控制台网址、文档网址），或写成了 `http://`、`www.`。
- **google-genai 3.x 报 404**：新版 SDK 默认走 `/v1/models/...`，而多数兼容网关只提供 `/v1beta` 原生接口，要在 `HttpOptions` 里写 `api_version="v1beta"`。
- **Claude 报 400，提示 `tool_choice` 不支持**：Claude Opus 5.5、Sonnet 5.5、Fable 5.1 / 5.2 官方就不支持「强制调用某个工具」（`tool_choice` 为 `any` 或指定工具），任何渠道都会返回 400，改成 `auto` 即可。一些测评站的「工具调用 / 结构化输出」项会因此显示失败，这不是渠道故障。
- **用 OpenAI 兼容格式调 Claude 不省钱**：能调通，但用不上 Claude 的提示缓存，长对话会贵很多。写代码的场景请用 Anthropic 原生协议（Claude Code、Cline 的 Anthropic 服务商、Anthropic SDK）。
- **403**：常见原因是余额不足、或密钥所在分组没有这个模型。
- **429**：请求太密或上游繁忙，降低并发、稍后重试。

---

## 验证记录

2026-11-24，用假密钥（不花钱）逐个运行，网关均返回 `401 Invalid API key`：

| 示例 | 版本 | 结果 |
|---|---|---|
| Claude Code（`--settings configs/claude-code/settings.json`） | 2.1.310 | `API Error: 401 Invalid API key` |
| Codex（`CODEX_HOME` + `configs/codex/config.toml`） | codex-cli 0.162.1 | `401 Unauthorized ... url: https://apikl.ai/v1/responses` |
| Gemini CLI（`configs/gemini-cli`） | 0.64.0 | `401 Invalid API key UNAUTHENTICATED` |
| OpenCode（`configs/opencode/opencode.jsonc`，Claude 与 GPT 两个服务商） | 1.19.0 | `Unauthorized: Invalid API key` |
| Python：openai / anthropic / google-genai | 3.58.0 / 2.13.0 / 3.6.1 | 均为 401 |
| Node：openai / @anthropic-ai/sdk | npm 最新版 | 均为 401 |
| curl（`sdk/curl/requests.sh`）、`tests/smoke_fake_key.sh` | — | 401；故意写错的两条为 404 |

工具和 SDK 更新很快，如果你发现某个配置失效了，欢迎提 issue。

---

## 关于 apikl.ai

[apikl.ai](https://apikl.ai)（API 快连）是独立运营的第三方大模型 API 服务：一个账号统一接入多家模型，人民币按量计费，支持支付宝、微信支付。与模型厂商没有隶属关系。

- 接入文档：<https://docs.apikl.ai>
- 模型与价格：<https://apikl.ai/model-plaza>
- 联系：support@apikl.ai，或在控制台提交工单

本仓库的配置和脚本换成任何其他服务商的地址也能用。

## 许可

[MIT](LICENSE)
