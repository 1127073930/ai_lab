"""
带对话记忆的全能科研助手:在多轮对话里"记住"前文的关键。
在ask_all基础上,把每轮"你问+它答"累积进一个大列表,并塞回给模型。
原理:模型"记得什么"=它能看到什么。能看到历史=>就记住了。
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

db_path, coll_name = "./course_db", "course"
client_cdb = chromadb.PersistentClient(path=db_path)
collection = client_cdb.get_or_create_collection(coll_name)

def ask_knowledge_base(query):
    try:
        res = collection.query(query_texts=[query], n_results=3)
        docs = res["documents"][0]
        return "\n".join(docs) if docs else "知识库没检索到"
    except Exception as e:
        return f"知识库查询失败:{e}"

def web_search(query):
    url = "https://www.baidu.com/s?wd=" + urllib.parse.quote(query)
    r = requests.get(url, headers=HEADERS, timeout=15); r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")
    out = [f"- {h3.find('a').get_text(strip=True)[:80]}" for h3 in soup.find_all("h3")[:5] if h3.find("a")]
    return "\n".join(out) if out else "没搜到"

def fetch_url(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script","style","nav","footer"]): t.decompose()
    return re.sub(r"\n{2,}","\n",soup.get_text("\n"))[:1500]

# 工具注册表(同第⑩课,原样搬进来即可)
TOOLS = [
    {"type": "function", "function": {"name": "ask_knowledge_base",
        "description": "在本地讲义/知识库里语义检索,适合问讲义里的概念",
        "parameters": {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type": "function", "function": {"name": "web_search",
        "description": "联网搜索关键词,返回最新资料",
        "parameters": {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type": "function", "function": {"name": "fetch_url",
        "description": "读取某个具体网页的正文",
        "parameters": {"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}},
]

def chat():
    MAX_RECALL = 20                     # 最多记住最近20条消息(滚动窗口)
    history = []                        # 短期记忆"仓库":存整个对话
    print("⚡ 全能记忆助手已启动(输入 exit 退出)")
    while True:
        user_msg = input("\n你: ")
        if user_msg.strip().lower() == "exit": break
        history.append({"role": "user", "content": user_msg})
        messages = ([{"role":"system","content":"你是全能科研助手,可查本地讲义、联网搜索、读网页,请记得我们前面的对话。"}]
                    + history[-MAX_RECALL:])
        for step in range(12):
            resp = client.chat.completions.create(model="deepseek-chat", messages=messages, tools=TOOLS)
            msg = resp.choices[0].message
            messages.append(msg)
            if not getattr(msg, "tool_calls", None):
                history.append({"role":"assistant","content":msg.content})
                print("\n助手:", msg.content)
                break
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                result = {"ask_knowledge_base":lambda q:ask_knowledge_base(q),
                          "web_search":lambda q:web_search(q),
                          "fetch_url":lambda u:fetch_url(u)}[tc.function.name](
                              args.get("query", args.get("url")))
                messages.append({"role":"tool","tool_call_id":tc.id,"content":str(result)})

if __name__ == "__main__":
    chat()
