from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_DIR / "frontend"
load_dotenv(PROJECT_DIR / "backend" / ".env")

from .deepseek_reviewer import run_deepseek_review
from .document_parser import extract_document
from .schemas import ReviewListItem, ReviewRequest, ReviewResponse
from .storage import ReviewStore


store = ReviewStore(PROJECT_DIR / "data" / "specpilot.db") #存储层初始化

app = FastAPI(title="SpecPilot API", version="0.2.0") #实例化FastAPI
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:8000"], allow_methods=["*"], allow_headers=["*"])

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
#前端写好的网页文件（HTML、CSS、图标、JS脚本）放在了 FRONTEND_DIR 这个文件夹里。让后端当网页服务器

def build_review(title: str, document: str, source_name: str | None = None) -> ReviewResponse:
    #返回一个符合 ReviewResponse 模型的完整对象，该对象会被 FastAPI 自动序列化为 JSON 返回给前端。
    findings = run_deepseek_review(document)
    counts = Counter(item.severity for item in findings)
    # 组装 Pydantic 响应对象（标准化输出）
    review = ReviewResponse(
        id=str(uuid4()), title=title, source_name=source_name, created_at=datetime.now(timezone.utc),
        summary="已从产品、技术、测试三个视角完成首轮评审。",
        findings=findings, counts={level: counts.get(level, 0) for level in ("high", "medium", "low")},
    )
    store.save(review)
    return review

"""
把数据库里的JSON 数据，变成层次分明的评审报告。
"""
def as_markdown(review: ReviewResponse) -> str:
    sections = [f"# {review.title} · SpecPilot 评审报告", "", review.summary, "", "## 风险概览", ""]
    sections.append(f"- 高风险：{review.counts['high']}\n- 中风险：{review.counts['medium']}\n- 低风险：{review.counts['low']}")
    for finding in review.findings:
        sections.extend(["", f"## [{finding.severity.upper()}] {finding.title}", f"- 评审角色：{finding.reviewer}", f"- 原文依据：{finding.evidence}", f"- 问题原因：{finding.reason}", f"- 修改建议：{finding.recommendation}"])
    return "\n".join(sections) + "\n"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/reviews", response_model=ReviewResponse)
def create_review(payload: ReviewRequest) -> ReviewResponse:
    return build_review(payload.title, payload.document)
#只负责接收请求、Pydantic校验、其他由底层函数完成，最后把成品返回前端。


#extract_document 把文档里面的正文提取成一个纯字符串，存到 document 变量里。
@app.post("/api/reviews/upload", response_model=ReviewResponse)
async def create_upload_review(file: UploadFile = File(...), title: str | None = Form(default=None)) -> ReviewResponse:
    file_name = file.filename or "未命名文档"
    document = extract_document(file_name, await file.read())
    return build_review(title or Path(file_name).stem, document, source_name=file_name)
"""
把纯文本，给build_review
同时，他把原始文件名也一并传给流水线，方便记录这是从哪个文件评出来的。
"""
@app.get("/api/reviews", response_model=list[ReviewListItem])
def list_reviews() -> list[ReviewListItem]:
    return store.list()
#陈列窗口。不触发AI,不返回完整报告，展示精简列表。

@app.get("/api/reviews/{review_id}", response_model=ReviewResponse)
def get_review(review_id: str) -> ReviewResponse:
    review = store.get(review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="评审记录不存在。")
    return review
#凭review_id展示完整的原始评审报告原件。

@app.get("/api/reviews/{review_id}/export")
def export_review(review_id: str) -> Response:
    review = get_review(review_id)
    file_name = f"{review.title}-评审报告.md".replace('"', "")
    return Response(as_markdown(review), media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(file_name)}"})
"""
 “下载按钮” 的后端逻辑。它把数据库里的结构化报告，翻译成 Markdown 格式，然后利用 HTTP 响应头强制触发浏览器的下载功能，
"""

@app.delete("/api/reviews/{review_id}", status_code=204)
def delete_review(review_id: str) -> Response:
    if not store.delete(review_id):
        raise HTTPException(status_code=404, detail="评审记录不存在。")
    return Response(status_code=204)
"""
删除按钮
store.delete(review_id)
"""