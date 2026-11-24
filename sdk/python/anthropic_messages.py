"""Anthropic 官方 SDK 调用 Claude（原生 Messages 协议，支持提示缓存）。pip install anthropic
注意：base_url 填根地址，不带 /v1（SDK 会自己拼 /v1/messages）。
"""
import os
import anthropic

client = anthropic.Anthropic(
    base_url="https://apikl.ai",
    api_key=os.environ["APIKL_API_KEY"],
)

long_doc = open(__file__, encoding="utf-8").read()  # 演示用：一段会被反复使用的长前缀

msg = client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=512,
    system=[
        {"type": "text", "text": "你是一个代码审阅助手。"},
        # 给长且固定的前缀打缓存标记，连续调用时可按缓存价计费
        {"type": "text", "text": long_doc, "cache_control": {"type": "ephemeral"}},
    ],
    messages=[{"role": "user", "content": "这段代码做了什么？一句话回答。"}],
)
print(msg.content[0].text)
print(msg.usage)  # 关注 cache_creation_input_tokens / cache_read_input_tokens
