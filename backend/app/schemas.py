from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field
#pydantic的强校验性

Severity = Literal["high", "medium", "low"]
Reviewer = Literal["产品", "技术", "测试"]


class ReviewRequest(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    document: str = Field(min_length=30, max_length=30_000)
#前端给后端发请求时的数据模式

class Finding(BaseModel):
    id: str
    severity: Severity
    reviewer: Reviewer
    title: str
    evidence: str
    reason: str
    recommendation: str
    #AI输出的单条问题


class ReviewResponse(BaseModel):
    id: str
    title: str
    summary: str
    findings: list[Finding]
    counts: dict[Severity, int]
    created_at: datetime
    source_name: str | None = None
#后端给前端返回的报告展示

class ReviewListItem(BaseModel):
    id: str
    title: str
    created_at: datetime
    finding_count: int
    high_count: int
    source_name: str | None = None
#历史列表模型