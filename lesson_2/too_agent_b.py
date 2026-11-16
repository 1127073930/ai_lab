"""
方案B：真·联网搜索 + 读网页的办公助手
原理：模型决定调工具 -> 代码真去搜/读网页 -> 结果喂回 -> 模型基于真实内容回答
"""
import os, json, re, urllib.parse   # os读环境变量; json解析工具参数; re处理文本; urllib拼URL
import requests                     # 发起网络请求(上网)
from bs4 import BeautifulSoup       # 解析HTML,提取网页文字
from dotenv import load_dotenv
from openai import OpenAI

# 读取 .env 里的 API Key 并初始化客户端
load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

# 伪装成浏览器访问,避免很多网站拒绝程序抓取
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


# ---------- 工具1: 联网搜索(用Bing结果页,无需API key) ----------
def web_search(query):
    """搜索关键词,返回前几条结果的 标题+链接 文本。"""
    # 把关键词拼进Bing搜索网址(quote处理中文等特殊字符)
    url = "https://www.bing.com/search?q=" + urllib.parse.quote(query)
    r = requests.get(url, headers=HEADERS, timeout=15)   # 请求搜索页,最多等15秒
    soup = BeautifulSoup(r.text, "html.parser")          # 解析返回的HTML
    out = []
    for li in soup.select("li.b_algo"):                  # Bing结果条目藏在 li.b_algo 里
        a = li.find("a")
        if a and a.get("href"):
            out.append(f"- {a.get_text(strip=True)[:80]} : {a['href']}")
    return "\n".join(out[:5]) if out else "没有搜到结果,请换关键词"


# ---------- 工具2: 读取网页正文 ----------
def fetch_url(url):
    """抓取指定网页,去掉标签和脚本,返回纯文本正文(前2000字)。"""
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):  # 删掉无用的脚本/导航
        tag.decompose()
    text = soup.get_text(separator="\n")     # 取出纯文本
    text = re.sub(r"\n{2,}", "\n", text)     # 压缩多余空行
    return text[:2000]                       # 只留前2000字,防止内容过长


# ---------- 把两个工具"注册"给模型 ----------
tools = [
    {"type": "function", "function": {"name": "web_search",
        "description": "联网搜索查询关键词,返回相关结果的标题和链接",
        "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "搜索关键词"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "fetch_url",
        "description": "读取指定网页URL的正文文本",
        "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "网页完整URL,含https://"}}, "required": ["url"]}}},
]


def call_model(messages):
    """调用模型,并带上可用工具列表,返回模型的回复。"""
    return client.chat.completions.create(
        model="deepseek-chat", messages=messages, tools=tools
    ).choices[0].message


# ---------- 主循环: 决定->执行->喂回->回答 ----------
def ask(question):
    messages = [{"role": "user", "content": question}]
    msg = call_model(messages)     # 第1次问:看模型要不要调工具
    messages.append(msg)
    for _ in range(10):             # 最多循环5轮,防止死循环
        if not getattr(msg, "tool_calls", None):   # 模型不再调工具,直接给答案
            return msg.content
        for tc in msg.tool_calls:                  # 模型要调工具,逐个执行
            args = json.loads(tc.function.arguments)   # 解析模型给的参数
            print(f"🧠 调用 {tc.function.name}({args})")
            if tc.function.name == "web_search":
                result = web_search(args["query"])
            elif tc.function.name == "fetch_url":
                result = fetch_url(args["url"])
            else:
                result = "没有这个工具"
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})
        msg = call_model(messages)     # 第2次:把工具结果喂回,模型给最终答案
        messages.append(msg)
    return "已达最大轮次,结束"


if __name__ == "__main__":
    # 先跑最稳的"读网页"验证(默认读取教育部官网,公网稳定)
    print(ask("帮我查一下2026年国家最新的教育政策动向"))