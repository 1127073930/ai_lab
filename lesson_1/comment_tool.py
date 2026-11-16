import json
import os
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# 用 few-shot 教模型我们要的格式
EXAMPLES = [
    ("老师讲课很生动,但作业难度偏高,希望能多给例题",
     '{"teacher_quality": "good", "pace": "适中", "problem": "作业偏难", "suggestion": "增加例题"}'),
    ("课程很有趣但进度太快,我跟不上",
     '{"teacher_quality": "good", "pace": "过快", "problem": "节奏快", "suggestion": "放慢进度"}'),
    ("老师讲得一般,课堂有点闷,希望多点互动",
     '{"teacher_quality": "normal", "pace": "适中", "problem": "互动少", "suggestion": "增加互动"}'),
]

def parse_comment(comment):
    messages = [{"role": "system",
                 "content": "你是教务数据分析助手。严格按给定JSON格式输出,不要输出任何额外文字。"}]
    for inp, out in EXAMPLES:
        messages.append({"role": "user", "content": f"评语: {inp}"})
        messages.append({"role": "assistant", "content": out})
    messages.append({"role": "user", "content": f"评语: {comment}"})

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0,
    )
    # 把模型输出的JSON文本解析成Python字典
    return json.loads(resp.choices[0].message.content)

def parse_many(comments):
    """批量解析,容错:单条失败不影响整体。"""
    results = []
    for i, c in enumerate(comments, 1):
        print(f"正在处理 {i}/{len(comments)}: {c[:15]}...")
        try:
            d = parse_comment(c)
            d["原始评语"] = c          # 把原文也存进去,方便对照
            results.append(d)
        except Exception as e:
            # 单条出错不中断,记录下来稍后处理
            print(f"❌ 第{i}条解析失败: {e}")
            results.append({"原始评语": c, "error": str(e)})
        print(f"   -> {d['teacher_quality']} / {d['pace']} / {d['problem']}")
    return results


def save_to_excel(rows, filename="评语分析结果.xlsx"):
    """把字典列表转成DataFrame并导出Excel。"""
    df = pd.DataFrame(rows)          # 列表[字典] -> 表格
    df.to_excel(filename, index=False)  # 导出,去掉行号
    print(f"✅ 已保存 {len(rows)} 条评语到 {filename}")
    return df



def parse_from_excel(input_path, comment_col="评语"):
    """从Excel读一列评语,批量解析,加一列满意度分析,导出新表。"""
    df = pd.read_excel(input_path)            # 用R的思维:读数据
    comments = df[comment_col].tolist()       # 取评语列

    rows = parse_many(comments)               # 批量交给大模型
    out_df = pd.DataFrame(rows)

    # 加一个简单的满意度统计列
    out_df["满意度"] = out_df["teacher_quality"].map(
        {"good": "满意", "normal": "一般", "bad": "不满意"}
    )
    out_df.to_excel("评语分析结果_带统计.xlsx", index=False)
    print("✅ 已存储:", len(out_df), "条")

    # 统计分布,方便汇报
    print("\n=== 满意度分布 ===")
    print(out_df["满意度"].value_counts())
    return out_df

if __name__ == "__main__":
    df = parse_from_excel("学生评语.xlsx")
    print("\n=== 表格前几行 ===")
    print(df.head())