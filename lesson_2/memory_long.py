"""
长期记忆助手:用JSON文件当"记忆库",实现 存->查->喂 三步。
原理:跨对话保存用户信息,回答时检索相关记忆喂给模型。
"""
import os, json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

MEMORY_FILE = "user_memory.json"   # 记忆库存放的文件


# ---------- 1. 保存:把信息写入记忆库 ----------
def save_memory(fact):
    """把一条用户信息(事实)存进JSON记忆库。fact:如"我是教统计学的柴老师" """
    mem = load_all()              # 先读现有的全部记忆
    if fact not in mem:           # 避免重复存
        mem.append(fact)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(mem, f, ensure_ascii=False, indent=2)  # 写回文件


# ---------- 2. 检索:从记忆库找出相关条目 ----------
def recall(query, top=3):
    """根据新问题query,用关键词匹配,从记忆库返回最相关的top条。"""
    mem = load_all()
    # 简单的相关度:统计query里每个词在记忆条目里出现几次
    scored = []
    for fact in mem:
        score = sum(1 for w in query.split() if w in fact)  # 匹配词数当分数
        if score > 0:
            scored.append((score, fact))
    scored.sort(reverse=True)     # 按相关度从高到低
    return [fact for _, fact in scored[:top]]


# ---------- 辅助:读取全部记忆 ----------
def load_all():
    """读取记忆库文件全部条目,没有就返回空列表。"""
    if not os.path.exists(MEMORY_FILE):
        return []
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------- 3. 注入 + 回答 ----------
def ask(question):
    """
    核心:把检索到的相关记忆注入,再让模型回答。
    """
    # 第一步先试着"记忆":如果用户话里像在告知信息(含'我是'/'我教'/'我喜欢'等),存起来
    for kw in ["我是", "我教", "我喜欢", "我偏好", "我的"]:
        if kw in question:
            save_memory(question)
    # 从记忆库检索相关问题相关的旧信息
    recalled = recall(question)
    # 把记忆拼进system,告诉模型"这些是你知道的用户背景"
    background = "以下是关于用户你已知的长期信息:\n" + "\n".join(recalled) if recalled else "尚无已知的用户背景信息。"
    messages = [
        {"role": "system", "content": "你是一位贴心的助理。回答时如有已知用户信息,请结合背景回答。"},
        {"role": "system", "content": background},
        {"role": "user", "content": question},
    ]
    resp = client.chat.completions.create(model="deepseek-chat", messages=messages)
    return resp.choices[0].message.content


if __name__ == "__main__":
    # 第一次:告知身份(会被存进user_memory.json)
    print(ask("你好,我是教统计学的柴老师"))
    # 第二次模拟"下次打开程序"(换了session,但记忆文件还在)
    print("\n--- 模拟重启程序后进行新对话 ---")
    print(ask("你还记得我是教什么的老师吗?"))   # 靠JSON记忆库,它能答出来