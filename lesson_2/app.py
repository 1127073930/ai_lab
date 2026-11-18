# app.py —— 把 course_qa_tool 变成网页问答
import streamlit as st
from course_qa_tool import load_folder, ask   # 复用你已写的函数

st.title("📚 课程材料问答助手")

# 侧边栏:选择素材文件夹
with st.sidebar:
    folder = st.text_input("素材文件夹路径:", ".")
    top_k = st.slider("检索条数", 1, 6, 3)
    if st.button("加载素材"):
        st.session_state["collection"] = load_folder(folder)  # 存进session

# 主区:连续问答
if "collection" not in st.session_state:
    st.info("请先在左侧选择素材文件夹并点击'加载素材'")
else:
    q = st.chat_input("输入你的问题...")
    if q:
        ans = ask(q, st.session_state["collection"], top_k)
        st.write("**你：**", q)
        st.write("**助手：**", ans)