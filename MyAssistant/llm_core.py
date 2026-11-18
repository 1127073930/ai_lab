# llm_core.py — 第③部分：调用大模型（Agent 的"大脑"）
# 职责：负责与大模型 API 通信，并管理"自主多步循环"。
#      大模型看问题决定调哪个工具(见tools.TOOLS)，这里循环执行工具并把结果喂回，
#      直到模型认为信息够了(不再返回tool_calls)才给出最终答案。
# 说明：不关心知识库怎么建、工具怎么实现——只管"循环调度"。这就是"分层"的好处。
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import tools  # 导入工具定义和注册表

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

# 系统提示词：定义助手角色，并告诉它有哪些能力、何时该总结
SYSTEM_PROMPT = (
    "你是全能科研助手。你有三种能力: "
    "① ask_knowledge_base 查本地讲义/知识库; "
    "② web_search 联网查最新资讯; "
    "③ fetch_url 读取具体网页。"
    "请根据问题自主选择合适工具,信息充分后综合给出清晰、有条理的中文回答。不要输出思考过程。"
)


def run_turn(messages, collection, max_steps=12):
    """
    执行一轮"自主多步循环"，返回(最终回答, 本轮用到的工具列表)。
    messages   : 已累积的历史(messages列表, 含system+以往对话+当前问题)
    collection : 当前选中的chroma知识库对象(传给ask_knowledge_base用)
    max_steps  : 最多循环几步，防止死循环/超预算
    """
    used = []                      # 记录本轮调用了哪些工具，供界面展示
    for step in range(max_steps):
        # 1) 请求模型，带上全部消息 + 工具清单
        resp = client.chat.completions.create(
            model="deepseek-chat", messages=messages, tools=tools.TOOLS)
        msg = resp.choices[0].message
        messages.append(msg)       # 模型的这一回应(可能是要调工具，也可能是最终答案)入列

        # 2) 若模型没有再请求工具 -> 信息够了，它给出的就是最终答案
        if not getattr(msg, "tool_calls", None):
            return msg.content, used

        # 3) 模型请求了工具 -> 逐个执行，把结果作为"工具反馈"塞回对话
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)   # 解析模型给的参数(JSON字符串)
            name = tc.function.name
            # 按工具名分发到对应函数（collection只在ask_knowledge_base时需要）
            if name == "ask_knowledge_base":
                result = tools.ask_knowledge_base(args["query"], collection)
            elif name == "web_search":
                result = tools.web_search(args["query"])
            elif name == "fetch_url":
                result = tools.fetch_url(args["url"])
            else:
                result = "未知工具"
            used.append(f"{name}: {args}")
            # role="tool" + 相同的tool_call_id 才能对应上模型的那次请求(你踩过这个坑)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})
    return "步数用尽,请简化问题。", used