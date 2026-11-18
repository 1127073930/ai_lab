# app.py — 第④部分：网页界面 (Streamlit)
# 职责：负责用户交互。侧边栏选文件夹建库/连库/新建/导出；主区像ChatGPT一样多轮对话。
#      只负责界面层，具体建库连库调 kb_manager，工具调用+思考走 llm_core。
# 启动：streamlit run app.py   (需在装了 rag_env 的目录，用 rag_env 的 python -m streamlit)
import os
import streamlit as st

import kb_manager   # 建库/连库
import llm_core     # 调模型

# ================= 页面标题 =================
st.set_page_config(page_title="全能科研助手", page_icon="🎓")
st.title("🎓 全能科研助手 (模块化版)")

# ============ session_state: Streamlit 跨交互暂存数据的机制 ============
# 每次你在页面上点按钮/输入，整个脚本都会"重新从顶部跑一遍"，
# 普通变量会被重置。存进 st.session_state 的数据才能跨操作保留。
if "history" not in st.session_state:
    st.session_state.history = []   # 短期记忆: 整场对话历史
if "collection" not in st.session_state:
    st.session_state.collection = None   # 当前已连接的知识库对象
if "kb_info" not in st.session_state:
    st.session_state.kb_info = None      # 知识库说明文本(哪个文件夹/多少块)

# ================= 侧边栏 =================
with st.sidebar:
    st.header("⚙️ 知识库")
    # ① 用户选择文件夹(输入路径)。Streamlit没有原生文件夹选择器，用文本输入最稳妥。
    folder_path = st.text_input("📁 建库文件夹路径(完整路径)", value="./my_docs")

    # ② 点击按钮 -> 从文件夹建库(清空旧库再重建)
    if st.button("🛠️ 用该文件夹建库"):
        if not os.path.isdir(folder_path):
            st.error("该路径不是有效文件夹")
        else:
            with st.spinner("正在建库..."):
                n = kb_manager.build_kb_from_folder(folder_path)   # 建库并清空旧库
                st.session_state.collection = kb_manager.get_collection()  # 建完再连上
                st.session_state.kb_info = f"已从 [{folder_path}] 导入 {n} 块知识点"
            st.success(st.session_state.kb_info)

    # ③ 连接已有默认库(不重建)
    if st.button("🔗 连接默认库"):
        st.session_state.collection = kb_manager.get_collection()
        st.session_state.kb_info = "已连接默认知识库 (course_db/course)"
        st.success(st.session_state.kb_info)

    if st.session_state.kb_info:
        st.caption(st.session_state.kb_info)

    st.divider()
    # ④ 新建对话 = 清空历史(让助手"忘掉"这场对话，重新开始)
    if st.button("🗑️ 新建对话"):
        st.session_state.history = []
        st.rerun()

    # ⑤ 导出对话记录为一个txt文件供下载
    if st.session_state.history:
        content = "\n\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in st.session_state.history)
        st.download_button("⬇️ 导出对话", data=content.encode("utf-8"),
                           file_name="对话记录.txt", mime="text/plain")

    st.divider()
    st.caption("提示：若还没建库，可先联网提问；知识库仅影响 ask_knowledge_base 工具。")

# ================= 主区：展示已有对话 =================
for m in st.session_state.history:
    if m["role"] == "user":
        st.chat_message("user").write(m["content"])
    elif m["role"] == "assistant":
        st.chat_message("assistant").write(m["content"])

# ================= 输入框：提问 =================
if prompt := st.chat_input("问问助手(资料/联网/读网页)..."):
    # 若还没连库，自动连默认库(即使没建过也不影响联网提问)
    if st.session_state.collection is None:
        st.session_state.collection = kb_manager.get_collection()

    # 显示用户问题 + 存进历史
    st.chat_message("user").write(prompt)
    st.session_state.history.append({"role": "user", "content": prompt})

    # 组装含全部历史的消息(短期记忆=把前文塞回给模型)，只保留最近20条防超长
    messages = ([{"role": "system", "content": llm_core.SYSTEM_PROMPT}]
                + st.session_state.history[-20:])

    # 调用模块化大脑: run_turn 返回(答案, 用到的工具)
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            answer, used = llm_core.run_turn(messages, st.session_state.collection)
        st.write(answer)
        if used:
            st.caption("🔧 用到的工具: " + "; ".join(used))

    # 把本轮回答也存进历史，供下一轮"记住"
    st.session_state.history.append({"role": "assistant", "content": answer})