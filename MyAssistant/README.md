# 全能科研助手 · 网页版（模块化版）

一套模块化的全能科研助手：从文件夹建知识库 + 联网搜索 + 读网页 + 多轮对话记忆，全部打包成网页应用。

## 四、文件结构（各司其职、单向依赖）
```
全能助手网页版/
├── kb_manager.py   建库/连库：从文件夹读文件→切块→embedding→写入chroma；连接库
├── tools.py        定义工具：web_search / fetch_url / ask_knowledge_base + 工具注册表TOOLS
├── llm_core.py     调用大模型：自主多步循环 run_turn（Agent的"大脑"）
├── app.py          Streamlit网页界面：选文件夹建库、多轮对话、新建/导出
└── README.md       本文件
```
依赖方向：app.py → llm_core.py → tools.py；app.py 还需要 kb_manager 建好库后把 collection 传给 run_turn。

## 五、运行
```powershell
cd 到你放这些文件的目录
& C:/Users/cht08/ai_lab/rag_env/Scripts/python.exe -m streamlit run app.py
```
浏览器自动打开页面：
- 侧边栏填一个文件夹路径 → 点"建库"（会清空旧库、重建）
- 或点"连接默认库"用已有 course_db/course
- 主区像 ChatGPT 一样多轮对话，模型自动决定查资料/联网/读网页

## 六、如何把界面分享给别人使用（三种方式，由易到难）

### 方式一：局域网内别人直接用（最快，适合同事/同实验室，装好 python 即可）
在你自己电脑上启动时指定监听地址和端口，别人手机/电脑连你同一个 Wi-Fi 就能访问：
```powershell
& C:/Users/cht08/ai_lab/rag_env/Scripts/python.exe -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```
然后查看你电脑的局域网IP（`ipconfig` 里的 IPv4），把
`http://你的局域网IP:8501` 发给别人即可。
注意：需要开着这台电脑、同一网络；别人浏览器的访问才加载的是你的AI。

### 方式二：部署到免费公网（Streamlit Community Cloud）——可长期在线
1. 把全套代码（app.py + kb_manager.py + tools.py + llm_core.py）上传到一个 GitHub 仓库
2. 去 https://share.streamlit.io 或 https://streamlit.io/cloud 用 GitHub 账号登录
3. "New app" → 选你的仓库和 app.py → Deploy
4. Streamlit 会生成一个公开网址，发给任何人即可访问。
   （需要墙外网络可用；历史/导出等功能也能用，但数据库路径需改到云端可写位置。）

### 方式三：本地打包类型 / 自行部署到你的服务器(VPS)
如果你有服务器(阿里云/腾讯云等)，把代码放上去，用 nginx + uvirt 反向代理，
即可做一个真正稳定的对外服务。需要Linux/运维知识，适合你不急时再折腾。

## 七、常见问题
- 建库后答不出/找不对：确认文件夹里有支持的格式(txt/md/qmd/rmd/csv/html/docx/pdf/xlsx)，
  且介质是文字型PDF(扫描件需OCR)。
- 联网超时：百度/Bing免费接口可能不稳，可试加大timeout或换取授权搜索API。
- 想给"知识库连接阶段"定不同库：可在app侧边栏再加一个"集合名"输入框(类似course_db)。