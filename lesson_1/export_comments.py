import json, re
import pandas as pd
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"),
                base_url="https://api.deepseek.com")

# ① 评语库（以后换成你真实的学生问卷/教学评价）
comments = [
    "老师上课很生动,例子用得好,但语速快,后排容易跟不上。",
    "课程内容充实但节奏偏快,希望能多给例题,作业有点难。",
    "教学很棒,就是教室太小,希望换个大教室。",
    "讲解清晰,互动多,但考试题目比练习难太多。",
    "课件做得很好,就是部分概念太快带过,希望放慢。",
]

def parse(comment):
    fewshots = [
        {"input": "老师讲课很生动,但作业难度偏高,希望能多给例题",
         "output": '{"teacher_quality":"good","pace":"适中","problem":"作业偏难","suggestion":"增加例题"}'},
    ]
    messages = [{"role":"system","content":"你是教务分析助手。只输出符合格式的JSON,禁止任何解释、前后缀、代码块,如需推理请在心里完成。"}]
    for ex in fewshots:
        messages.append({"role":"user","content":f"评语:{ex['input']}"})
        messages.append({"role":"assistant","content":ex["output"]})
    messages.append({"role":"user","content":f"评语:{comment}"})

    resp = client.chat.completions.create(
        model="deepseek-chat", temperature=0, messages=messages,
    )
    raw = resp.choices[0].message.content
    match = re.search(r'\{.*\}', raw, re.S)      # 兜底防污染
    return json.loads(match.group(0))

# ② 逐条解析，把所有结果收进一个"列表"，每条是字典
results = []
for c in comments:
    d = parse(c)
    d["原评语"] = c                      # 别忘了保留原始文本
    results.append(d)

print("解析出", len(results), "条结果")
for r in results:
    print(r)

# ③★★★★★ 这一课的核心：字典列表 → DataFrame → Excel
df = pd.DataFrame(results)                # 字典列表转表格
df.to_excel("教学评语分析.xlsx", index=False)   # 导出Excel

print("\n已导出: 教学评语分析.xlsx")