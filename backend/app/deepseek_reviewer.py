"""DeepSeek 驱动的三角色 PRD 评审器。"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx
from fastapi import HTTPException

from .schemas import Finding


DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

ROLE_PROMPTS = {
    "产品": "你是一名资深产品经理，评审 PRD 的目标、用户流程、业务规则、权限和异常闭环。",
    "技术": "你是一名资深后端技术负责人，评审 PRD 的数据、接口、状态一致性、性能、安全和工程风险。",
    "测试": "你是一名资深测试工程师，评审 PRD 的边界条件、异常路径、验收标准和回归风险。",
}

OUTPUT_INSTRUCTION = """
仅输出 JSON 对象，不要输出 Markdown。格式必须是：
{"findings":[{"severity":"high|medium|low","title":"问题标题","evidence":"PRD 原文或未明确说明",
"reason":"问题原因","recommendation":"可执行的修改建议"}]}
只报告有依据的问题，最多 5 条。不要杜撰 PRD 未提及的业务事实。
"""


def _parse_findings(content: str, reviewer: str) -> list[Finding]:
    #content为AI返回的原始字符串(预期为json格式)
    try:
        payload = json.loads(content) #将字符串 content 反序列化为 Python 字典 payload。
    except json.JSONDecodeError as exc: #如果 content 不是合法的 JSON 格式（例如缺少引号、括号不匹配），捕获 JSONDecodeError 异常
        raise ValueError("DeepSeek 返回的内容不是有效 JSON。") from exc

    raw_findings = payload.get("findings", []) #从 payload 字典中获取 "findings" 键对应的值。若该键不存在，默认设为空列表 []。
    if not isinstance(raw_findings, list):
        raise ValueError("DeepSeek 返回缺少 findings 数组。")

    findings: list[Finding] = [] #创建一个空列表 findings，类型注解指明里面存放的是 Finding 对象
    for index, item in enumerate(raw_findings[:5], start=1): #enumerate(..., start=1)：从 1 开始生成序号，便于后续生成唯一的 id。
        """
        切片 [:5]：关键业务逻辑。只截取列表的前 5 个元素。
        防止 AI 一次性返回几十上百条发现，导致响应体过大、前端渲染卡顿或数据库写入压力过大。
        """
        if not isinstance(item, dict):
            continue

        severity = item.get("severity", "medium") #尝试从当前 item 字典中读取 severity（严重程度）。若缺失，默认赋值为 "medium"（中等风险）
        findings.append(
            Finding(
                id=f"{reviewer}-{index}", reviewer=reviewer,
                severity=severity if severity in {"high", "medium", "low"} else "medium",
                title=str(item.get("title", "未命名问题"))[:80],
                evidence=str(item.get("evidence", "未明确说明"))[:300],
                reason=str(item.get("reason", "未提供原因"))[:500],
                recommendation=str(item.get("recommendation", "建议补充说明"))[:500],
            )
        )
    return findings



def _review_one_role(document: str, reviewer: str, api_key: str) -> list[Finding]:
    payload: dict[str, Any] = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": ROLE_PROMPTS[reviewer] + OUTPUT_INSTRUCTION},
            {"role": "user", "content": f"请评审以下 PRD：\n\n{document}"},
        ],
        "temperature": 0.2,
        "max_tokens": 1800,
        "response_format": {"type": "json_object"},
    }
    try:
        with httpx.Client(timeout=75) as client:
            response = client.post(
                f"{DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"DeepSeek API 返回错误：{exc.response.text[:300]}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="无法连接 DeepSeek API，请检查网络与配置。") from exc
    try:
        content = response.json()["choices"][0]["message"]["content"]
        return _parse_findings(content, reviewer)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"无法解析 DeepSeek 的结构化结果：{exc}") from exc


def run_deepseek_review(document: str) -> list[Finding]:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="服务端未配置 DEEPSEEK_API_KEY。")
    with ThreadPoolExecutor(max_workers=3) as executor: #线程池
        futures = [executor.submit(_review_one_role, document, role, api_key) for role in ROLE_PROMPTS]
        return [finding for future in futures for finding in future.result()]
