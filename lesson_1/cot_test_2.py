from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

question = "一只鸡2条腿,一头牛4条腿。农场鸡牛共12个头、34条腿,各几只?"

# 版本1：不限制
v1 = "问题:" + question
# 版本2：禁止解释，只给答案
v2 = question + "\n只输出两个数字：鸡几只、牛几只，不要任何过程。"
# 版本3：强制一步一步详细想
v3 = question + "\n请把每一步推理都写出来，最后再给结论。"

for v in [v1, v2, v3]:
    r = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": v}],
        temperature=0,
    )
    print("---", "不限制" if v==v1 else ("禁止解释" if v==v2 else "强制思考"), "---")
    print(r.choices[0].message.content, "\n")