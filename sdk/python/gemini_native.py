"""Google 官方 google-genai SDK 调用 Gemini（原生 generateContent）。pip install google-genai
base_url 填根地址，不带 /v1beta；api_version 要写 "v1beta"
（google-genai 3.x 起默认走 /v1，很多兼容网关只提供 /v1beta 原生接口，不写会 404）。
"""
import os
from google import genai
from google.genai import types

client = genai.Client(
    api_key=os.environ["APIKL_API_KEY"],
    http_options=types.HttpOptions(base_url="https://apikl.ai", api_version="v1beta"),
)

resp = client.models.generate_content(model="gemini-3.8-flash", contents="用一句话介绍你自己")
print(resp.text)
print(resp.usage_metadata)
