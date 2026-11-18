"""
全能科研助手 · 网页版 (Streamlit)
整合: RAG知识库 + 联网搜索 + 读网页 + 对话记忆 + 多知识库切换 + 导出对话
启动: streamlit run assistant_app.py
原理: 仍是"模型自主多步循环+历史塞messages",只是换成网页交互+session_state存历史
"""
import os, json, re, urllib.parse
import requests
from bs4 import BeautifulSoup
import chromadb
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# ------------------ 三个工具(同前几课,原样保留) ------------------
def web_search(query):
    """百度搜索:返回几条标题。"""
    url = "https://www.baidu.com/s?wd=" + urllib.parse.quote(query)
    r = requests.get(url, headers=HEADERS, timeout=15); r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")
    out = [f"- {h3.find('a').get_text(strip=True)[:80]}" for h3 in soup.find_all("h3")[:5] if h3.find("a")]
    return "\n".join(out) if out else "没搜到,换关键词"

def fetch_url(url):
    """抓网页正文(前1500字)。"""
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    for t in soup(["script","style","nav","footer"]): t.decompose()
    return re.sub(r"\n{2,}","\n",soup.get_text("\n"))[:1500]

def ask_knowledge_base(query, collection):
    """在指定知识库里语义检索,返回最相关片段。"""
    try:
        res = collection.query(query_texts=[query], n_results=3)
        docs = res["documents"][0]
        return "\n".join(docs) if docs else "知识库没检索到相关内容"
    except Exception as e:
        return f"知识库查询失败: {e}"

# ------------------ 工具注册表(同前,ask_knowledge_base参数里不带collection,运行时用当前库) ------------------
TOOLS = [
    {"type": "function", "function": {"name": "ask_knowledge_base",
        "description": "在本地讲义/知识库里检索,适合问资料里的概念",
        "parameters": {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type": "function", "function": {"name": "web_search",
        "description": "联网搜索关键词,返回最新资料",
        "parameters": {"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
    {"type": "function", "function": {"name": "fetch_url",
        "description": "读取某个网页的正文",
        "parameters": {"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}},
]

# ------------------ 连接知识库(支持路径/集合名参数) ------------------
@st.cache_resource            # 缓存:相同参数只连接一次,避免每次交互重连
def load_collection(db_path, coll_name):
    """连接chroma知识库,返回collection。Streamlit每次交互会重跑脚本,cache避免重复建连。"""
    c = chromadb.PersistentClient(path=db_path)
    return c.get_or_create_collection(coll_name)

# ------------------ 调模型跑一整个自主循环(和chat()逻辑一样,可复用) ------------------
def run_turn(messages, collection):
    """
    执行模型的自主多步循环,返回(最终回答, 这轮的工具调用记录列表)
    messages: 累积的历史(含system+以前对话+当前问题)
    collection: 当前选中的知识库
    """
    step = 0
    used_tools = []                       # 记录本轮调用了哪些工具(用于界面展示)
    while step < 12:
        resp = client.chat.completions.create(model="deepseek-chat", messages=messages, tools=TOOLS)
        msg = resp.choices[0].message
        messages.append(msg)
        if not getattr(msg, "tool_calls", None):   # 信息够了,返回最终答案
            return msg.content, used_tools
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            if tc.function.name == "ask_knowledge_base":
                result = ask_knowledge_base(args["query"], collection)
            elif tc.function.name == "web_search":
                result = web_search(args["query"])
            else:
                result = fetch_url(args["url"])
            used_tools.append(f"{tc.function.name}: {args}")   # 记下供展示
            messages.append({"role":"tool","tool_call_id":tc.id,"content":str(result)})
        step += 1
    return "步数用尽,请简化问题。", used_tools

# ========================= 网页界面 =========================
st.set_page_config(page_title="全能科研助手", page_icon="🎓")
st.title("🎓 全能科研助手")

# ---- 侧边栏: 配置知识库 + 新建/导出对话 ----
with st.sidebar:
    st.header("⚙️ 配置")
    db_path = st.text_input("知识库路径(db_path)", value="./course_db")
    coll_name = st.text_input("集合名(coll)", value="course")

    # session_state: Streamlit跨交互暂存数据的关键机制
    # 页面每次操作都会"重新跑整个脚本",普通变量会被重置;存进session_state才能保留
    if "history" not in st.session_state:
        st.session_state.history = []              # 短期记忆:整个对话历史
    if "collection" not in st.session_state:
        st.session_state.collection = None         # 当前知识库

    if st.button("🔄 连接/切换知识库"):
        st.session_state.collection = load_collection(db_path, coll_name)
        st.success("已连接知识库")

    if st.button("🗑️ 新建对话"):
        st.session_state.history = []              # 清空历史=失忆,开启新对话
        st.rerun()

    if st.session_state.history:
        # 导出对话:把历史写成一个txt提供下载
        content = "\n\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in st.session_state.history)
        st.download_button("⬇️ 导出对话", data=content.encode("utf-8"),
                           file_name="对话记录.txt", mime="text/plain")

# ---- 主区: 展示已有对话 ----
for m in st.session_state.history:
    if m["role"] == "user":
        st.chat_message("user").write(m["content"])
    elif m["role"] == "assistant":
        st.chat_message("assistant").write(m["content"])

# ---- 输入框: 提问并触发回答 ----
if prompt := st.chat_input("问问助手(可问资料/联网/读网页)..."):
    if st.session_state.collection is None:
        # 未连接知识库也能用联网/读网页,但先提示
        st.session_state.collection = load_collection(db_path, coll_name)  # 自动连默认库

    st.chat_message("user").write(prompt)
    st.session_state.history.append({"role": "user", "content": prompt})

    # 组装含历史的消息(和chat()相同)
    messages = ([{"role":"system","content":"你是全能科研助手,可查本地讲义、联网、读网页,请记得我们前面的对话。"}]
                + st.session_state.history[-20:])

    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            answer, used = run_turn(messages, st.session_state.collection)
        st.write(answer)
        if used:
            st.caption("🔧 用到的工具: " + "; ".join(used))

    # 把本轮回答追加进历史(供下一次对话记住)
    st.session_state.history.append({"role": "assistant", "content": answer})
