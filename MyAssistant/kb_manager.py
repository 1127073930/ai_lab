# kb_manager.py — 第①部分：建立知识库 + 连接知识库
# 职责：负责"数据"层面 —— 从文件夹读文件→切块→embedding→写入chroma向量库；以及后续连接库。
#      界面(app.py)只负责让用户选文件夹路径，真正的建库/连库逻辑都封装在这里。
import os
import re
import chromadb

# ========== 支持的文档扩展名（想加格式，在这里再加一行即可） ==========
SUPPORTED_EXTS = {".txt", ".md", ".qmd", ".rmd", ".csv", ".html", ".docx", ".pdf", ".xlsx"}


# ---------- 工具: 按扩展名读取文件文本 ----------
def read_any_file(file_path):
    """根据文件后缀用对应方式读出纯文本。延迟导入对应库，避免装一大堆依赖。
    返回: 文件内全部文字(字符串)；失败则返回空字符串。"""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext in (".txt", ".md", ".qmd", ".rmd", ".csv"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == ".html":
            from bs4 import BeautifulSoup
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f.read(), "html.parser")
                for t in soup(["script", "style", "nav", "footer"]):
                    t.decompose()
                return soup.get_text("\n")
        elif ext == ".docx":
            import docx
            d = docx.Document(file_path)
            parts = [p.text for p in d.paragraphs]
            for tb in d.tables:                      # 也读表格里的文字
                for row in tb.rows:
                    parts.append(" | ".join(c.text for c in row.cells))
            return "\n".join(parts)
        elif ext == ".pdf":
            from pypdf import PdfReader
            return "\n".join(p.extract_text() or "" for p in PdfReader(file_path).pages)
        elif ext == ".xlsx":
            import pandas as pd
            return "\n".join(df.to_string() for df in pd.read_excel(file_path, sheet_name=None).values())
    except Exception:
        return ""   # 单个文件失败不影响整批，跳过
    return ""


# ---------- 工具: 按"句子"切块(尊重语义边界) ----------
def split_chunks(text, target_size=200):
    """把长文本切成若干块。用正则按中文句号/问号/感叹号/分号/换行切，再合并到目标长度。
    关键：按句子切(而不是硬按字符数切)，避免切断一句话导致语义断裂(你之前踩过这个坑)。"""
    sentences = re.split(r"(?<=[。！？；\n])", text)   # "lookbehind"在标点后切开
    sentences = [s.strip() for s in sentences if s.strip()]
    chunks, cur = [], ""
    for s in sentences:                               # 逐个句子累积到 cur
        if len(cur) + len(s) <= target_size:          # 没超目标长度→继续累加
            cur += s
        else:                                         # 超了→把当前块存下，另起新块
            if cur:
                chunks.append(cur)
            cur = s
    if cur:
        chunks.append(cur)
    return chunks


# ---------- 核心: 从文件夹建库(清空旧库再重建) ----------
def build_kb_from_folder(folder_path, db_path="./course_db", coll_name="course"):
    """遍历文件夹里所有支持格式的文件，切块后写入chroma向量库。
    每次调用都会【清空】旧知识库再重建，确保和选中的文件夹一致。
    返回: 装了多少块(chunk数)，供界面提示。"""
    # 1) 连接(或创建)数据库client
    client_cdb = chromadb.PersistentClient(path=db_path)
    # 2) 清空旧库: 直接删除整个collection再重建，最干净(避免 delete(where={}) 那个坑)
    try:
        client_cdb.delete_collection(coll_name)
    except Exception:
        pass   # 若库不存在，delete会报错，忽略即可
    collection = client_cdb.get_or_create_collection(coll_name)

    # 3) 遍历文件夹，每个文件读出文本→切块→入库
    total = 0
    if os.path.isdir(folder_path):
        for fname in os.listdir(folder_path):
            fpath = os.path.join(folder_path, fname)
            if not os.path.isfile(fpath):
                continue
            if os.path.splitext(fname)[1].lower() not in SUPPORTED_EXTS:
                continue                             # 跳过不支持的格式
            text = read_any_file(fpath)
            if not text.strip():
                continue
            chunks = split_chunks(text)
            if not chunks:
                continue
            # ids用"文件名_序号"保证唯一; metadatas记录来源文件名(便于溯源)
            collection.add(
                ids=[f"{fname}_{i}" for i in range(len(chunks))],
                documents=chunks,
                metadatas=[{"source": fname}] * len(chunks),
            )
            total += len(chunks)
    return total


# ---------- 连接库(读，不重建) ----------
def get_collection(db_path="./course_db", coll_name="course"):
    """连接已有的chroma知识库。建库用上面的 build_kb_from_folder，这里只连不建。
    返回: collection 对象(供检索用)。"""
    client_cdb = chromadb.PersistentClient(path=db_path)
    return client_cdb.get_or_create_collection(coll_name)


# ---------- 独立测试(直接运行本文件可单独测建库) ----------
if __name__ == "__main__":
    n = build_kb_from_folder(input("文件夹路径:"))
    print(f"已导入 {n} 块到 course_db/course")