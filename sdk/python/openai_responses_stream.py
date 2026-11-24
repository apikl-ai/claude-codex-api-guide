"""OpenAI 官方 SDK 调用（Responses 接口 + 流式输出）。pip install openai"""
import os
from openai import OpenAI

client = OpenAI(base_url="https://apikl.ai/v1", api_key=os.environ["APIKL_API_KEY"])

with client.responses.stream(model="gpt-5.6-sol", input="写一首四行短诗") as stream:
    for event in stream:
        if event.type == "response.output_text.delta":
            print(event.delta, end="", flush=True)
    print()
    print(stream.get_final_response().usage)
