import json, re
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"),
                base_url="https://api.deepseek.com")

comments = [
    "老师上课很生动,例子用得好,但语速快,后排容易跟不上。",
    "课程内容充实但节奏偏快,希望能多给例题,作业有点难。",
    "教学很棒,就是教室太小,希望换个大教室。",
]

def parse(comment):
    # 用少样本(few-shot) + 明确禁止解释 + temperature=0，三重保障稳定JSON
    fewshots = [
        {"input": "老师讲课很生动,但作业难度偏高,希望能多给例题",
         "output": '{"teacher_quality":"good","pace":"适中","problem":"作业偏难","suggestion":"增加例题"}'},
    ]
    messages = [{"role":"system","content":"你是教务分析助手。只输出符合格式的JSON,禁止任何解释、前后缀、代码块。你格式必须与例子完全一致。如需推理请在心里完成,不要输出。"}]
    for ex in fewshots:
        messages.append({"role":"user","content":f"评语:{ex['input']}"})
        messages.append({"role":"assistant","content":ex["output"]})
    messages.append({"role":"user","content":f"评语:{comment}"})

    resp = client.chat.completions.create(
        model="deepseek-chat",
        temperature=0,
        messages=messages,
    )
    raw = resp.choices[0].message.content
    # 兜底：无论有没有前后缀噪音，都能抽出JSON
    match = re.search(r'\{.*\}', raw, re.S)
    return json.loads(match.group(0))

for c in comments:
    print(parse(c))