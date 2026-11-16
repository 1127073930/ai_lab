import os, json, urllib.parse
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# ---- 给模型"注册"一个工具：联网搜索 ----
tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "联网搜索公开信息,获取最新资料",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要搜索的关键词"}
                },
                "required": ["query"]
            }
        }
    }
]

def web_search(query):
    """模拟一个搜索工具:返回一段占位结果(真实联网搜索我们稍后接入)。"""
    return f"[搜索到关于'{query}'的结果]: 这里是你在网上查到的资料..."

# ---- 让模型"思考该调哪个工具" ----
resp = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "user", "content": "帮我查一下2026年国家最新的教育相关政策动向"}
    ],
    tools=tools,        # 告诉模型你有这些工具
    tool_choice="auto", # 让模型自己决定要不要调
)

msg = resp.choices[0].message
print("模型的回答(可能只是个工具调用请求):")
print(msg)

# 如果模型决定要调工具:
if msg.tool_calls:
    for tc in msg.tool_calls:
        fn = tc.function
        args = json.loads(fn.arguments)
        print(f"\n🧠 模型决定调用: {fn.name}({args})")
        result = web_search(args["query"])
        print(f"🔧 工具返回: {result}")

# 把工具结果作为assistant之后的消息喂回去
messages = [
    {"role": "user", "content": "帮我查一下2026年国家最新的教育相关政策动向"}
]
# 第一次:模型返回工具调用请求
msg = client.chat.completions.create(model="deepseek-chat", messages=messages, tools=tools).choices[0].message
# 我们把模型的决定追加进历史
messages.append(msg)
# 模型说要调哪个就调哪个
if msg.tool_calls:
    for tc in msg.tool_calls:
        args = json.loads(tc.function.arguments)
        result = web_search(args["query"])
        # 把工具结果也追加进历史
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
# 现在让模型基于"搜到的东西"给最终答案
final = client.chat.completions.create(model="deepseek-chat", messages=messages, tools=tools).choices[0].message.content
print("\n🧠 模型基于搜索结果给你的最终回答:")
print(final)