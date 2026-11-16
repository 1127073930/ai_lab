from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

question = "一个班级30人，平均身高165cm，加上一位195cm的老师，新的平均身高是多少？"

# 实验A：不思考，直接答
resp_no_cot = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": question + "\n只回答最终数字结果，不要输出任何计算过程。"}],
    temperature=0,
)
print("【不思考】\n", resp_no_cot.choices[0].message.content, "\n")

# 实验B：让模型一步步思考
resp_cot = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": question + "\n请一步步推理，并保留中间步骤，最后给出结论。"}],
    temperature=0,
)
print("【思考链】\n", resp_cot.choices[0].message.content)