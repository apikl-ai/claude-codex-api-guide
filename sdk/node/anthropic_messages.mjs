// Anthropic 官方 Node SDK 调用 Claude。npm i @anthropic-ai/sdk
// 运行：APIKL_API_KEY=sk-... node anthropic_messages.mjs
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic({
  baseURL: "https://apikl.ai",             // 根地址，不带 /v1
  apiKey: process.env.APIKL_API_KEY,
});

const msg = await client.messages.create({
  model: "claude-sonnet-5-5",
  max_tokens: 512,
  messages: [{ role: "user", content: "用一句话介绍你自己" }],
});
console.log(msg.content[0].text);
console.log(msg.usage);
