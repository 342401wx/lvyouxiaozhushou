# 旅游规划小助手

这是一个基于 RAG、向量检索、地图工具和大模型的旅游规划 Demo 小助手。用户可以注册登录账号，用自然语言输入出游需求，系统会识别目的地、出发地、日期、天数、预算、交通方式和兴趣点，并生成包含景点、餐饮、住宿、天气、地图、预算和参考资料的旅游攻略。

当前正式项目目录：

```text
D:\桌面\zuoye\A3.1小助手
```

> 运行命令前一定先 `cd` 到这个目录。之前报 `can't open file ... scripts\serve_tourism_with_railway.py`，就是因为站到了 `A3实战1` 旧目录。

## 主要功能

- 登录/注册：账号和密码校验，多账户记忆隔离。
- 需求识别：优先使用 DeepSeek 识别用户需求，失败时规则兜底。
- RAG 检索：从旅游知识库中召回相关景点、美食、交通、住宿资料。
- 向量库：使用自建 TF-IDF VectorStore，属于“Chroma 或其他向量库”中的其他向量库方案。
- 行程规划：按日期、到达时间、营业时间、交通时间和用餐时间生成每日安排。
- 城际交通：支持高铁/火车候选查询，用户选择往返车次后再生成攻略。
- 地图展示：展示景点、住宿点和路线点位，支持全景地图查看。
- 美食安排：优先从知识库和地图餐饮候选中生成就餐信息。
- 酒店评论：展示住宿关注点、好评差评摘要和评论样例。
- 记忆卡片：保存历史需求和历史攻略，可点击恢复详情。
- 并发优化：后端支持线程池、请求队列、规划并发和 SQLite WAL。

## 数据集来源

本项目主数据集来自中文维基导游 Wikivoyage 的公开旅游资料：

