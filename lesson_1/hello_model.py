import os
from dotenv import load_dotenv
from openai import OpenAI

# 读取同目录下的 .env 文件
load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

resp = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是一位耐心、严谨的统计学教授，爱用比喻解释概念。"},
        {"role": "user", "content": "请用一句话向大一新生解释什么是P值。"},
    ],
    temperature=0.5,
)

print(resp.choices[0].message.content)