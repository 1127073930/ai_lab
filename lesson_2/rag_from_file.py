"""
RAG从真实文件读取,相比上节课,只把"资料"来源从字符串改成了文件读取。
"""
import os
import chromadb
from openai import OpenAI
from dotenv import load_dotenv
from read_any_file import read_any_file

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")


# ---------- 切块(与上节课相同) ----------
def split_chunks(text, size=80, overlap=20):
    """
    按"字符数"切块,并带重叠。size每块长度;overlap块间重叠长度(避免切断语义)。
    相比按句号切,这种更适合长文档(如整本讲义)。
    """
    chunks = []
    for i in range(0, len(text), size - overlap):   # 步长=size-overlap,产生重叠
        chunks.append(text[i:i + size])
    return chunks

# ---------- 建库 + 检索 + 生成 ----------
def build_index(file_path):
    """
    从文件读取全文 -> 切块 -> 写入chroma向量库。返回collection。
    """
    text = read_any_file(file_path)               # 读文件
    chunks = split_chunks(text)                    # 切块
    client_cdb = chromadb.PersistentClient(path="./chroma_file_db")
    client_cdb.delete_collection("file_lecture")  
    collection = client_cdb.get_or_create_collection("file_lecture")
    collection.upsert(
        ids=[f"c{i}" for i in range(len(chunks))],
        documents=chunks,
    )
    print(f"已从 {file_path} 读取 {len(chunks)} 块入库。")
    return collection

def ask_about_file(question, collection, top_k=3):
    """检索+生成:RAG问答。"""
    res = collection.query(query_texts=[question], n_results=top_k)
    context = "\n\n".join(res["documents"][0])
    messages = [
        {"role": "system", "content": "你严谨的助手,请严格基于资料回答,资料外不臆造。"},
        {"role": "user", "content": f"【资料】\n{context}\n【问题】{question}"},
    ]
    r = client.chat.completions.create(model="deepseek-chat", messages=messages)
    return r.choices[0].message.content

if __name__ == "__main__":
    col = build_index("我的rag资料\数据配平.qmd")        # 读取示例讲义建库
    q = "什么叫混淆矩阵?"                       # 问题
    print("检索:", col.query(query_texts=[q], n_results=3)["documents"][0])
    print("\n=== 回答 ===")
    print(ask_about_file(q, col))