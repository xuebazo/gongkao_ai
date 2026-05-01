"""
Streamlit 多页应用 - 公考智能解析助手 Web 版

运行方式:
    cd gongkao_ai
    streamlit run app.py

需要先: pip install streamlit
"""
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from config import config
from modules.policy_analyzer import PolicyAnalyzer
from modules.shenlun_reviewer import ShenlunReviewer

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

    # API Key 状态
    if config.DEEPSEEK_API_KEY:
        st.success(f"API 已配置 (来源: {config.KEY_SOURCE})")
    else:
        st.error("API Key 未配置！请设置 .env 文件")
        st.stop()

    st.divider()
    st.caption("面向公考备考者的 AI 辅助工具")

# ── Tab 页 ──
tab1, tab2, tab3 = st.tabs(["📄 政策解析", "📝 申论批改", "🎤 面试训练"])

# ═══════════════════════════════════════════════════════
# Tab 1: 政策解析
# ═══════════════════════════════════════════════════════
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

                # 核心信号
                st.subheader("📌 核心信号")
                st.info(result.get("core_signal", "无"))

                # 金句
                quotes = result.get("golden_quotes", [])
                if quotes:
                    st.subheader("🏅 申论金句")
                    for i, q in enumerate(quotes, 1):
                        with st.container(border=True):
                            st.markdown(f"**{i}. {q.get('quote', '')}**")
                            st.caption(f"出处: {q.get('paragraph_ref', '')}")
                            st.caption(f"适用: {q.get('source', '')}")

                # 出题角度
                angles = result.get("exam_angles", [])
                if angles:
                    st.subheader("📝 申论出题角度")
                    for i, a in enumerate(angles, 1):
                        with st.expander(f"{i}. {a.get('angle', '')}"):
                            st.write(a.get("description", ""))
                            org = a.get("material_organization", "")
                            if org:
                                st.info(f"**材料组织建议**: {org}")

                # 面试素材
                materials = result.get("interview_material", [])
                if materials:
                    st.subheader("🎤 面试观点素材")
                    for i, m in enumerate(materials, 1):
                        with st.container(border=True):
                            st.markdown(f"**{m.get('viewpoint', '')}**")
                            st.caption(m.get("argument", ""))

                # Deep 模式额外维度
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

                # 导出
                st.download_button(
                    "下载 JSON 结果",
                    data=__import__("json").dumps(result, ensure_ascii=False, indent=2),
                    file_name="policy_analysis.json",
                    mime="application/json",
                )


# ═══════════════════════════════════════════════════════
# Tab 2: 申论批改
# ═══════════════════════════════════════════════════════
with tab2:
    st.header("申论真题深度拆解")
    st.caption("提交真题与文章，AI 扮演阅卷组长+辅导老师给出评分与提升方案")

    col1, col2 = st.columns([1, 2])
    with col1:
        question_type = st.selectbox(
            "题型",
            ["申发论述", "概括归纳", "综合分析", "贯彻执行"],
            index=0,
        )
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

                # 保存 + 下载
                output_dir = Path("output")
                output_dir.mkdir(exist_ok=True)
                from datetime import datetime
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = output_dir / f"shenlun_feedback_{ts}.md"
                filepath.write_text(feedback, encoding="utf-8")

                st.download_button(
                    "下载评阅报告 (Markdown)",
                    data=feedback,
                    file_name=f"shenlun_feedback_{ts}.md",
                    mime="text/markdown",
                )

                # ── 错题本集成 ──
                try:
                    from modules.mistake_tracker import MistakeTracker
                    tracker = MistakeTracker()
                    tracker.add_shenlun_mistake(
                        question=question,
                        question_type=question_type,
                        feedback=feedback,
                    )
                    st.caption("📋 已自动记录到错题本")
                except Exception:
                    pass


# ═══════════════════════════════════════════════════════
# Tab 3: 面试训练
# ═══════════════════════════════════════════════════════
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

    # 会话状态管理
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

            # 获取第一题
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

    # 显示对话
    for msg in st.session_state.interview_messages:
        if msg["role"] == "assistant":
            with st.chat_message("assistant", avatar="🎓"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg["content"])

    # 用户输入
    if st.session_state.interview_active:
        user_input = st.chat_input("输入你的回答...")
        if user_input:
            st.session_state.interview_messages.append({"role": "user", "content": user_input})
            trainer = st.session_state.interview_trainer

            # 调用 AI 获取反馈+追问
            with st.spinner("面试官思考中..."):
                api_msgs = [{"role": "system", "content": """你是一位体制内面试官。
首轮出题。中间轮: 【反馈】≤50字点评\n【追问】第X题：[题目]。
最后一轮后输出【面试总结】。"""}] + st.session_state.interview_messages

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

    # 面试结束后显示操作
    if st.session_state.interview_messages and not st.session_state.interview_active:
        st.success("面试结束！")
        full_md = "\n\n".join(
            f"**{m['role']}**: {m['content']}"
            for m in st.session_state.interview_messages
        )
        st.download_button("下载对话记录", data=full_md, file_name="interview_session.md")
        if st.button("重新开始"):
            st.session_state.interview_messages = []
            st.session_state.interview_round = 0
            st.session_state.interview_active = False
            st.rerun()
