# -*- coding: utf-8 -*-
"""
第6课·A方案：用最简联网动作跑通"工具调用闭环"
目标：理解 agent 的核心骨架 —— 模型只负责"决定要搜什么"，代码去"真正联网搜"，再把结果喂回模型。
运行前：myenv\Scripts\python.exe -m pip install requests openai python-dotenv
"""
import json
import os

import requests                              # 用来发网络请求
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


# ==================== 第 1 步：给模型"说明书"，告诉它有哪些工具可用 ====================
# 这段 JSON 是"工具清单"，发给模型，让模型知道"你可以调用 web_search 这个工具，参数是 query"
tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",                     # 工具名（模型返回时靠这个名字指认）
            "description": "联网搜索最新信息。当问题是关于实时新闻、当前事件、时效性数据时需要调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要搜索的关键词"}  # 模型要填的参数
                },
                "required": ["query"],                # query 是必填参数
            },
        },
    }
]


# ==================== 第 2 步：真正干活的函数（A方案用最简联网接口）====================
def web_search(query: str) -> str:
    """
    真正去"联网"并返回一段文本给模型。
    【注意】A方案用的是一个公开热搜接口做演示（无需Key），
    真正的全网搜索是B方案要升级成的东西。这里重点是"真发了网络请求、真拿到了实时数据"。
    """
    # 用一个公开的"微博热榜"接口作为演示性联网动作（可能随接口方调整而失效，属正常）
    url = "https://api.vvhan.com/api/hotlist/wbHot"
    try:
        r = requests.get(url, timeout=10)              # 发请求，10秒超时避免卡死
        data = r.json()                                # 接口返回 JSON
        # 接口返回结构大致是 { data: [ {title, hot}, ...] }，取前5条拼成文本
        hot_list = data.get("data", [])[:5]
        lines = [f"- {item.get('title','')}" for item in hot_list]
        return "\n".join(lines) if lines else "暂无热搜数据"
    except Exception as e:                             # 网络/解析失败也不让程序崩
        return f"联网失败: {e}"


# ==================== 第 3 步：跑闭环 ====================
def ask(question: str):
    """
    一次完整的"思考+工具调用"闭环：
    发请求给模型 → 模型可能想调工具 → 我们解析参数并真正调用 → 把结果喂回模型 → 模型给最终答案。
    """
    messages = [
        {"role": "user", "content": question},
    ]

    # 第一次发请求：带上 tools，让模型知道有工具可用
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,                # ★关键：把工具清单告诉模型
    )
    msg = resp.choices[0].message

    # 判断模型是否想要调用工具（这就是上一课学的 if msg.tool_calls 那段）
    if msg.tool_calls:
        tool_call = msg.tool_calls[0]                     # 只取第一个工具调用（简化演示）
        # 模型给的是 JSON 字符串，还原成字典
        args = json.loads(tool_call.function.arguments)
        print(f"[模型请求调用] {tool_call.function.name}, 参数={args}")

        # 真正执行：调用我们的 web_search
        result = web_search(args["query"])
        print(f"[代码执行结果]\n{result}\n")

        # 把工具结果作为一条 assistant 的消息喂回模型
        messages.append(msg)                              # 追加模型的原调用请求
        messages.append({
            "role": "tool",                               # tool 角色：返回给模型工具执行结果
            "tool_call_id": tool_call.id,                 # 对应刚才那个调用
            "content": result,                            # 搜索结果文本
        })
        
        # 第二次发请求：模型基于搜索结果给出最终答案
        resp2 = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
        )
        return resp2.choices[0].message.content
    else:
        # 模型觉得不用搜，直接回答
        return msg.content


if __name__ == "__main__":
    # 用一条"需要当前信息"的问题来触发工具调用
    answer = ask("今天微博上有哪些热搜？帮我简单说几条。")
    print("【最终答案】\n", answer)