"""
RAG(检索增强生成)入门：用 Chroma 向量库 + DeepSeek，做"讲义问答"。
流程：建知识库(写入) -> 检索(查TopK) -> 生成(喂回模型回答)。
"""
import os
import chromadb                           # 向量数据库
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

# ---------- Step 0: 准备"资料" ----------
# 用一段讲义片段做演示。真实使用时，把文件读进来再切成chunk。
lecture = """
回归分析是研究变量之间相关关系的一种统计方法。
它通过建立数学模型,描述一个因变量与一个或多个自变量之间的关系。
线性回归是最基础的形式,假设因变量与自变量呈线性关系。
在使用线性回归时,需要注意多重共线性、异常值、残差的正态性等假设检验。
回归模型的优劣常用 R 方、调整R方、显著性检验等指标评估。
"""

# ---------- 切块工具函数 ----------
def split_chunks(text, sep="。"):
    """
    把文本按句号切成若干独立片段(chunk),去掉空段。
    切块是RAG第一步:文档必须切小块,才能精确检索到局部内容。
    text:原始讲义文本; sep:分隔符(默认中文句号)
    返回:片段字符串列表
    """
    chunks = [c.strip() for c in text.split(sep) if c.strip()]
    return chunks

chunks = split_chunks(lecture)
print("切分后的片段:", chunks)

# ---------- Step 1: 建知识库(入库) ----------
# Chroma 用内置embedding模型把每个片段转成向量并存盘
client_cdb = chromadb.PersistentClient(path="./chroma_db")      # 指定持久化目录,数据存在本地
collection = client_cdb.get_or_create_collection("lecture_db")  # 获取或创建集合(相当于"库")

# 把每个片段写入:ids唯一编号 / documents原文 / metadatas可附来源
collection.upsert(
    ids=[f"chunk_{i}" for i in range(len(chunks))],
    documents=chunks,
    metadatas=[{"source": "regression_lecture"} for _ in chunks],
)
print(f"已入库 {len(chunks)} 个片段。")

# ---------- Step 2: 检索(把问题变向量,找最相关片段) ----------
def retrieve(question, top_k=2):
    """
    把用户问题embedding成向量,在向量库查语义最相关的top_k块。
    注意:这里是"语义相似度"(向量距离)而非字面匹配,所以措辞不同也能找到。
    question:用户问题; top_k:返回块数
    返回:命中的片段原文列表
    """
    result = collection.query(query_texts=[question], n_results=top_k)
    return result["documents"][0]          # documents[0]是本次查询命中的片段

# ---------- Step 3: 生成(把检索结果喂回模型) ----------
def ask_with_rag(question):
    """
    核心:RAG问答。检索相关片段 -> 拼进上下文 -> 让模型基于资料回答。
    question:用户提问
    返回:模型基于检索资料给出的回答
    """
    hits = retrieve(question)                    # 步骤②检索
    context = "\n\n".join(hits)                  # 把命中片段拼成上下文
    messages = [
        {"role": "system", "content": "你是严谨的统计课助教。请严格基于提供的资料回答,资料中没有的不臆造。"},
        {"role": "user", "content": f"参考以下资料回答问题。\n\n【资料】\n{context}\n\n【问题】{question}"},
    ]
    resp = client.chat.completions.create(model="deepseek-chat", messages=messages)
    return resp.choices[0].message.content

if __name__ == "__main__":
    # 故意用"意思相关但字面不同"的问题,验证语义检索
    q = "线性回归模型的假设条件有哪些？"
    print("检索到的片段:\n", retrieve(q))
    print("\n=== RAG最终回答 ===")
    print(ask_with_rag(q))