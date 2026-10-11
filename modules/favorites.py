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
import os
import shutil
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any


# ── 数据目录/文件 ──
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FAVORITES_FILE = DATA_DIR / "favorites.json"


def load_favorites_file() -> list[dict[str, Any]]:
    """读取收藏 JSON；文件损坏时保留现场并尝试从备份恢复，绝不静默清零"""
    for attempt in range(2):
        if not FAVORITES_FILE.exists():
            return []
        try:
            data = json.loads(FAVORITES_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            reason = f"数据格式异常: 期望列表，实际 {type(data).__name__}"
        except (json.JSONDecodeError, OSError) as e:
            reason = str(e)
        if attempt == 0:
            # 第一轮失败：隔离坏文件并尝试从备份恢复，第二轮读取恢复结果
            _quarantine_and_restore(reason)
    return []


def _quarantine_and_restore(reason: str) -> None:
    """把损坏的收藏文件改名保留，并尝试从 favorites.bak 恢复上一版"""
    corrupt = FAVORITES_FILE.with_name(
        f"favorites.corrupt-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    try:
        FAVORITES_FILE.replace(corrupt)
        warnings.warn(f"收藏本数据文件损坏（{reason}），已保留为 {corrupt.name}，尝试从备份恢复")
    except OSError as replace_err:
        warnings.warn(f"收藏本数据损坏（{reason}）且无法保留原文件: {replace_err}")
        return

    bak = FAVORITES_FILE.with_suffix(".bak")
    if not bak.exists():
        return
    try:
        data = json.loads(bak.read_text(encoding="utf-8"))
        if isinstance(data, list) and save_favorites_file(data):
            warnings.warn(f"已从备份 {bak.name} 恢复 {len(data)} 条收藏")
    except (json.JSONDecodeError, OSError) as bak_err:
        warnings.warn(f"备份文件也不可读，请手动检查 {corrupt.name} 与 {bak.name}: {bak_err}")


def save_favorites_file(items: list[dict[str, Any]]) -> bool:
    """原子保存收藏列表：先写临时文件再 os.replace；替换前把上一版轮转为 favorites.bak"""
    tmp = FAVORITES_FILE.with_suffix(".tmp")
    bak = FAVORITES_FILE.with_suffix(".bak")
    try:
        if FAVORITES_FILE.exists():
            try:
                shutil.copyfile(FAVORITES_FILE, bak)  # 备份失败不阻塞保存
            except OSError:
                pass
        tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, FAVORITES_FILE)
        return True
    except OSError as e:
        warnings.warn(f"收藏本数据保存失败: {e}")
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return False


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

    def search_favorites(self, keyword: str) -> list[dict[str, Any]]:
        """
        按关键词搜索收藏（标题字段大小写不敏感匹配）。

        参数:
            keyword: 搜索关键词

        返回:
            匹配的收藏条目列表
        """
        if not keyword or not keyword.strip():
            return self.list_favorites()
        items = self.list_favorites()
        kw = keyword.strip().lower()
        return [
            item for item in items
            if kw in item.get("title", "").lower()
        ]

    # ── 私有方法 ──

    def _load(self) -> list[dict[str, Any]]:
        """从 JSON 文件加载收藏列表"""
        return load_favorites_file()

    def _save(self, items: list[dict[str, Any]]) -> bool:
        """保存收藏列表到 JSON 文件（原子写，损坏自动隔离）"""
        return save_favorites_file(items)
