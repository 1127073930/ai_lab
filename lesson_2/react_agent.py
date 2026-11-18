"""
ReAct 文献整理Agent:自动 搜索->读网页->归纳要点,无需用户逐步指挥。
原理:模型循环"思考下一步->调工具->看结果",直到它认为信息够了,才开始总结。
"""
import os, json, re, urllib.parse
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ---------- 工具1: 搜索 ----------
def web_search(query):
    """Bing搜索,返回几条标题+链接。"""
    url = "https://www.baidu.com/s?wd=" + urllib.parse.quote(query)   # 百度
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for li in soup.select("li.b_algo"):
        a = li.find("a")
        if a and a.get("href"):
            out.append(f"- {a.get_text(strip=True)[:80]} : {a['href']}")
    return "\n".join(out[:5]) if out else "没搜到,换关键词"

# ---------- 工具2: 读网页正文 ----------
def fetch_url(url):
    """抓网页正文(前1500字)。"""
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{2,}", "\n", text)
    return text[:1500]

# ---------- 注册工具 ----------
TOOLS = [
    {"type": "function", "function": {"name": "web_search",
        "description": "搜索关键词,返回相关结果的标题和链接",
        "parameters": {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type": "function", "function": {"name": "fetch_url",
        "description": "读取指定网页URL的正文",
        "parameters": {"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}},
]

def run_agent(task):
    """
    核心:自主多步运行的ReAct循环。
    task: 用户给的调研任务
    流程:循环让模型决定下一步,直到它不再调工具(信息够)才输出最终总结。
    """
    messages = [
        {"role": "system", "content":
            "你是科研调研助手。你可以搜索和读取网页来收集信息。"
            "请自主决定:先搜索,必要时读几个网页,信息充分后直接综合给出有条理的要点总结。不要输出思考过程,只输出最终要点。"},
        {"role": "user", "content": task},
    ]
    step = 0
    while step < 10:                          # 最多10步,防止死循环
        resp = client.chat.completions.create(
            model="deepseek-chat", messages=messages, tools=TOOLS)
        msg = resp.choices[0].message
        messages.append(msg)

        if not getattr(msg, "tool_calls", None):   # 不再调工具 -> 输出最终总结
            return msg.content

        for tc in msg.tool_calls:                  # 要调工具 -> 执行并喂回
            args = json.loads(tc.function.arguments)
            print(f"🧠 步骤{step+1}: 调用 {tc.function.name}({args})")
            if tc.function.name == "web_search":
                result = web_search(args["query"])
            elif tc.function.name == "fetch_url":
                result = fetch_url(args["url"])
            else:
                result = "未知工具"
            messages.append({"role":"tool","tool_call_id":tc.id,"content":str(result)})
        step += 1
    return "已达最大步数,可能信息不完整,请简化任务重试。"

if __name__ == "__main__":
    # 示例:调研一个你真关心的话题
    print(run_agent("调研一下2026年大模型在教育领域的几个主要应用方向,整理成3-5条要点。"))
