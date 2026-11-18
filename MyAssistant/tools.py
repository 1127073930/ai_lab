# tools.py — 第②部分：定义 Agent 的"工具"
# 职责：提供 Agent 能调用的各种"能力"(手脚)。包括:
#       ① 联网搜索 web_search   ② 读网页 fetch_url   ③ 查本地知识库 ask_knowledge_base
#       ④ TOOLS 注册表: 告诉大模型"你有哪些工具可用、参数长什么样"
# 说明：这里的工具函数都不直接调大模型，只做"执行动作并返回文本结果"，
#      由 llm_core.run_turn 循环调用并把结果喂回模型。
import os
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup

# 通用请求头，模拟浏览器，降低被反爬拦的概率
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


# ---------- 工具1: 联网搜索 ----------
def web_search(query, top_k=5):
    """用百度搜索关键词，返回前top_k条标题。
    注意：百度是免费接口，可能不稳定；若超时可以改更大timeout或换其他源。"""
    url = "https://www.baidu.com/s?wd=" + urllib.parse.quote(query)
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for h3 in soup.find_all("h3")[:top_k]:            # 百度标题在<h3>
        a = h3.find("a")
        if a and a.get("href"):
            out.append(f"- {a.get_text(strip=True)[:80]}")
    return "\n".join(out) if out else "没搜到,换关键词"


# ---------- 工具2: 读网页正文 ----------
def fetch_url(url, max_len=1500):
    """抓取指定网页正文的前max_len字。去掉脚本/样式/导航/页脚等噪音。"""
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):   # 剔除无关标签
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"\n{2,}", "\n", text)                     # 压缩连续空行
    return text[:max_len]


# ---------- 工具3: 查本地知识库(RAG) ----------
def ask_knowledge_base(query, collection, n_results=3):
    """在指定的chroma知识库collection里做语义检索，返回最相关的n块片段。
    collection 由界面在连接库后传入，这里只负责检索。"""
    try:
        res = collection.query(query_texts=[query], n_results=n_results)
        docs = res["documents"][0]
        return "\n".join(docs) if docs else "知识库里没检索到相关内容"
    except Exception as e:
        return f"知识库查询失败: {e}"


# ---------- 工具注册表: 这份清单会被喂给大模型 ----------
# 大模型看到这个清单才知道"我能调用哪些函数、每个函数接收什么参数"
TOOLS = [
    {"type": "function", "function": {
        "name": "ask_knowledge_base",
        "description": "在主人的本地讲义/知识库里语义检索。适合问讲义里讲过的概念、公式、定理等自备资料内容",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string"}},
                       "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "web_search",
        "description": "联网搜索关键词，返回最新/网络上的资料。适合问外部动态、前沿进展",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string"}},
                       "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "fetch_url",
        "description": "读取某个具体网页URL的正文",
        "parameters": {"type": "object",
                       "properties": {"url": {"type": "string"}},
                       "required": ["url"]}}},
]