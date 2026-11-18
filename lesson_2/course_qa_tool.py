"""
完整工具:课程材料问答助手
用法:把讲义/论文路径传给工具,它会自动读取->切块->入库,然后支持连续问答。
整合了三样能力:read_any_file(多格式读取) + RAG(检索生成) + 多轮口语化输入。
"""
import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv
import re

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

# ==== 1. 文件读取(可复用你已写的 read_any_file) ====
def read_any_file(path):
    """多格式文件读取:txt/md/qmd/csv/html/docx/pdf/xlsx 自动分流。"""
    if not os.path.exists(path):
        return f"[文件不存在] {path}"
    ext = os.path.splitext(path)[1].lower()
    if ext in [".txt", ".md", ".qmd", ".rmd", ".csv", ".json"]:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    elif ext in [".html", ".htm"]:
        from bs4 import BeautifulSoup
        with open(path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text("\n")
    elif ext == ".docx":
        from docx import Document
        doc = Document(path)
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells]
                if any(cells):
                    parts.append(" | ".join(cells))
        return "\n".join(parts)
    elif ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(path)
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    else:
        return f"[暂不支持] {ext}"


# ==== 2. 切块 ====
def split_chunks(text, target_size=200):
    """
    改进版切块:先按句子切,再合并成接近target_size的块,保证每块是完整语义。
    中文以句号、问号、叹号、段落结尾为断句点。
    相比"固定字符数硬切",这样不会把一句话拦腰切断,检索更准。
    text: 全文; target_size: 每块目标字符数
    """
    # 1. 先把文本切成"句子列表"(按标点断句,保留标点)
    sentences = re.split(r'(?<=[。！？；\n])', text)     # 在标点后切断
    sentences = [s.strip() for s in sentences if s.strip()]

    # 2. 把相邻句子拼成块,直到接近target_size
    chunks, cur = [], ""
    for s in sentences:
        if len(cur) + len(s) <= target_size:   # 未超目标,继续拼接
            cur += s
        else:                                  # 超了,先存现有块,开新块
            if cur:
                chunks.append(cur)
            cur = s
    if cur:                                    # 收尾存最后一块
        chunks.append(cur)
    return chunks


# ==== 3. 建立索引(把文件入库) ====

SUPPORTED = [".txt", ".md", ".qmd", ".rmd", ".csv", ".html", ".docx", ".pdf", ".xlsx"]

def load_folder(folder_path, db_path="./course_db", coll="course"):
    """
    读取整个文件夹里的所有支持文档,统一并入同一个向量库collection。
    folder_path: 文件夹路径; db_path/coll: 向量库存放位置与集合名
    返回: collection(知识库)
    """
    client_cdb = chromadb.PersistentClient(path=db_path)
    collection = client_cdb.get_or_create_collection(coll)

    # 遍历文件夹(含子目录更好,这里先只取当前层,可扩展)
    files = [f for f in os.listdir(folder_path)
             if os.path.splitext(f)[1].lower() in SUPPORTED]

    if not files:
        print("该文件夹下没有支持的文档格式")
        return collection

    total = 0
    for fname in files:
        full = os.path.join(folder_path, fname)
        text = read_any_file(full)                 # 复用多格式读取
        if text.startswith("["):                   # 读取失败则跳过
            print(f"跳过 {fname}: {text}")
            continue
        chunks = split_chunks(text)                # 应用改进版按句切块
        # ids用"文件名+序号",保证跨文件不冲突; metadatas记录来源文件
        collection.upsert(
            ids=[f"{fname}_{i}" for i in range(len(chunks))],
            documents=chunks,
            metadatas=[{"source": fname} for _ in chunks],
        )
        print(f"✅ 已入库 {fname} ({len(chunks)} 块)")
        total += len(chunks)

    print(f"\n本次共入库 {len(files)} 个文件, {total} 块。")
    return collection



# ==== 4. 对话问答(检索+生成) ====
def ask(question, collection, top_k=3):
    """
    基于已加载的资料回答。检索最相关的top_k块,拼进上下文。
    question: 用户问题; collection: 知识库; top_k: 检索块数
    """
    if collection is None:
        return "请先加载文档 (调用 load_document)。"
    res = collection.query(query_texts=[question], n_results=top_k)
    docs = res["documents"][0]
    context = "\n\n".join(docs)
    messages = [
        {"role": "system",
         "content": "你严谨的课程助教。请严格基于资料回答,资料没提到就说明'资料中未涉及',不要臆造。"},
        {"role": "user",
         "content": f"【资料】\n{context}\n\n【问题】\n{question}"},
    ]
    r = client.chat.completions.create(model="deepseek-chat", messages=messages)
    return r.choices[0].message.content


# ==== 5. 交互主程序 ====
def main():
    """交互式入口:加载文档后,持续让用户在命令行提问。"""
    print("=== 课程材料问答助手 ===")
    path = input("请输入讲义文件夹路径:").strip()
    collection = load_folder(path)
    print("素材已就绪,输入问题开始提问,输入 'exit' 退出\n")
    while True:
        q = input("你: ").strip()
        if q.lower() in ("exit", "quit", "退出"):   # 退出命令
            break
        if not q:
            continue
        print("\n助手:", ask(q, collection), "\n")


if __name__ == "__main__":
    main()