[https://dumps.wikimedia.org/zhwikivoyage/latest/](https://dumps.wikimedia.org/zhwikivoyage/latest/)

项目中使用的数据文件：

```text
zhwikivoyage-latest-pages-articles.xml.bz2
travel+reviews.zip
archive.zip
基于YoloV8的驾驶行为检测系统.pdf
```

已处理后的主要数据：

```text
data/processed/tourism_qa.jsonl        # 旅游 RAG 知识库，约 30323 条
data/vectorstore/tourism_tfidf.pkl     # 旅游 TF-IDF 向量库
data/processed/papers.jsonl            # PDF 论文切片数据
data/vectorstore/papers_tfidf.pkl      # 论文向量库
data/tourism_app.sqlite                # 用户、会话、记忆数据库
```

## 技术栈

后端：

- Python 3.11
- pandas
- requests
- scikit-learn
- sqlite3
- pytest

前端：

- Next.js 13
- React 18
- TypeScript
- Tailwind CSS
- Leaflet / react-leaflet
- Zustand
- lucide-react

可选扩展：

- DeepSeek OpenAI-compatible API
- 高德 Web Service API
- 高德 JS API
- 12306-MCP
- Chroma / LangChain

## 环境变量

在项目根目录创建 `.env`，按需填写：

```text
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

AMAP_API_KEY=
AMAP_JS_KEY=
AMAP_SECURITY_JS_CODE=

REQUEST_TIMEOUT=12

HTTP_MAX_WORKERS=32
HTTP_REQUEST_QUEUE_SIZE=128
PLAN_CONCURRENCY=8
INTENT_CONCURRENCY=12
SQLITE_TIMEOUT=30

RAILWAY_PROVIDER=12306_mcp
RAILWAY_MCP_URL=http://127.0.0.1:8765

SEARCH_PROVIDER=tavily
SEARCH_API_KEY=
```

说明：

- 不填 DeepSeek Key 也能跑，但 AI 识别能力会下降，会更多依赖规则兜底。
- 不填高德 Key 也能跑，但地图、天气、POI 和酒店会使用兜底数据。
- 使用 12306-MCP 时，需要本机能运行 `npx -y 12306-mcp`。

## 安装依赖

进入正式项目目录：

```powershell
cd "D:\桌面\zuoye\A3.1小助手"
```

安装后端依赖：

```powershell
pip install -r requirements.txt
```

如需 Chroma/LangChain 扩展：

```powershell
pip install -r requirements-optional.txt
```

安装前端依赖：

```powershell
npm install
```

## 数据处理与向量库构建

首次运行或数据更新后执行：

```powershell
python -X utf8 scripts\prepare_tourism.py
python -X utf8 scripts\build_tourism_index.py
```

如果要处理论文 PDF：

```powershell
python -X utf8 scripts\prepare_papers.py
python -X utf8 scripts\build_paper_index.py
```

如果要构建可选 Chroma 索引：

```powershell
pip install -r requirements-optional.txt
python -X utf8 scripts\build_chroma_index.py
```

## 启动项目

当前推荐端口：

```text
Next.js 前端：7860
Python 后端：7861
```

这样可以直接适配已经绑定到 `7860` 的 `lv.852sq.cn`。如果只是在本机调试，也可以把前端跑到默认的 `3000`，但对外访问以 `7860` 为准。

### 1. 启动后端

普通后端：

```powershell
cd "D:\桌面\zuoye\A3.1小助手"
python -B scripts\serve_tourism_app.py --port 7861
```

带 12306-MCP 的后端：

```powershell
cd "D:\桌面\zuoye\A3.1小助手"
python -B scripts\serve_tourism_with_railway.py --port 7861
```

### 2. 启动前端

另开一个 PowerShell：

```powershell
cd "D:\桌面\zuoye\A3.1小助手"
npm run dev:7860
```

浏览器打开：

```text
http://localhost:7860/
```

前端会通过 `app/api/[...path]/route.ts` 自动把 `/api/*` 请求代理到：

```text
http://127.0.0.1:7861
```

## 给别人访问

如果通过 Cloudflare Tunnel 或其他内网穿透给朋友访问，把隧道绑定到前端 `7860`：

```text
http://localhost:7860
```

你的 `lv.852sq.cn` 当前就是这个用法：外网域名 -> 本机 `7860` 前端 -> 本机 `7861` 后端 API。

不要只暴露后端 `7861`，因为完整 UI 在 Next.js 前端里。前端会在服务器侧继续代理到本机后端 `7861`。

## 常用测试命令

后端测试：

```powershell
python -m pytest
```

前端类型检查：

```powershell
npm run typecheck -- --pretty false
```

命令行 RAG 检索：

```powershell
python -X utf8 scripts\ask_tourism.py "铜陵有什么美食？" --top-k 3
```

健康检查：

```powershell
curl http://127.0.0.1:7861/api/health
```

## 项目结构

```text
app/                         # Next.js 页面与 API 代理
components/travel/            # 旅游工作台前端组件
lib/                          # 前端 API、数据适配和状态管理
src/education_qa/             # Python 后端核心模块
scripts/                      # 数据处理、向量库构建、启动脚本
data/processed/               # 处理后的 JSONL 知识库
data/vectorstore/             # TF-IDF 向量库文件
data/tourism_app.sqlite       # 用户与记忆数据库
report_assets/                # 技术报告截图素材
旅游规划小助手技术报告.docx   # Word 技术报告
```

## 课程要求对应

| 要求 | 项目实现 | 结论 |
|---|---|---|
| 选择数据集 | 中文 Wikivoyage 旅游资料、酒店评论、论文 PDF、教育问答 Demo | 满足 |
| PDF 转 TXT | `pdf_extract.py`、`papers.py` | 满足 |
| 数据清洗和切片 | 旅游知识和 PDF 论文均处理为 JSONL 文档片段 | 满足 |
| 存入向量库 | `tourism_tfidf.pkl` TF-IDF VectorStore | 满足 |
| Chroma 或其他向量库 | 当前使用自建 TF-IDF 向量库，并保留 Chroma 扩展 | 满足 |
| 问答/检索流程 | 用户输入 -> 意图识别 -> RAG 检索 -> 工具调用 -> 生成攻略 | 满足 |
| LLM + VectorStore + Memory + Chain | DeepSeek、TF-IDF VectorStore、SQLite Memory、Trip Planner Chain | 满足 |
| Demo 小助手 | Next.js 前端 + Python 后端，可本地运行 | 满足 |

## 提交材料

建议提交：

```text
代码文件完整项目目录
旅游规划小助手技术报告.docx
```

如果 Word 打开时出现“代理身份验证错误”，这是 Word 连接微软在线服务时的代理问题，不影响本地文档内容。可以取消弹窗，或关闭系统代理后重启 Word。
