"""本地 SQLite 存储层：让评审结果在重启后仍可查询。

这是一个数据持久化层（Repository 模式）的实现类，专门负责将评审报告（ReviewResponse）存入 SQLite 数据库，并提供基础的增删改查（CRUD）操作。
序列化策略清晰：利用 Pydantic 自带的 model_dump_json 和 model_validate_json 完成对象与数据库文本字段的互转，省去了手写繁琐的字段映射代码。
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .schemas import ReviewListItem, ReviewResponse


class ReviewStore:
# 初始化
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize() #创建数据表
#数据库连接
    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path) #调用 sqlite3.connect()，传入实例变量中的路径。如果文件不存在，SQLite 会自动创建该文件。
        connection.row_factory = sqlite3.Row
        return connection #返回连接对象
#初始化数据表
    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    source_name TEXT,
                    review_json TEXT NOT NULL
                )
                """
            )#执行 SQL 建表语句。

    def save(self, review: ReviewResponse) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO reviews (id, title, created_at, source_name, review_json)
                   VALUES (?, ?, ?, ?, ?)""",
                (review.id, review.title, review.created_at.isoformat(), review.source_name, review.model_dump_json()),
            )#INSERT OR REPLACE：如果表中已存在相同 id 的记录，先删除旧行再插入新行（等同于“覆盖更新”）；否则直接插入。
#根据 ID 查询单条记录，返回 ReviewResponse 对象或 None（未找到）。
    def get(self, review_id: str) -> ReviewResponse | None:
        with self._connect() as connection:
            row = connection.execute("SELECT review_json FROM reviews WHERE id = ?", (review_id,)).fetchone()
        return ReviewResponse.model_validate_json(row["review_json"]) if row else None
#如果 row 不为空（即找到了记录），则使用 Pydantic 的 .model_validate_json() 将 JSON 字符串还原为 ReviewResponse 对象（自动校验类型）。
#获取所有历史记录的简要列表（用于前端侧边栏展示），返回 ReviewListItem 列表。
    def list(self) -> list[ReviewListItem]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, title, created_at, source_name, review_json FROM reviews ORDER BY created_at DESC"
            ).fetchall()
        items: list[ReviewListItem] = []
        for row in rows:
            review = ReviewResponse.model_validate_json(row["review_json"])
            items.append(
                ReviewListItem(
                    id=row["id"],
                    title=row["title"],
                    created_at=row["created_at"],
                    source_name=row["source_name"],
                    finding_count=len(review.findings),
                    high_count=review.counts["high"],
                )
            )
        return items
#根据 ID 删除记录，返回布尔值（True 表示删除了至少一行，False 表示 ID 不存在或删除失败）。
    def delete(self, review_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
        return cursor.rowcount > 0
