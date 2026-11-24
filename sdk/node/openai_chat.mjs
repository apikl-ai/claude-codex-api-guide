// OpenAI 官方 Node SDK。npm i openai
// 运行：APIKL_API_KEY=sk-... node openai_chat.mjs
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "https://apikl.ai/v1",          // 带 /v1
  apiKey: process.env.APIKL_API_KEY,
});

const stream = await client.chat.completions.create({
  model: "gpt-5.6-sol",
  messages: [{ role: "user", content: "用一句话介绍你自己" }],
  stream: true,
});
for await (const chunk of stream) {
  process.stdout.write(chunk.choices[0]?.delta?.content ?? "");
}
process.stdout.write("\n");
