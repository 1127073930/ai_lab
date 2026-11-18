"""
全能科研助手: 把 = 查本地讲义(RAG) + 联网搜索 + 读网页 三个工具合一。
模型根据你的问题,自主决定用哪个(或哪几个),信息够了就综合回答。
原理: 你react_agent的自主多步循环,只是工具清单变多了。
"""
import os, json, re, urllib.parse
import requests
from bs4 import BeautifulSoup
import chromadb
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ---------- 第0步: 连接你已有的知识库 ----------
db_path = "./course_db"        # 你course_qa_tool.py里的数据库路径
coll_name = "course"           # 你course_qa_tool.py里的集合名
client_cdb = chromadb.PersistentClient(path=db_path)
collection = client_cdb.get_or_create_collection(coll_name)

# ---------- 工具1: 查本地讲义(RAG) ----------
def ask_knowledge_base(query):
    """在本地讲义/知识库里语义检索,返回最相关片段(前3块)。"""
    try:
        res = collection.query(query_texts=[query], n_results=3)
        docs = res["documents"][0]
        return "\n".join(docs) if docs else "知识库里没检索到相关内容"
    except Exception as e:
        return f"知识库查询失败: {e}"

# ---------- 工具2: 百度搜索(方案A已验证) ----------
def web_search(query):
    """百度搜索:返回几条标题。"""
    url = "https://www.baidu.com/s?wd=" + urllib.parse.quote(query)
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for h3 in soup.find_all("h3")[:5]:
        a = h3.find("a")
        if a and a.get("href"):
            out.append(f"- {a.get_text(strip=True)[:80]}")
    return "\n".join(out) if out else "没搜到,换关键词"

# ---------- 工具3: 读网页正文 ----------
def fetch_url(url):
    """抓网页正文(前1500字)。"""
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{2,}", "\n", text)
    return text[:1500]

# ---------- 工具注册表: 告诉模型"你有哪三种能力" ----------
TOOLS = [
    {"type": "function", "function": {"name": "ask_knowledge_base",
        "description": "在主人的本地讲义/知识库里语义检索。适合问讲义里讲过的概念、公式、定理等自备资料内容",
        "parameters": {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type": "function", "function": {"name": "web_search",
        "description": "联网搜索关键词,返回最新/网络上的资料。适合问外部动态、前沿进展",
        "parameters": {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type": "function", "function": {"name": "fetch_url",
        "description": "读取某个具体网页URL的正文",
        "parameters": {"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}},
]

# ---------- 统一自主循环(复用react_agent核心,只多一个工具) ----------
def ask_all(question):
    """安心问任意问题;模型自主决定用RAG、联网还是读网页,信息够了就综合回答。"""
    messages = [
        {"role": "system", "content":
            "你是全能科研助手。你有三种能力:"
            "① ask_knowledge_base 查本地讲义/知识库;"
            "② web_search 联网查最新资讯;"
            "③ fetch_url 读取具体网页。"
            "请根据问题自主选择合适工具,信息充分后综合给出清晰、有条理的中文回答。不要输出思考过程。"},
        {"role": "user", "content": question},
    ]
    step = 0
    while step < 12:                       # 最多12步
        resp = client.chat.completions.create(
            model="deepseek-chat", messages=messages, tools=TOOLS)
        msg = resp.choices[0].message
        messages.append(msg)

        if not getattr(msg, "tool_calls", None):   # 信息够了,输出最终答案
            return msg.content

        for tc in msg.tool_calls:                  # 分发到对应工具
            args = json.loads(tc.function.arguments)
            print(f"🧠 步骤{step+1}: 调用 {tc.function.name}({args})")
            if tc.function.name == "ask_knowledge_base":
                result = ask_knowledge_base(args["query"])
            elif tc.function.name == "web_search":
                result = web_search(args["query"])
            elif tc.function.name == "fetch_url":
                result = fetch_url(args["url"])
            else:
                result = "未知工具"
            messages.append({"role":"tool","tool_call_id":tc.id,"content":str(result)})
        step += 1
    return "步数用尽,任务可能太复杂,请拆小一点。"

if __name__ == "__main__":
    # 演示:一个本地型问题 + 一个网络型问题,看模型如何自主选工具
    print("【Q1 本地型】", ask_all("根据讲义,后验概率是什么?它和先验概率什么关系?"))
    print("\n【Q2 网络型】", ask_all("2026年大模型在教育领域有哪些新应用?简要列出几点。"))
