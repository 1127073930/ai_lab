import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

def chat_with_memory(history, user_msg):
    """
    短期记忆助手：传入历史对话history,再追加用户新消息,一起发给模型。
    history: 之前所有对话的 messages 列表(含role和content)
    user_msg: 用户新说的一句话
    """
    messages = history[:]                    # 复制历史对话
    messages.append({"role": "user", "content": user_msg})  # 追加新提问
    resp = client.chat.completions.create(model="deepseek-chat", messages=messages)
    reply = resp.choices[0].message.content
    # 把这次问答也存进历史,以便下次继续
    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": reply})
    return reply

# 测试:模拟多轮对话
history = []                                 # 空历史开始
print(chat_with_memory(history, "你好,我是教统计学的柴老师"))
print(chat_with_memory(history, "你还记得我是谁吗?"))   # 因为有记忆,它能回答"你是李老师"
print(chat_with_memory(history, "你能帮我写一份大数据探索性分析的课程大纲吗?"))