"""
收藏本模块 - Favorites

管理用户收藏的政策解析报告、申论批改报告和面试记录。
数据存储在 data/favorites.json，以 JSON 文件持久化。

用法:
    from modules.favorites import Favorites

    fav = Favorites()
    fav.add_favorite("policy", "国务院办公厅关于…", "output/policy_20260430.md")
    items = fav.list_favorites()
    fav.remove_favorite(0)
    content = fav.view_favorite(0)
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# ── 数据目录/文件 ──
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FAVORITES_FILE = DATA_DIR / "favorites.json"


class Favorites:
    """收藏本管理器"""

    def __init__(self) -> None:
        """初始化收藏本，确保数据目录和 JSON 文件存在"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not FAVORITES_FILE.exists():
            self._save([])

    # ── 公开方法 ──

    def add_favorite(
        self,
        fav_type: str,
        title: str,
        source_file: str,
    ) -> bool:
        """
        添加一条收藏记录。

        参数:
            fav_type: 类型 "policy" / "shenlun" / "interview"
            title: 标题（自动提取或用户自定义）
            source_file: 指向 output/ 目录中原始报告的路径

        返回:
            是否添加成功
        """
        items = self._load()
        items.append({
            "type": fav_type,
            "title": title,
            "source_file": source_file,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        return self._save(items)

    def list_favorites(self) -> list[dict[str, Any]]:
        """返回所有收藏，按时间倒序"""
        items = self._load()
        return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)

    def remove_favorite(self, index: int) -> bool:
        """
        删除指定索引的收藏记录。

        参数:
            index: 0-based 索引

        返回:
            是否删除成功
        """
        items = self._load()
        if 0 <= index < len(items):
            items.pop(index)
            return self._save(items)
        return False

    def view_favorite(self, index: int) -> str | None:
        """
        查看收藏对应的原始报告内容。

        参数:
            index: 0-based 索引

        返回:
            报告内容文本，若文件不存在或索引无效返回 None
        """
        items = self._load()
        if index < 0 or index >= len(items):
            return None

        source_file = Path(items[index].get("source_file", ""))
        if not source_file.exists():
            return f"[文件已不存在: {source_file}]"

        try:
            return source_file.read_text(encoding="utf-8")
        except Exception as e:
            return f"[读取文件失败: {e}]"

    def count(self) -> int:
        """返回收藏总数"""
        return len(self._load())

    # ── 私有方法 ──

    def _load(self) -> list[dict[str, Any]]:
        """从 JSON 文件加载收藏列表"""
        try:
            if FAVORITES_FILE.exists():
                data = json.loads(FAVORITES_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
        except (json.JSONDecodeError, OSError) as e:
            import warnings
            warnings.warn(f"收藏本数据读取失败，已重置: {e}")
        return []

    def _save(self, items: list[dict[str, Any]]) -> bool:
        """保存收藏列表到 JSON 文件"""
        try:
            FAVORITES_FILE.write_text(
                json.dumps(items, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return True
        except OSError as e:
            import warnings
            warnings.warn(f"收藏本数据保存失败: {e}")
            return False
