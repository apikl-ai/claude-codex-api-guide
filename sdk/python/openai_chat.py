"""OpenAI 官方 SDK 调用（Chat Completions）。pip install openai
GPT、DeepSeek 等 OpenAI 兼容模型都用这种写法；base_url 要带 /v1。
"""
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://apikl.ai/v1",
    api_key=os.environ["APIKL_API_KEY"],   # 不要把密钥写死在代码里
)

resp = client.chat.completions.create(
    model="gpt-5.6-sol",
    messages=[{"role": "user", "content": "用一句话介绍你自己"}],
)
print(resp.choices[0].message.content)
print(resp.usage)
