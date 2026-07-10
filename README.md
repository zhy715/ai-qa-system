# 律答 AI — 智能法律咨询助手

基于 RAG 架构的 AI 法律智能客服系统。上传法律法规、合同、裁判文书等文件后，用户可通过自然语言提问，系统自动检索相关法律条文并生成专业解答，支持多轮连续对话。

## 应用场景

- **律所知识管理** — 上传内部案例库，律师快速检索历史判例和法律依据
- **企业法务助手** — 导入合同模板与合规文件，员工自助查询法律问题
- **公众法律咨询** — 上传民法典等法律法规，提供 24×7 基础法律问答

## 系统架构

```
用户提问 → 向量语义检索 → Prompt 拼装（文档 + 对话历史）→ DeepSeek 生成回答
```

## 功能特性

- 支持 PDF / DOCX / TXT / Markdown / CSV / HTML 六种格式上传
- 中文语义检索（多语言 MiniLM 嵌入模型，Recall@5 达 100%）
- 多轮对话记忆，理解代词指代与追问意图
- 法律专业 Prompt 模板：法条引用 + 三段式回答结构
- 文档原文查看（右侧可拖拽面板）

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python / FastAPI |
| 大模型 | DeepSeek API（兼容 OpenAI SDK） |
| RAG 框架 | LangChain |
| 向量数据库 | ChromaDB（本地部署） |
| 嵌入模型 | paraphrase-multilingual-MiniLM-L12-v2 |
| 前端 | React / Vite |
| 设计系统 | Impeccable |

## 快速启动

```bash
# 1. 配置 API Key
cp .env.example .env
# 编辑 .env，填入 DeepSeek API Key

# 2. 安装依赖
python -m venv venv
source venv/Scripts/activate  # Windows
pip install -r requirements.txt

# 3. 启动后端
python run_server.py

# 4. 启动前端（新终端）
cd frontend && npm install && npx vite --port 5173
```

访问 `http://localhost:5173`

## 项目结构

```
.
├── app/
│   ├── main.py                    # FastAPI 入口，11 个 REST 接口
│   ├── models/schemas.py          # 数据模型
│   └── services/
│       ├── document_service.py    # 多格式文档解析 + 文本分块
│       ├── vector_service.py      # ChromaDB 向量存储与检索
│       ├── llm_service.py         # DeepSeek LLM + 法律 Prompt
│       └── conversation_service.py # 多轮对话管理
├── frontend/                      # React 前端
│   └── src/
│       ├── api/index.js           # API 调用封装
│       └── components/
│           ├── Sidebar.jsx        # 侧边栏（上传 / 对话列表 / 文档列表）
│           ├── ChatArea.jsx       # 聊天区
│           ├── ChatMessage.jsx    # 消息气泡
│           └── DocumentViewer.jsx # 文档查看器（可拖拽宽度）
├── eval_retrieval.py              # 检索评估脚本（Recall@K / MRR 网格搜索）
├── run_server.py                  # 后端启动脚本
└── .env                           # API Key 配置（不入库）
```
