#!/usr/bin/env bash
# 用 curl 直接打三种协议。先：export APIKL_API_KEY=sk-...
# 正常返回 JSON；返回 401 说明地址对、密钥不对；返回 404 或网页说明地址填错。
set -u
BASE="${APIKL_BASE:-https://apikl.ai}"

echo "== 1. 列出这把密钥能用的模型（OpenAI 格式）"
curl -sS "$BASE/v1/models" -H "Authorization: Bearer $APIKL_API_KEY"; echo

echo "== 2. OpenAI Chat Completions"
curl -sS "$BASE/v1/chat/completions" \
  -H "Authorization: Bearer $APIKL_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"gpt-5.6-sol","messages":[{"role":"user","content":"hi"}]}'; echo

echo "== 3. Anthropic Messages（Claude 原生协议）"
curl -sS "$BASE/v1/messages" \
  -H "x-api-key: $APIKL_API_KEY" -H "anthropic-version: 2023-06-01" -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-5-5","max_tokens":256,"messages":[{"role":"user","content":"hi"}]}'; echo

echo "== 4. Gemini 原生 generateContent"
curl -sS "$BASE/v1beta/models/gemini-3.8-flash:generateContent" \
  -H "x-goog-api-key: $APIKL_API_KEY" -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"hi"}]}]}'; echo

echo "== 5. 查余额与用量"
curl -sS "$BASE/v1/usage" -H "Authorization: Bearer $APIKL_API_KEY"; echo
