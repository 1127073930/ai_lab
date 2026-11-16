import json
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

comment = "老师上课很生动,例子用得特别好,但老师说话有点快,最后几排同学容易跟不上。"

resp = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是教务数据分析助手。请从课程评语中抽取信息并输出JSON。"},
        {"role": "user", "content": f"请把下面这条评语结构化输出: {comment}"},
    ],
    temperature=0,
)
print(resp.choices[0].message.content)
print("---- 分隔线,上面是zero-shot,下面看few-shot ----")

fewshots = [
    {"input": "老师讲课很生动,但作业难度偏高,希望能多给例题",
     "output": '{"teacher_quality": "good", "pace": "适中", "problem": "作业偏难", "suggestion": "增加例题"}'},
    {"input": "课程很有趣但进度太快,我跟不上",
     "output": '{"teacher_quality": "good", "pace": "过快", "problem": "节奏快", "suggestion": "放慢进度"}'},
]

# 构造 messages
messages = [{"role": "system", "content": "你是教务数据分析助手,严格按给定JSON格式输出,不要加任何说明文字。"}]
for ex in fewshots:
    messages.append({"role": "user", "content": f"评语: {ex['input']}"})
    messages.append({"role": "assistant", "content": ex["output"]})
messages.append({"role": "user", "content": f"评语: {comment}"})

resp2 = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    temperature=0,
)
# ---------- 下面 3 行就是今天要学的关键 ----------
raw_content = resp.choices[0].message.content   # 1. 拿到字符串
print("模型返回的字符串:\n", raw_content)        # 2. 先看看原始返回长啥样

data = json.loads(raw_content)                  # 3. 转成 Python 字典 ★
print("data 的所有键:", list(data.keys()))
print("完整内容:", data)
print("\n转成字典后的 data:", data)
print("data 的类型是:", type(data))
print("\n单独取某个字段: problem =", data["不足"])

len(raw_content)

