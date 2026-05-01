"""
社群导出模版 - 将分析结果转换为可直接发布到小红书的 Markdown 格式

支持导出模式:
    - xiaohongshu: 小红书风格（emoji、短句、话题标签）
    - community: 公考社群风格（结构化、适合 Notion/飞书）
    - plain: 纯文本摘要

用法:
    from modules.export_templates import export_policy_analysis

    md = export_policy_analysis(result, mode="xiaohongshu")
"""
from typing import Any


def export_policy_analysis(result: dict[str, Any], mode: str = "xiaohongshu") -> str:
    """将政策解析结果导出为社群模版"""
    if mode == "xiaohongshu":
        return _policy_to_xiaohongshu(result)
    elif mode == "community":
        return _policy_to_community(result)
    else:
        return _policy_to_plain(result)


def export_shenlun_feedback(feedback: str, mode: str = "xiaohongshu") -> str:
    """将申论评阅反馈导出为社群模版"""
    if mode == "xiaohongshu":
        return _shenlun_to_xiaohongshu(feedback)
    elif mode == "community":
        return _shenlun_to_community(feedback)
    else:
        return feedback


def export_interview_summary(
    messages: list[dict[str, str]], topic: str, mode: str = "xiaohongshu"
) -> str:
    """将面试记录导出为社群模版"""
    if mode == "xiaohongshu":
        return _interview_to_xiaohongshu(messages, topic)
    elif mode == "community":
        return _interview_to_community(messages, topic)
    else:
        return _interview_to_plain(messages, topic)


# ── 小红书模版 ──

def _policy_to_xiaohongshu(result: dict[str, Any]) -> str:
    lines = [
        "📚 公考政策速递 | 一篇读懂最新考点",
        "",
        "---",
        "",
        f"💡 **核心信号**: {result.get('core_signal', '')}",
        "",
    ]

    quotes = result.get("golden_quotes", [])
    if quotes:
        lines.append("✍️ **申论金句** (直接背!)")
        for q in quotes:
            lines.append(f"- 「{q.get('quote', '')}」")
            lines.append(f"  📍 {q.get('paragraph_ref', '')[:50]}")
        lines.append("")

    angles = result.get("exam_angles", [])
    if angles:
        lines.append("🎯 **出题角度预测**")
        for a in angles:
            lines.append(f"- **{a.get('angle', '')}**: {a.get('description', '')[:60]}")
        lines.append("")

    materials = result.get("interview_material", [])
    if materials:
        lines.append("💬 **面试观点素材**")
        for m in materials:
            lines.append(f"- {m.get('viewpoint', '')}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "#公考 #申论 #政策解读 #公务员考试 #备考干货",
        "",
        "💾 工具: 公考智能解析助手 | AI驱动",
    ])
    return "\n".join(lines)


def _shenlun_to_xiaohongshu(feedback: str) -> str:
    lines = [
        "📝 申论批改复盘 | AI 阅卷组长给你的评分",
        "",
        "---",
        "",
        feedback[:800],
        "",
        "---",
        "",
        "📌 **我的反思**:",
        "- (在这里写下你的复盘)",
        "- (下次要注意的点)",
        "",
        "#申论批改 #公考 #AI辅助学习 #备考打卡",
    ]
    return "\n".join(lines)


def _interview_to_xiaohongshu(
    messages: list[dict[str, str]], topic: str
) -> str:
    qa_pairs: list[str] = []
    for m in messages:
        role = "🎓 面试官" if m["role"] == "assistant" else "👤 我"
        qa_pairs.append(f"**{role}**: {m['content'][:150]}")

    lines = [
        f"🎤 面试模拟复盘 | 主题: {topic}",
        "",
        "---",
        "",
    ] + qa_pairs + [
        "",
        "---",
        "",
        "📌 **本场收获**:",
        "- (写下你的心得)",
        "",
        "#公务员面试 #结构化面试 #面试技巧 #公考备考",
    ]
    return "\n".join(lines)


# ── 社群模版 ──

def _policy_to_community(result: dict[str, Any]) -> str:
    lines = [
        "# 政策解析报告",
        "",
        f"> **核心信号**: {result.get('core_signal', '')}",
        "",
        "## 申论金句",
    ]
    for q in result.get("golden_quotes", []):
        lines.append(f"- **{q.get('quote', '')}**")
        lines.append(f"  - 出处: {q.get('paragraph_ref', '')}")
        lines.append(f"  - 适用: {q.get('source', '')}")

    lines.append("\n## 出题角度")
    for a in result.get("exam_angles", []):
        lines.append(f"### {a.get('angle', '')}")
        lines.append(a.get("description", ""))
        org = a.get("material_organization", "")
        if org:
            lines.append(f"> 材料组织: {org}")

    return "\n".join(lines)


def _shenlun_to_community(feedback: str) -> str:
    return feedback


def _interview_to_community(
    messages: list[dict[str, str]], topic: str
) -> str:
    lines = [f"# 面试记录: {topic}\n"]
    for m in messages:
        role = "面试官" if m["role"] == "assistant" else "考生"
        lines.append(f"**{role}**: {m['content']}\n")
    return "\n".join(lines)


# ── 纯文本 ──

def _policy_to_plain(result: dict[str, Any]) -> str:
    return str(result)

def _interview_to_plain(
    messages: list[dict[str, str]], _topic: str
) -> str:
    return "\n\n".join(f"[{m['role']}] {m['content']}" for m in messages)
