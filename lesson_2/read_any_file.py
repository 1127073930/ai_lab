"""
read_any_file 升级版:按扩展名自动分流读取,支持 txt/md/qmd/csv/html/docx/pdf/xlsx。
特点:1)延迟导入依赖库,用啥装啥不强制 2)docx含表格也读 3)出错不崩返回提示 4)输出统一清理。
"""
import os
from bs4 import BeautifulSoup        # 解析html


# ---------- 核心:根据扩展名分发送到对应读取函数 ----------
def read_any_file(path):
    """
    万能文件读取入口。根据文件扩展名自动选择提取文本的方式,返回规范清理后的纯文本。
    path: 文件绝对或相对路径
    返回: 文件中的纯文本; 不支持的格式或读取失败则返回说明文字
    """
    if not os.path.exists(path):                     # 文件不存在提前拦截
        return f"[文件不存在] {path}"

    ext = os.path.splitext(path)[1].lower()          # 取扩展名(转小写,如".TXT"->".txt")
    try:
        # ---------- 分支1: 纯文本类 ----------
        if ext in [".txt", ".md", ".qmd", ".rmd", ".csv", ".json"]:
            return _read_plain(path)

        # ---------- 分支2: HTML ----------
        elif ext in [".html", ".htm"]:
            return _read_html(path)

        # ---------- 分支3: Word ----------
        elif ext == ".docx":
            return _read_docx(path)

        # ---------- 分支4: PDF ----------
        elif ext == ".pdf":
            return _read_pdf(path)

        # ---------- 分支5: Excel ----------
        elif ext in [".xlsx", ".xls"]:
            return _read_excel(path)

        # ---------- 兜底: 不支持的格式 ----------
        else:
            return f"[暂不支持的格式] {ext}"

    except Exception as e:                           # 任何读取异常都不崩,友好提示
        return f"[读取失败] {path}: {str(e)[:100]}"


# ---------- 各格式读取函数 ----------
def _read_plain(path):
    """读取纯文本文件,utf-8编码(中文不乱码)。"""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _read_html(path):
    """html:去标签、去脚本/样式,只取正文纯文本。"""
    with open(path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()                              # 删掉无关块
    text = soup.get_text("\n")                       # 转纯文本,换行分隔
    return _clean(text, sep=True)


def _read_docx(path):
    """Word:读取正文段落 + 表格单元格文本(python-docx)。"""
    from docx import Document                        # 延迟导入,没装才报错
    doc = Document(path)
    parts = [p.text for p in doc.paragraphs if p.text.strip()]   # 段落
    for table in doc.tables:                         # 表格
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))      # 单元格用竖线连接
    return _clean("\n".join(parts))


def _read_pdf(path):
    """PDF:逐页提取文字(pypdf)。仅文字型PDF,扫描件需OCR。"""
    from pypdf import PdfReader                      # 延迟导入
    reader = PdfReader(path)
    texts = [page.extract_text() or "" for page in reader.pages]
    return _clean("\n".join(texts))


def _read_excel(path):
    """Excel:读每个sheet的所有单元格文本(pandas)。"""
    import pandas as pd                              # 延迟导入
    frames = []
    for sheet in pd.read_excel(path, sheet_name=None, dtype=str).values():
        frames.append(sheet.to_string(index=False))  # 每一sheet转字符串
    return _clean("\n".join(frames))


# ---------- 统一的文本清理 ----------
def _clean(text, sep=False):
    """
    清理文本:压缩多余空行(和可选空格换行)。
    目的是让切块更干净,避免空行干扰检索。
    """
    import re
    text = re.sub(r"\n{2,}", "\n", text)             # 连续2+空行压缩为1
    if sep:
        # html的换行可能带空格,清一下行首尾空格
        text = "\n".join(line.strip() for line in text.splitlines())
    return text.strip()


# ---------- 测试 ----------
if __name__ == "__main__":
    print(read_any_file("my_lecture.txt"))           # 纯文本
    print("----")
    print(read_any_file("不存在的文件.docx"))          # 测试容错
