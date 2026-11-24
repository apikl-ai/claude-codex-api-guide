#!/usr/bin/env bash
# 用一把「假密钥」检查本仓库里所有地址和路径是否写对，不花一分钱。
# Checks every endpoint used in this repo with a fake key: correct path => 401, wrong path => 404.
#
#   bash tests/smoke_fake_key.sh                 # 默认测 https://apikl.ai
#   BASE=https://你的中转站 bash tests/smoke_fake_key.sh   # 也能拿来测别家
#
# 期望结果：前 7 行都是 401（地址和路径正确、密钥被拒），最后 2 行是 404（故意写错的反例）。
set -u
BASE="${BASE:-https://apikl.ai}"
FAKE="sk-fake-$(date +%s)-not-a-real-key"
pass=0; fail=0

check() { # 名称 期望状态码 curl参数...
  local name="$1" want="$2"; shift 2
  local got
  got=$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 "$@")
  if [ "$got" = "$want" ]; then pass=$((pass+1)); mark="✓"; else fail=$((fail+1)); mark="✗"; fi
  printf '%s %-46s 期望 %s  实际 %s\n' "$mark" "$name" "$want" "$got"
}
J='Content-Type: application/json'

check "GET  /v1/models"                       401 "$BASE/v1/models" -H "Authorization: Bearer $FAKE"
check "POST /v1/chat/completions (OpenAI)"    401 "$BASE/v1/chat/completions" -H "Authorization: Bearer $FAKE" -H "$J" -d '{"model":"gpt-5.6-sol","messages":[{"role":"user","content":"hi"}]}'
check "POST /v1/responses (Codex)"            401 "$BASE/v1/responses" -H "Authorization: Bearer $FAKE" -H "$J" -d '{"model":"gpt-5.6-sol","input":"hi"}'
check "POST /v1/messages (Claude, x-api-key)" 401 "$BASE/v1/messages" -H "x-api-key: $FAKE" -H "anthropic-version: 2023-06-01" -H "$J" -d '{"model":"claude-sonnet-5-5","max_tokens":16,"messages":[{"role":"user","content":"hi"}]}'
check "POST /v1/messages (Claude Code, Bearer)" 401 "$BASE/v1/messages" -H "Authorization: Bearer $FAKE" -H "anthropic-version: 2023-06-01" -H "$J" -d '{"model":"claude-sonnet-5-5","max_tokens":16,"messages":[{"role":"user","content":"hi"}]}'
check "POST /v1beta/...:generateContent (Gemini)" 401 "$BASE/v1beta/models/gemini-3.8-flash:generateContent" -H "x-goog-api-key: $FAKE" -H "$J" -d '{"contents":[{"parts":[{"text":"hi"}]}]}'
check "GET  /v1/usage (余额)"                  401 "$BASE/v1/usage" -H "Authorization: Bearer $FAKE"
# 反例：Claude Code 的地址多写了 /v1、google-genai 3.x 不指定 v1beta 时的路径
check "反例 /v1/v1/messages"                   404 "$BASE/v1/v1/messages" -H "x-api-key: $FAKE" -H "$J" -d '{}'
check "反例 /v1/models/...:generateContent"     404 "$BASE/v1/models/gemini-3.8-flash:generateContent" -H "x-goog-api-key: $FAKE" -H "$J" -d '{}'

echo "通过 $pass，不符 $fail（目标：$BASE）"
[ "$fail" -eq 0 ]
