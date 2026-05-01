"""
错题本模块 - SQLite 持久化存储

记录用户在申论批改和面试训练中的薄弱点，
支持按模块/题型/时间查询，为复习提供数据支撑。

用法:
    from modules.mistake_tracker import MistakeTracker

    tracker = MistakeTracker()
    tracker.add_shenlun_mistake(question="...", question_type="申发论述", feedback="...")
    tracker.add_interview_mistake(topic="基层治理", question="...", weak_point="...")

    # 查询
    mistakes = tracker.get_shenlun_mistakes(limit=10)
    stats = tracker.get_stats()
"""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 数据库路径
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "mistakes.db"


def _get_connection() -> sqlite3.Connection:
    """获取数据库连接（自动创建目录和表）"""
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _init_tables(conn)
    return conn


def _init_tables(conn: sqlite3.Connection) -> None:
    """初始化数据库表"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS shenlun_mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            question_type TEXT NOT NULL,
            weak_points TEXT,
            score_range TEXT,
            feedback_summary TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS interview_mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            question TEXT NOT NULL,
            weak_point TEXT,
            answer_summary TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE INDEX IF NOT EXISTS idx_shenlun_type
            ON shenlun_mistakes(question_type);
        CREATE INDEX IF NOT EXISTS idx_shenlun_created
            ON shenlun_mistakes(created_at);
        CREATE INDEX IF NOT EXISTS idx_interview_topic
            ON interview_mistakes(topic);
        CREATE INDEX IF NOT EXISTS idx_interview_created
            ON interview_mistakes(created_at);
    """)
    conn.commit()


class MistakeTracker:
    """错题本管理器"""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or str(DB_PATH)
        self.conn = _get_connection() if db_path is None else sqlite3.connect(self.db_path)

    # ── 申论错题 ──

    def add_shenlun_mistake(
        self,
        question: str,
        question_type: str,
        feedback: str = "",
        weak_points: str = "",
        score_range: str = "",
    ) -> int:
        """
        记录一条申论错题。

        参数:
            question: 真题题目
            question_type: 题型（概括归纳/综合分析/贯彻执行/申发论述）
            feedback: AI 评阅反馈全文
            weak_points: 手动标注或自动提取的薄弱点
            score_range: 预估分数区间

        返回:
            新纪录 ID
        """
        # 自动从反馈中提取关键薄弱点
        if not weak_points and feedback:
            weak_points = self._extract_weak_points(feedback)

        summary = feedback[:200] if feedback else ""

        cursor = self.conn.execute(
            """INSERT INTO shenlun_mistakes
               (question, question_type, weak_points, score_range, feedback_summary)
               VALUES (?, ?, ?, ?, ?)""",
            (question, question_type, weak_points, score_range, summary),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_shenlun_mistakes(
        self,
        question_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """查询申论错题记录"""
        if question_type:
            rows = self.conn.execute(
                "SELECT * FROM shenlun_mistakes WHERE question_type = ? ORDER BY created_at DESC LIMIT ?",
                (question_type, limit),
            )
        else:
            rows = self.conn.execute(
                "SELECT * FROM shenlun_mistakes ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        return [dict(r) for r in rows]

    # ── 面试错题 ──

    def add_interview_mistake(
        self,
        topic: str,
        question: str,
        weak_point: str = "",
        answer_summary: str = "",
    ) -> int:
        """
        记录一条面试薄弱点。

        参数:
            topic: 面试主题
            question: 面试题目
            weak_point: 薄弱点描述
            answer_summary: 回答摘要

        返回:
            新纪录 ID
        """
        cursor = self.conn.execute(
            """INSERT INTO interview_mistakes
               (topic, question, weak_point, answer_summary)
               VALUES (?, ?, ?, ?)""",
            (topic, question, weak_point, answer_summary),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_interview_mistakes(
        self,
        topic: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """查询面试错题记录"""
        if topic:
            rows = self.conn.execute(
                "SELECT * FROM interview_mistakes WHERE topic = ? ORDER BY created_at DESC LIMIT ?",
                (topic, limit),
            )
        else:
            rows = self.conn.execute(
                "SELECT * FROM interview_mistakes ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        return [dict(r) for r in rows]

    # ── 统计 ──

    def get_stats(self) -> dict[str, Any]:
        """获取错题统计概览"""
        shenlun_total = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM shenlun_mistakes"
        ).fetchone()["cnt"]

        interview_total = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM interview_mistakes"
        ).fetchone()["cnt"]

        # 按题型分布
        type_dist = self.conn.execute(
            "SELECT question_type, COUNT(*) as cnt FROM shenlun_mistakes GROUP BY question_type"
        ).fetchall()

        # 按主题分布
        topic_dist = self.conn.execute(
            "SELECT topic, COUNT(*) as cnt FROM interview_mistakes GROUP BY topic"
        ).fetchall()

        # 最近记录
        recent = self.conn.execute(
            "SELECT question, question_type, created_at FROM shenlun_mistakes "
            "UNION ALL "
            "SELECT question, topic, created_at FROM interview_mistakes "
            "ORDER BY created_at DESC LIMIT 5"
        ).fetchall()

        return {
            "shenlun_total": shenlun_total,
            "interview_total": interview_total,
            "shenlun_by_type": [dict(r) for r in type_dist],
            "interview_by_topic": [dict(r) for r in topic_dist],
            "recent": [dict(r) for r in recent],
        }

    # ── 辅助 ──

    @staticmethod
    def _extract_weak_points(feedback: str) -> str:
        """从 AI 反馈中自动提取薄弱点关键词"""
        keywords = []
        indicators = [
            ("缺乏", "lack"),
            ("不足", "insufficient"),
            ("薄弱", "weak"),
            ("扣分", "deduction"),
            ("主要问题", "main_issue"),
            ("短板", "shortcoming"),
        ]
        for line in feedback.split("\n"):
            for cn, _ in indicators:
                if cn in line:
                    keywords.append(line.strip())
                    break
        return "; ".join(keywords[:5]) if keywords else feedback[:100]


# ── 向后兼容的函数接口 ──

def get_mistake_stats() -> dict[str, Any]:
    """获取错题统计（向后兼容）"""
    tracker = MistakeTracker()
    return tracker.get_stats()
