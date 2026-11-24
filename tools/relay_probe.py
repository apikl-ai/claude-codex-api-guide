#!/usr/bin/env python3
"""
relay_probe.py — 任何 OpenAI / Anthropic / Gemini 兼容 API（含各家中转站）的自测脚本
A vendor-neutral self-check for any OpenAI / Anthropic / Gemini compatible endpoint.

它只做三件事 / It does three things:
  1. 连通：地址和路径对不对、密钥是否被接受           (reachability & auth)
  2. 「hi」测试：只发一个 hi，看对方记了多少输入 token  (is anything injected into your prompt?)
  3. 首字耗时：流式请求多久收到第一个字               (time to first byte / first token)
可选 / optional:
  --cache  连发两次同一段约 2000 token 的长前缀，看第二次有没有记为缓存读取

只用 Python 标准库，无需安装任何依赖。Python 3.8+。
Standard library only. No third-party packages.

用法 / Usage:
  export RELAY_API_KEY=sk-...                 # 密钥只从环境变量或隐藏输入读取，不会写入任何文件
  python3 relay_probe.py --base https://apikl.ai --protocol anthropic --model claude-sonnet-5-5
  python3 relay_probe.py --base https://apikl.ai --protocol openai-chat --model gpt-5.6-sol
  python3 relay_probe.py --base https://apikl.ai --protocol openai-responses --model gpt-5.6-sol
  python3 relay_probe.py --base https://apikl.ai --protocol gemini --model gemini-3.8-flash

--base 填站点根地址（不带 /v1）；带了 /v1 脚本会自动去掉并提示。
--base is the site root (without /v1); a trailing /v1 is stripped automatically.

License: MIT
"""
import argparse
import getpass
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request

UA = "relay-probe/1.0 (+https://github.com/apikl-ai/claude-codex-api-guide)"
TIMEOUT = 180

# 「hi」测试的判定阈值（输入 + 缓存写入 + 缓存读取 的总和）
# Thresholds for the "hi" test (input + cache write + cache read).
NORMAL_MAX = 40      # 正常：不同模型分词不同，一般在 5~30 之间
SUSPECT_MAX = 300    # 偏高：可能被加了一段简短的系统提示


def say(msg=""):
    print(msg, flush=True)


def norm_base(base):
    b = base.strip().rstrip("/")
    for suffix in ("/v1beta", "/v1"):
        if b.endswith(suffix):
            say(f"  提示：--base 不需要带 {suffix}，已自动去掉 / note: stripped trailing {suffix}")
            b = b[: -len(suffix)]
    if b.startswith("http://"):
        say("  提示：用的是 http://，多数服务只接受 https:// / note: most services require https://")
    return b


def headers_for(protocol, key):
    h = {"Content-Type": "application/json", "User-Agent": UA}
    if protocol == "anthropic":
        h["x-api-key"] = key
        h["anthropic-version"] = "2023-06-01"
    elif protocol == "gemini":
        h["x-goog-api-key"] = key
    else:
        h["Authorization"] = f"Bearer {key}"
    return h


def endpoint(protocol, base, model, stream):
    if protocol == "openai-chat":
        return f"{base}/v1/chat/completions"
    if protocol == "openai-responses":
        return f"{base}/v1/responses"
    if protocol == "anthropic":
        return f"{base}/v1/messages"
    if protocol == "gemini":
        action = "streamGenerateContent?alt=sse" if stream else "generateContent"
        return f"{base}/v1beta/models/{model}:{action}"
    raise ValueError(protocol)


def body_for(protocol, model, text, stream, max_out=64, cache=False):
    if protocol == "openai-chat":
        b = {"model": model, "messages": [{"role": "user", "content": text}], "max_tokens": max_out}
        if stream:
            b["stream"] = True
            b["stream_options"] = {"include_usage": True}
        return b
    if protocol == "openai-responses":
        b = {"model": model, "input": text, "max_output_tokens": max_out}
        if stream:
            b["stream"] = True
        return b
    if protocol == "anthropic":
        content = text
        if cache:
            content = [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]
        b = {"model": model, "max_tokens": max_out, "messages": [{"role": "user", "content": content}]}
        if stream:
            b["stream"] = True
        return b
    if protocol == "gemini":
        return {"contents": [{"role": "user", "parts": [{"text": text}]}],
                "generationConfig": {"maxOutputTokens": max_out}}
    raise ValueError(protocol)


