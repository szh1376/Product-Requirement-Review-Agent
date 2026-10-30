# SpecPilot · 产品需求评审智能体

基于 FastAPI 和 DeepSeek 的 PRD 评审工具。从产品、技术、测试三个视角并发检查需求，输出风险等级、原文依据、问题原因和修改建议。

## 功能

- 粘贴需求文本或上传 `.txt`、`.md`、文本型 `.pdf`、`.docx` 文件。
- 三角色并发评审，每个角色最多返回 5 条问题。
- 按高、中、低风险展示结果。
- 使用 SQLite 保存历史评审，支持查看、删除及导出 Markdown 报告。
- 前端由后端直接提供，无需 Node.js 或额外的前端构建步骤。

## 快速开始

需要 Python 3.10 或更高版本，以及可用的 DeepSeek API Key。以下命令在项目根目录执行。

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example backend\.env
```

编辑 `backend/.env`，填写自己的 `DEEPSEEK_API_KEY`，然后启动：

```powershell
.\scripts\start.ps1
```

也可以直接运行：

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# Edit backend/.env and set DEEPSEEK_API_KEY.
cd backend
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

打开 <http://127.0.0.1:8000> 使用网页；交互式 API 文档位于 <http://127.0.0.1:8000/docs>。

## 配置

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥，执行 AI 评审时必填 | 无 |
| `DEEPSEEK_BASE_URL` | API 服务地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 评审模型 | `deepseek-chat` |

配置从 `backend/.env` 加载，已有系统环境变量优先。仓库仅包含空密钥配置示例。

## 项目结构

```text
specpilot/
├── backend/
│   ├── app/
│   │   ├── main.py               # API、静态页面和报告导出
│   │   ├── deepseek_reviewer.py  # DeepSeek 三角色评审
│   │   ├── document_parser.py    # 上传文档解析
│   │   ├── schemas.py            # 请求和响应模型
│   │   ├── storage.py            # SQLite 持久化
│   │   └── reviewer.py           # 保留的规则评审器，当前 API 未使用
│   ├── .env.example
│   └── requirements.txt
├── frontend/                    # 原生 HTML、CSS、JavaScript
├── examples/sample-prd.md        # 可上传的虚构示例需求
├── scripts/start.ps1            # Windows 本地开发启动脚本
└── data/                        # 首次运行自动创建，不纳入版本控制
```

## API

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/health` | 服务健康检查 |
| `POST` | `/api/reviews` | 提交 JSON：`title` 和 `document` |
| `POST` | `/api/reviews/upload` | 上传文件，表单字段为 `file`，可选 `title` |
| `GET` | `/api/reviews` | 查询历史列表 |
| `GET` | `/api/reviews/{review_id}` | 查询完整报告 |
| `GET` | `/api/reviews/{review_id}/export` | 下载 Markdown 报告 |
| `DELETE` | `/api/reviews/{review_id}` | 删除历史报告 |

文本提交要求标题 2–120 个字符、正文 30–30,000 个字符。上传文件最大 8 MB，解析后的文本至少 30 个字符，超过 30,000 个字符会被截断。扫描件 PDF 暂不支持 OCR。

## 数据与使用说明

需求正文会发送到配置的 DeepSeek API 进行评审；每次评审会为三个角色分别发起请求。请先确认文档适合交给该 API 处理。

上传文件在内存中解析，不保存原始文件；评审结果及其原文摘录保存在本地 `data/specpilot.db`。`.env`、虚拟环境、数据库和编辑器配置均已加入忽略规则。

当前版本面向本地使用，尚未实现用户认证和用户间数据隔离。开发启动命令只监听本机地址。

若提示未配置密钥，请检查 `backend/.env` 并重启服务。若 API 返回 502，请检查网络、密钥、模型和账户额度。AI 结果需人工复核。
