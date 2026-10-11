"""
Streamlit 多页应用 - 公考智能解析助手 Web 版

运行方式:
    cd gongkao_ai
    streamlit run app.py

需要先: pip install streamlit
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from config import config
from modules.favorites import load_favorites_file, save_favorites_file
from modules.policy_analyzer import PolicyAnalyzer
from modules.shenlun_reviewer import ShenlunReviewer

# ── 常量 ──
PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DATA_DIR = PROJECT_ROOT / "data"

DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


# ═══════════════════════════════════════
# 收藏本辅助函数（存取统一走 modules/favorites，保证原子写与损坏保护）
# ═══════════════════════════════════════

def _load_favorites() -> list[dict]:
    return load_favorites_file()


def _save_favorites(favs: list[dict]) -> None:
    save_favorites_file(favs)


def _add_favorite(fav_type: str, title: str, source_file: str) -> bool:
    favs = _load_favorites()
    # 防重复
    if any(f.get("source_file") == source_file for f in favs):
        return False
    favs.append({
        "type": fav_type,
        "title": title,
        "source_file": str(source_file),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    _save_favorites(favs)
    return True


def _delete_favorite(index: int) -> None:
    favs = _load_favorites()
    if 0 <= index < len(favs):
        favs.pop(index)
        _save_favorites(favs)


# ═══════════════════════════════════════
# 历史文件扫描（缓存）
# ═══════════════════════════════════════

@st.cache_data(ttl=30)
def _scan_output_files(pattern: str) -> list[dict]:
    """扫描 output 目录，返回文件列表（按修改时间倒序）"""
    files = []
    try:
        for f in sorted(OUTPUT_DIR.glob(pattern), key=lambda x: x.stat().st_mtime, reverse=True):
            stat = f.stat()
            files.append({
                "name": f.name,
                "path": str(f),
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            })
    except OSError:
        pass
    return files


def _clear_file_cache() -> None:
    _scan_output_files.clear()


def _policy_to_markdown(result: dict) -> str:
    lines = [f"# 政策解析报告\n", f"**核心信号**: {result.get('core_signal', '')}\n"]
    for q in result.get("golden_quotes", []):
        lines.append(f"\n### {q.get('quote', '')}")
        lines.append(f"- 出处: {q.get('paragraph_ref', '')}")
        lines.append(f"- 适用: {q.get('source', '')}")
    for a in result.get("exam_angles", []):
        lines.append(f"\n### {a.get('angle', '')}")
        lines.append(a.get("description", ""))
    return "\n".join(lines)


# ── 页面配置 ──
st.set_page_config(
    page_title=config.APP_NAME,
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 侧边栏 ──
with st.sidebar:
    st.title(config.APP_NAME)
    st.caption(f"v{config.APP_VERSION}")
    st.divider()

    if config.DEEPSEEK_API_KEY:
        st.success(f"API 已配置 (来源: {config.KEY_SOURCE})")
    else:
        st.error("API Key 未配置！请设置 .env 文件")
        st.stop()

    st.divider()
    st.caption("面向公考备考者的 AI 辅助工具")

# ── Tab 页 ──
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📄 政策解析", "📝 申论批改", "🎤 面试训练",
    "📋 错题本", "⭐ 收藏本", "📂 历史解析",
])

# ══════════════════════════════════════════════════════════════
# Tab 1: 政策解析
# ══════════════════════════════════════════════════════════════
with tab1:
    st.header("政策文件智能解析")
    st.caption("上传政策文件或粘贴文本，AI 自动提取备考要点")

    col1, col2 = st.columns([1, 1])
    with col1:
        analysis_mode = st.radio("分析模式", ["quick (四维)", "deep (六维)"], horizontal=True)
    with col2:
        uploaded_file = st.file_uploader("上传政策文件 (txt)", type=["txt"])

    policy_text = ""
    if uploaded_file:
        policy_text = uploaded_file.read().decode("utf-8")
        with st.expander("文件内容预览", expanded=False):
            st.text(policy_text[:500] + ("..." if len(policy_text) > 500 else ""))
    else:
        policy_text = st.text_area("或直接粘贴政策文本", height=200, placeholder="请粘贴政策文件内容...")

    if st.button("开始解析", type="primary", key="btn_policy"):
        if not policy_text.strip():
            st.warning("请输入政策文本")
        else:
            with st.spinner("正在调用 DeepSeek API 分析..."):
                analyzer = PolicyAnalyzer()
                mode = "deep" if "deep" in analysis_mode else "quick"
                result = analyzer.analyze_policy(policy_text, mode)

            if "error" in result:
                st.error(result["error"])
            elif "raw_response" in result:
                st.warning("API 返回非标准格式")
                st.text(result["raw_response"])
            else:
                st.success("解析完成！")
                # 保存结果到 output
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                result_file = OUTPUT_DIR / f"policy_{ts}.md"
                md_content = _policy_to_markdown(result)
                result_file.write_text(md_content, encoding="utf-8")
                st.session_state["_last_policy_file"] = str(result_file)
                st.session_state["_last_policy_result"] = result
                _clear_file_cache()

                # 显示结果
                st.subheader("📌 核心信号")
                st.info(result.get("core_signal", "无"))

                quotes = result.get("golden_quotes", [])
                if quotes:
                    st.subheader("🏅 申论金句")
                    for i, q in enumerate(quotes, 1):
                        with st.container(border=True):
                            st.markdown(f"**{i}. {q.get('quote', '')}**")
                            st.caption(f"出处: {q.get('paragraph_ref', '')}")
                            st.caption(f"适用: {q.get('source', '')}")

                angles = result.get("exam_angles", [])
                if angles:
                    st.subheader("📝 申论出题角度")
                    for i, a in enumerate(angles, 1):
                        with st.expander(f"{i}. {a.get('angle', '')}"):
                            st.write(a.get("description", ""))
                            org = a.get("material_organization", "")
                            if org:
                                st.info(f"**材料组织建议**: {org}")

                materials = result.get("interview_material", [])
                if materials:
                    st.subheader("🎤 面试观点素材")
                    for i, m in enumerate(materials, 1):
                        with st.container(border=True):
                            st.markdown(f"**{m.get('viewpoint', '')}**")
                            st.caption(m.get("argument", ""))

                misunderstandings = result.get("common_misunderstandings", [])
                if misunderstandings:
                    st.subheader("⚠️ 常见解读误区")
                    for i, m in enumerate(misunderstandings, 1):
                        st.error(f"**误区**: {m.get('misunderstanding', '')}")
                        st.success(f"**正解**: {m.get('correction', '')}")

                cross_refs = result.get("policy_cross_references", [])
                if cross_refs:
                    st.subheader("🔗 政策交叉关联")
                    for i, c in enumerate(cross_refs, 1):
                        st.markdown(f"**关联**: {c.get('related_policy', '')}")
                        st.caption(c.get("intersection", ""))

                col_a, col_b = st.columns(2)
                with col_a:
                    st.download_button(
                        "下载 JSON 结果",
                        data=json.dumps(result, ensure_ascii=False, indent=2),
                        file_name=f"policy_{ts}.json",
                        mime="application/json",
                    )
                with col_b:
                    if st.button("⭐ 收藏此分析", key="fav_policy"):
                        ok = _add_favorite("政策解析", result.get("core_signal", "政策分析"), str(result_file))
                        if ok:
                            st.toast("已收藏！", icon="⭐")
                        else:
                            st.toast("已收藏过", icon="ℹ️")


# ══════════════════════════════════════════════════════════════
# Tab 2: 申论批改
# ══════════════════════════════════════════════════════════════
with tab2:
    st.header("申论真题深度拆解")
    st.caption("提交真题与文章，AI 扮演阅卷组长+辅导老师给出评分与提升方案")

    col1, col2 = st.columns([1, 2])
    with col1:
        question_type = st.selectbox("题型", ["申发论述", "概括归纳", "综合分析", "贯彻执行"], index=0)
    with col2:
        st.caption("选择正确的题型可获得更准确的评分侧重")

    question = st.text_area("真题题目", height=100, placeholder="请输入申论真题题目...")
    essay = st.text_area("你的文章", height=250, placeholder="请输入你的申论文章...")

    if st.button("提交批改", type="primary", key="btn_shenlun"):
        if not question.strip():
            st.warning("请输入真题题目")
        elif not essay.strip():
            st.warning("请输入你的文章")
        else:
            with st.spinner("正在评阅中（约 10-30 秒）..."):
                reviewer = ShenlunReviewer()
                result = reviewer.evaluate_essay(question, essay, question_type)

            if "error" in result:
                st.error(result["error"])
            else:
                feedback = result["feedback"]
                st.success("评阅完成！")
                st.markdown(feedback)

                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = OUTPUT_DIR / f"shenlun_feedback_{ts}.md"
                filepath.write_text(feedback, encoding="utf-8")
                st.session_state["_last_shenlun_file"] = str(filepath)
                st.session_state["_last_shenlun_title"] = question[:40]

                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.download_button("下载报告", data=feedback, file_name=f"shenlun_feedback_{ts}.md", mime="text/markdown")
                with col_b:
                    if st.button("⭐ 收藏此批改", key="fav_shenlun"):
                        ok = _add_favorite("申论批改", question[:50], str(filepath))
                        if ok:
                            st.toast("已收藏！", icon="⭐")
                        else:
                            st.toast("已收藏过", icon="ℹ️")
                with col_c:
                    pass

                try:
                    from modules.mistake_tracker import MistakeTracker
                    tracker = MistakeTracker()
                    tracker.add_shenlun_mistake(question=question, question_type=question_type, feedback=feedback)
                    st.caption("📋 已自动记录到错题本")
                except Exception:
                    pass


# ══════════════════════════════════════════════════════════════
# Tab 3: 面试训练
# ══════════════════════════════════════════════════════════════
with tab3:
    st.header("面试模拟对练")
    st.caption("AI 模拟体制内面试官，动态出题、追问+反馈")

    col1, col2 = st.columns([1, 1])
    with col1:
        interview_mode = st.radio("模式", ["普通模式", "高仿真 (10分钟3题)"], horizontal=True)
    with col2:
        if interview_mode == "普通模式":
            direction = st.selectbox("方向", ["结构化", "专业面"])
            max_rounds = st.slider("训练轮次", 1, 5, 3)
        else:
            direction = "结构化"
            max_rounds = 3

    topic = st.text_input("面试主题", placeholder="如: 基层治理 / 新能源汽车电池")

    if "interview_messages" not in st.session_state:
        st.session_state.interview_messages = []
        st.session_state.interview_round = 0
        st.session_state.interview_active = False
        st.session_state.interview_trainer = None

    if st.button("开始面试", type="primary", key="btn_interview"):
        if not topic.strip():
            st.warning("请输入面试主题")
        else:
            from modules.interview_trainer import InterviewTrainer
            trainer = InterviewTrainer(max_rounds=max_rounds)
            st.session_state.interview_trainer = trainer
            st.session_state.interview_messages = []
            st.session_state.interview_round = 0
            st.session_state.interview_active = True

            try:
                msgs = [
                    {"role": "system", "content": "你是一位体制内面试官。请根据主题出一道结构化面试题。只输出题目。"},
                    {"role": "user", "content": f"面试主题：{topic}\n请出第一题。"},
                ]
                q1 = trainer._call_api(msgs)
                st.session_state.interview_messages.append({"role": "assistant", "content": q1})
                st.session_state.interview_round = 1
            except Exception as e:
                st.error(f"出题失败: {e}")
                st.session_state.interview_active = False
            st.rerun()

    for msg in st.session_state.interview_messages:
        if msg["role"] == "assistant":
            with st.chat_message("assistant", avatar="🎓"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg["content"])

    if st.session_state.interview_active:
        user_input = st.chat_input("输入你的回答...")
        if user_input:
            st.session_state.interview_messages.append({"role": "user", "content": user_input})
            trainer = st.session_state.interview_trainer
            with st.spinner("面试官思考中..."):
                api_msgs = [{"role": "system", "content": "你是一位体制内面试官。首轮出题。中间轮: 【反馈】≤50字点评\\n【追问】第X题：[题目]。最后一轮后输出【面试总结】。"}] + st.session_state.interview_messages
                if st.session_state.interview_round >= max_rounds:
                    api_msgs.append({"role": "user", "content": "面试结束，请输出【面试总结】。"})
                try:
                    resp = trainer._call_api(api_msgs)
                    st.session_state.interview_messages.append({"role": "assistant", "content": resp})
                    st.session_state.interview_round += 1
                    if "面试总结" in resp:
                        st.session_state.interview_active = False
                except Exception as e:
                    st.error(f"API 错误: {e}")
            st.rerun()

    if st.session_state.interview_messages and not st.session_state.interview_active:
        st.success("面试结束！")
        full_md = "\n\n".join(f"**{m['role']}**: {m['content']}" for m in st.session_state.interview_messages)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        iv_file = OUTPUT_DIR / f"interview_{ts}.md"
        iv_file.write_text(full_md, encoding="utf-8")
        st.session_state["_last_interview_file"] = str(iv_file)
        st.session_state["_last_interview_topic"] = topic

        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button("下载对话记录", data=full_md, file_name=f"interview_{ts}.md")
        with col_b:
            if st.button("⭐ 收藏此对话", key="fav_interview"):
                ok = _add_favorite("面试对练", topic, str(iv_file))
                if ok:
                    st.toast("已收藏！", icon="⭐")
                else:
                    st.toast("已收藏过", icon="ℹ️")
        if st.button("重新开始"):
            st.session_state.interview_messages = []
            st.session_state.interview_round = 0
            st.session_state.interview_active = False
            st.rerun()


# ══════════════════════════════════════════════════════════════
# Tab 4: 错题本
# ══════════════════════════════════════════════════════════════
with tab4:
    st.header("错题本")
    st.caption("申论与面试的薄弱点记录，自动积累，辅助复习")

    try:
        from modules.mistake_tracker import MistakeTracker
        tracker = MistakeTracker()
        stats = tracker.get_stats()
    except Exception as e:
        st.error("错题本数据库读取失败，请检查 data/mistakes.db 是否完整。")
        st.caption(f"错误详情: {e}")
        st.stop()

    if stats["shenlun_total"] == 0 and stats["interview_total"] == 0:
        st.info("暂无错题记录。使用申论批改功能后，薄弱点会自动记录到这里。")
    else:
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.metric("申论错题", f"{stats['shenlun_total']} 条")
                if stats["shenlun_by_type"]:
                    st.caption("按题型分布")
                    st.bar_chart(
                        {r["question_type"]: r["cnt"] for r in stats["shenlun_by_type"]},
                        horizontal=True,
                    )
        with col2:
            with st.container(border=True):
                st.metric("面试错题", f"{stats['interview_total']} 条")
                if stats["interview_by_topic"]:
                    st.caption("按主题分布")
                    st.bar_chart(
                        {r["topic"]: r["cnt"] for r in stats["interview_by_topic"]},
                        horizontal=True,
                    )

        # 详情展开
        choice = st.radio("查看详情", ["申论错题", "面试错题"], horizontal=True)
        if choice == "申论错题":
            try:
                mistakes = tracker.get_shenlun_mistakes(limit=20)
            except Exception:
                mistakes = []
            if not mistakes:
                st.info("暂无申论错题记录")
            else:
                for i, m in enumerate(mistakes):
                    with st.expander(f"{i+1}. [{m.get('question_type','')}] {m.get('question','')[:60]}"):
                        st.caption(f"记录时间: {m.get('created_at','')}")
                        if m.get("weak_points"):
                            st.warning(f"薄弱点: {m['weak_points']}")
                        if m.get("feedback_summary"):
                            st.text(m["feedback_summary"][:300])
        else:
            try:
                mistakes = tracker.get_interview_mistakes(limit=20)
            except Exception:
                mistakes = []
            if not mistakes:
                st.info("暂无面试错题记录")
            else:
                for i, m in enumerate(mistakes):
                    with st.expander(f"{i+1}. [{m.get('topic','')}] {m.get('question','')[:60]}"):
                        st.caption(f"记录时间: {m.get('created_at','')}")
                        if m.get("weak_point"):
                            st.warning(f"薄弱点: {m['weak_point']}")
                        if m.get("answer_summary"):
                            st.text(m["answer_summary"][:300])


# ══════════════════════════════════════════════════════════════
# Tab 5: 收藏本
# ══════════════════════════════════════════════════════════════
with tab5:
    st.header("收藏本")
    st.caption("你在政策解析、申论批改、面试对练中收藏的报告")

    try:
        favs = _load_favorites()
    except Exception:
        favs = []

    if not favs:
        st.info("收藏本还是空的，去政策解析 / 申论批改 / 面试对练里按 ⭐ 收藏吧！")

    # 按类型分组
    policy_favs = [f for f in favs if f.get("type") == "政策解析"]
    shenlun_favs = [f for f in favs if f.get("type") == "申论批改"]
    interview_favs = [f for f in favs if f.get("type") == "面试对练"]

    def _render_fav_group(label: str, items: list[dict], icon: str) -> None:
        if not items:
            return
        st.subheader(f"{icon} {label} ({len(items)})")
        for i, item in enumerate(items):
            idx_in_full = favs.index(item)
            with st.container(border=True):
                col1, col2 = st.columns([6, 1])
                with col1:
                    st.markdown(f"**{item.get('title', '无标题')}**")
                    st.caption(f"{item.get('created_at', '')}")
                with col2:
                    if st.button("🗑️", key=f"del_fav_{idx_in_full}", help="删除"):
                        _delete_favorite(idx_in_full)
                        st.rerun()
                # 展开查看原文
                sf = item.get("source_file", "")
                if sf and Path(sf).exists():
                    with st.expander("查看原文"):
                        try:
                            content = Path(sf).read_text(encoding="utf-8")
                            st.markdown(content)
                        except Exception:
                            st.warning("文件读取失败，可能已被移动或删除")
                elif sf:
                    st.caption("⚠️ 原始文件已不存在")

    _render_fav_group("政策解析", policy_favs, "📄")
    _render_fav_group("申论批改", shenlun_favs, "📝")
    _render_fav_group("面试对练", interview_favs, "🎤")


# ══════════════════════════════════════════════════════════════
# Tab 6: 历史解析
# ══════════════════════════════════════════════════════════════
with tab6:
    st.header("历史解析记录")
    st.caption("所有政策解析报告，按时间倒序排列")

    try:
        files = _scan_output_files("policy_*.md")
    except Exception:
        files = []

    if not files:
        st.info("暂无历史解析记录。使用政策解析功能后，报告会自动保存在这里。")
    else:
        st.caption(f"共 {len(files)} 条记录")

        for f in files:
            col1, col2, col3 = st.columns([5, 2, 1])
            with col1:
                st.markdown(f"**{f['name']}**")
                st.caption(f"{f['mtime']} · {f['size']} B")
            with col2:
                if st.button("📖 查看", key=f"view_{f['name']}", use_container_width=True):
                    try:
                        content = Path(f["path"]).read_text(encoding="utf-8")
                        with st.expander(f"📄 {f['name']}", expanded=True):
                            st.markdown(content)
                    except Exception:
                        st.warning("文件读取失败")
            with col3:
                if st.button("🗑️", key=f"del_{f['name']}", help="删除此文件"):
                    try:
                        Path(f["path"]).unlink()
                        _clear_file_cache()
                        st.toast("已删除", icon="🗑️")
                        st.rerun()
                    except Exception:
                        st.warning("删除失败")