def classify_http_error(code, raw):
    """把常见失败翻译成大白话 / Turn common failures into plain words."""
    text = raw[:400].decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw)[:400]
    low = text.lower()
    if "<html" in low or "<!doctype" in low:
        return "返回的是网页而不是 JSON：Base URL 多半填成了网站页面地址 / got an HTML page: base URL points to a website"
    if code == 401:
        return "地址和路径正确，但密钥无效或已删除（401） / endpoint OK, key rejected (401)"
    if code == 403:
        return "密钥被拒绝：余额不足、分组无权限或被限制（403） / forbidden: balance, group or permission (403)"
    if code == 404:
        return "路径不存在（404）：检查 Base URL 是否多写或少写了 /v1 / path not found: check /v1 in base URL"
    if code == 400:
        return "请求被拒（400）：多半是模型名或参数不被支持 / bad request: model name or parameter"
    if code == 429:
        return "被限流（429）：并发太高或上游繁忙 / rate limited"
    if code >= 500:
        return f"服务端错误（{code}）：上游或网关故障，稍后重试 / server error"
    return f"HTTP {code}"


def post(url, headers, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    return urllib.request.urlopen(req, timeout=TIMEOUT, context=ssl.create_default_context())


def parse_usage(protocol, obj):
    """返回 (input, output, cache_write, cache_read)。缺字段返回 None。"""
    if not isinstance(obj, dict):
        return None
    if protocol == "openai-chat":
        u = obj.get("usage") or {}
        if not u:
            return None
        cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
        # OpenAI 口径：prompt_tokens 已包含 cached_tokens
        return (u.get("prompt_tokens", 0) - cached, u.get("completion_tokens", 0), 0, cached)
    if protocol == "openai-responses":
        u = obj.get("usage") or (obj.get("response") or {}).get("usage") or {}
        if not u:
            return None
        cached = (u.get("input_tokens_details") or {}).get("cached_tokens") or 0
        return (u.get("input_tokens", 0) - cached, u.get("output_tokens", 0), 0, cached)
    if protocol == "anthropic":
        u = obj.get("usage") or {}
        if not u:
            return None
        return (u.get("input_tokens", 0), u.get("output_tokens", 0),
                u.get("cache_creation_input_tokens", 0) or 0, u.get("cache_read_input_tokens", 0) or 0)
    if protocol == "gemini":
        u = obj.get("usageMetadata") or {}
        if not u:
            return None
        cached = u.get("cachedContentTokenCount", 0) or 0
        out = (u.get("candidatesTokenCount", 0) or 0) + (u.get("thoughtsTokenCount", 0) or 0)
        return (u.get("promptTokenCount", 0) - cached, out, 0, cached)
    return None


def text_delta(protocol, obj):
    """流式事件里是否带有正文或思考内容 / does this stream event carry content?"""
    try:
        if protocol == "openai-chat":
            d = obj["choices"][0].get("delta") or {}
            return bool(d.get("content") or d.get("reasoning_content") or d.get("reasoning"))
        if protocol == "openai-responses":
            return obj.get("type", "").endswith(".delta")
        if protocol == "anthropic":
            return obj.get("type") == "content_block_delta"
        if protocol == "gemini":
            parts = obj["candidates"][0]["content"].get("parts") or []
            return any(p.get("text") for p in parts)
    except (KeyError, IndexError, TypeError):
        return False
    return False


def step_reach(base, protocol, key):
    say("\n[1] 连通与鉴权 / reachability & auth")
    if protocol == "gemini":
        url = f"{base}/v1beta/models"
    else:
        url = f"{base}/v1/models"
    req = urllib.request.Request(url, headers=headers_for(protocol, key))
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as r:
            raw = r.read()
            ms = (time.time() - t0) * 1000
            if b"<html" in raw[:300].lower():
                say(f"  ✗ {url} 返回了网页：Base URL 填错了 / returned HTML: wrong base URL")
                return False
            n = None
            try:
                j = json.loads(raw)
                n = len(j.get("data") or j.get("models") or [])
            except ValueError:
                pass
            say(f"  ✓ {url} → {r.status}，{ms:.0f} ms" + (f"，可见模型 {n} 个 / {n} models" if n is not None else ""))
            return True
    except urllib.error.HTTPError as e:
        raw = e.read()
        say(f"  ✗ {url} → {e.code}：{classify_http_error(e.code, raw)}")
        return e.code not in (401, 403, 404)
    except (urllib.error.URLError, socket.timeout) as e:
        say(f"  ✗ 连不上 {url}：{e} / cannot connect (DNS, proxy or network)")
        return False


def step_hi(base, protocol, model, key):
    say("\n[2] 「hi」测试：一句 hi 被记了多少输入 token / how many input tokens does 'hi' cost?")
    url = endpoint(protocol, base, model, stream=False)
    t0 = time.time()
    try:
        with post(url, headers_for(protocol, key), body_for(protocol, model, "hi", False)) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        say(f"  ✗ {e.code}：{classify_http_error(e.code, e.read())}")
        return None
    except (urllib.error.URLError, socket.timeout) as e:
        say(f"  ✗ 请求失败：{e}")
        return None
    ms = (time.time() - t0) * 1000
    try:
        obj = json.loads(raw)
    except ValueError:
        say(f"  ✗ {classify_http_error(200, raw)}")
        return None
    u = parse_usage(protocol, obj)
    if not u:
        say(f"  ? 响应里没有 usage 字段，无法判断（{ms:.0f} ms） / no usage in response")
        return None
    inp, out, cw, cr = u
    total = inp + cw + cr
    say(f"  输入 input={inp}  缓存写入 cache_write={cw}  缓存读取 cache_read={cr}  输出 output={out}  （{ms:.0f} ms）")
    if total <= NORMAL_MAX:
        say(f"  ✓ 合计 {total}：正常，没有发现夹带内容 / normal, nothing injected")
    elif total <= SUSPECT_MAX:
        say(f"  ! 合计 {total}：偏高，对方可能加了一小段系统提示 / slightly high, maybe a short system prompt")
    else:
        say(f"  ✗ 合计 {total}：明显偏高，每次请求都被夹带了约 {total} 个 token 的额外内容，")
        say("    这部分会算进你的费用，也会影响模型行为 / large hidden prompt injected; you pay for it")
    return total


def step_stream(base, protocol, model, key):
    say("\n[3] 首字耗时（流式） / time to first token (streaming)")
    url = endpoint(protocol, base, model, stream=True)
    t0 = time.time()
    t_head = t_first = None
    usage = None
    try:
        with post(url, headers_for(protocol, key), body_for(protocol, model, "用一句话介绍你自己。", True, max_out=256)) as r:
            t_head = time.time()
            for line in r:
                line = line.strip()
                if not line.startswith(b"data:"):
                    continue
                data = line[5:].strip()
                if data == b"[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except ValueError:
                    continue
                if t_first is None and text_delta(protocol, obj):
                    t_first = time.time()
                if protocol == "anthropic" and obj.get("type") == "message_start":
                    usage = parse_usage(protocol, obj.get("message") or {})
                got = parse_usage(protocol, obj)
                if got and (protocol != "anthropic" or got[0] or got[1]):
                    usage = got if protocol != "anthropic" or usage is None else (usage[0], got[1], usage[2], usage[3])
    except urllib.error.HTTPError as e:
        say(f"  ✗ {e.code}：{classify_http_error(e.code, e.read())}")
        return
    except (urllib.error.URLError, socket.timeout) as e:
        say(f"  ✗ 请求失败或超时：{e}")
        return
    t_end = time.time()
    say(f"  收到响应头 headers: {(t_head - t0) * 1000:.0f} ms")
    if t_first:
        say(f"  首个内容 first token: {(t_first - t0) * 1000:.0f} ms")
    else:
        say("  ? 没收到正文（推理模型可能把额度都用在思考上） / no visible text (reasoning models may think only)")
    say(f"  全部结束 total: {(t_end - t0) * 1000:.0f} ms")
    if usage:
        say(f"  用量 usage: input={usage[0]} output={usage[1]} cache_write={usage[2]} cache_read={usage[3]}")


def step_cache(base, protocol, model, key):
    say("\n[4] 缓存测试：同一段长前缀连发两次 / prompt-cache test (same long prefix twice)")
    seed = str(int(time.time()))
    prefix = (f"[probe {seed}] " + "下面是一段用于缓存测试的固定文本，请忽略内容。" * 120)
    text = prefix + "\n\n只回复 OK。"
    results = []
    for i in (1, 2):
        try:
            with post(endpoint(protocol, base, model, False), headers_for(protocol, key),
                      body_for(protocol, model, text, False, max_out=32, cache=True)) as r:
                u = parse_usage(protocol, json.loads(r.read()))
        except urllib.error.HTTPError as e:
            say(f"  ✗ 第 {i} 次：{e.code} {classify_http_error(e.code, e.read())}")
            return
        except (urllib.error.URLError, socket.timeout, ValueError) as e:
            say(f"  ✗ 第 {i} 次失败：{e}")
            return
        if not u:
            say("  ? 响应里没有 usage，无法判断")
            return
        results.append(u)
        say(f"  第 {i} 次 run {i}: input={u[0]} cache_write={u[2]} cache_read={u[3]}")
        time.sleep(2)
    second = results[1]
    total2 = second[0] + second[2] + second[3]
    if total2 and second[3] / total2 >= 0.5:
        say(f"  ✓ 第二次有 {second[3] / total2:.0%} 记为缓存读取 / cache hit on 2nd call")
    else:
        say("  ! 第二次没有明显的缓存读取：可能该模型/渠道不支持缓存，或前缀不够长 / no cache hit observed")


def main():
    ap = argparse.ArgumentParser(description="中转站 / API 接口自测 · relay & API self-check")
    ap.add_argument("--base", required=True, help="站点根地址，例如 https://apikl.ai（不带 /v1）")
    ap.add_argument("--protocol", required=True,
                    choices=["openai-chat", "openai-responses", "anthropic", "gemini"])
    ap.add_argument("--model", required=True, help="模型名，例如 claude-sonnet-5-5 / gpt-5.6-sol / gemini-3.8-flash")
    ap.add_argument("--cache", action="store_true", help="额外做缓存测试（会多花约 4000 输入 token）")
    ap.add_argument("--skip-stream", action="store_true", help="跳过首字耗时测试")
    args = ap.parse_args()

    key = os.environ.get("RELAY_API_KEY") or getpass.getpass("API Key（输入时不显示）: ").strip()
    if not key:
        say("没有密钥：请先 export RELAY_API_KEY=sk-... / no key")
        return 2
    base = norm_base(args.base)
    say(f"目标 target: {base}  协议 protocol: {args.protocol}  模型 model: {args.model}")
    say(f"密钥 key: {key[:5]}…{key[-4:] if len(key) > 12 else ''}（只显示首尾）")

    ok = step_reach(base, args.protocol, key)
    if not ok:
        say("\n连通/鉴权没通过，后面的测试跳过。 / stopping: reachability or auth failed.")
        return 1
    step_hi(base, args.protocol, args.model, key)
    if not args.skip_stream:
        step_stream(base, args.protocol, args.model, key)
    if args.cache:
        step_cache(base, args.protocol, args.model, key)
    say("\n完成。结果只代表这一次、这一个模型；建议在不同时段多测几次。 / Done. One run, one model — repeat at different times.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
