"""MVP 规则评审器。

接口和输出结构与未来的 LangGraph/LLM 工作流保持一致，以便替换实现而不改变前端。
"""

from .schemas import Finding


RULES = [
    {
        "keywords": ("注销", "删除账号", "删除用户"),
        "reviewer": "产品",
        "severity": "high",
        "title": "未定义账号注销后的数据处理策略",
        "reason": "需求涉及个人数据，但没有说明订单、内容、日志等数据的删除、匿名化或保留期限。",
        "recommendation": "按数据类型明确删除范围、保留期限、撤销机制及相关用户提示。",
    },
    {
        "keywords": ("支付", "退款", "订单", "订阅"),
        "reviewer": "技术",
        "severity": "high",
        "title": "交易状态与异常处理未说明",
        "reason": "涉及交易的流程若缺少失败、重试、退款和状态同步设计，容易造成资损或对账问题。",
        "recommendation": "补充状态机、幂等键、回调校验、失败重试及人工介入流程。",
    },
    {
        "keywords": ("权限", "管理员", "角色", "登录"),
        "reviewer": "产品",
        "severity": "medium",
        "title": "权限边界需要细化",
        "reason": "文档出现账户或角色相关能力，但未明确各角色可见数据和可执行操作。",
        "recommendation": "补充角色权限矩阵，以及越权访问、权限变更后的生效规则。",
    },
    {
        "keywords": ("上传", "文件", "图片", "附件"),
        "reviewer": "技术",
        "severity": "medium",
        "title": "文件处理约束未定义",
        "reason": "未限定文件格式、大小、存储位置和内容安全检查方式。",
        "recommendation": "定义格式与大小白名单、病毒扫描、对象存储策略和失败提示。",
    },
    {
        "keywords": ("立即", "自动", "成功"),
        "reviewer": "测试",
        "severity": "medium",
        "title": "验收标准缺少异常路径",
        "reason": "只描述了成功流程，没有覆盖网络中断、重复操作、权限不足等情况。",
        "recommendation": "为每个关键流程补充前置条件、失败提示、重试和幂等验收用例。",
    },
]


def excerpt(document: str, keyword: str) -> str:
    position = document.find(keyword)
    if position < 0:
        return document[:80]
    start = max(0, position - 30)
    end = min(len(document), position + len(keyword) + 50)
    return document[start:end].replace("\n", " ")


def run_review(document: str) -> list[Finding]:
    findings: list[Finding] = []
    for index, rule in enumerate(RULES, start=1):
        keyword = next((item for item in rule["keywords"] if item in document), None)
        if keyword is None:
            continue
        findings.append(
            Finding(
                id=f"F-{index:03}",
                severity=rule["severity"],
                reviewer=rule["reviewer"],
                title=rule["title"],
                evidence=excerpt(document, keyword),
                reason=rule["reason"],
                recommendation=rule["recommendation"],
            )
        )

    if not findings:
        findings.append(
            Finding(
                id="F-001",
                severity="low",
                reviewer="测试",
                title="建议补充可验证的验收标准",
                evidence=document[:100].replace("\n", " "),
                reason="未命中当前 MVP 的高风险规则；仍建议将需求描述转为可观测、可复现的验收条件。",
                recommendation="为关键流程补充输入、预期输出、异常提示与完成条件。",
            )
        )
    return findings
