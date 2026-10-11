# 🎯 公考智能解析助手 · PolicyLens

<p align="center">
  <strong>PolicyLens — 面向公考备考者的全流程 AI 辅助工具</strong><br>
  政策解析 · 申论批改 · 面试对练 · 错题本 · 收藏本 · 历史归档
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Web-Streamlit-red?logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/AI-DeepSeek-purple" alt="DeepSeek">
  <img src="https://img.shields.io/badge/CLI%20%2B%20Web-dual%20mode-success" alt="Dual mode">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

---

## 📑 目录

- [✨ 功能特性](#-功能特性)
- [🚀 快速开始](#-快速开始)
- [📁 项目结构](#-项目结构)
- [🔧 技术栈](#-技术栈)
- [🔐 数据与隐私](#-数据与隐私)
- [🔮 路线图](#-路线图)

---

## ✨ 功能特性

### 📋 政策文件解析
粘贴或导入政策原文，AI 提取**核心信号 / 申论金句 / 出题角度 / 面试素材**四类考点。分析结果自动落盘到 `output/policy_<时间戳>.md`，可随时回看与二次引用。

### ✍️ 申论真题评阅
AI 多维评分 + 针对性写作建议，提供两档深度：

| 档位 | 说明 | 适用 |
|---|---|---|
| **quick**（默认） | ①核心信号 ②申论金句 ③出题角度 ④面试素材 | 日常快速浏览，Token 消耗低 |
| **Pro** | 更深度评阅（Token 消耗约多 50%） | 精修一篇时使用 |

文章超过 4000 字会被截断，此时返回值带 `truncated` 标记，界面明确提示"评分仅供参考"——不会假装评了全文。

### 🎤 面试模拟训练
AI 扮演面试官进行多轮追问，计时报告全中文；会话结束后**自动把暴露出的薄弱点写入错题本**。面试记录按时间戳命名（`interview_session_<时间戳>.md`），多次练习不再互相覆盖。

### 📚 错题本
- 申论 / 面试薄弱点自动归档
- 支持关键词检索
- 支持**手动补录**（`main.py` 菜单项 `a`），来源自动标注 `[手动添加]`

### ⭐ 收藏本
收藏政策 / 申论 / 面试素材，支持关键词搜索。数据层做了三道防线：

```
写入：临时文件 + os.replace 原子替换，替换前把上一版轮转为 favorites.bak
读取：文件损坏时不再静默清零 —— 隔离为 favorites.corrupt-<时间戳>.json 并尝试从 .bak 恢复
检索：search_favorites() 关键词过滤
```

### 🕘 历史记录
政策 / 申论 / 面试三类结果**分类浏览**，支持统一查看与删除；解决早期"面试后收藏永远指向固定文件名"的问题。

### 🖥️ 双模式入口

| 模式 | 启动 | 适合 |
|---|---|---|
| **Web** | `python launch.py` | 一键启动 Streamlit 并自动打开浏览器 |
| **CLI** | `python main.py` | 菜单式交互，批处理与脚本化 |
| Windows 快捷方式 | 双击 `考公助手.bat` | 等价于 `python launch.py` |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

> ⚠️ **绝对不要将 `.env` 提交到 GitHub 或公开分享。** 仓库里的 `.env.example` 只是模板，不含真实密钥。

在项目根目录创建 `.env`：

```bash
DEEPSEEK_API_KEY=sk-你的密钥
```

也可以直接用环境变量（推荐，任何启动方式都生效）：

```powershell
# Windows PowerShell
[Environment]::SetEnvironmentVariable('DEEPSEEK_API_KEY','sk-你的密钥','User')
```

```bash
# Linux / macOS
export DEEPSEEK_API_KEY=sk-你的密钥
```

### 3. 启动

```bash
# Web 界面（推荐，自动开浏览器）
python launch.py

# 或 CLI 菜单
python main.py
```

Web 默认地址 `http://127.0.0.1:8501`（**仅监听本机**）。

---

## 📁 项目结构

```
gongkao_ai/
├── launch.py                  # Web 一键启动（Streamlit + 自动开浏览器）
├── main.py                    # CLI 主程序（菜单式交互）
├── config.py                  # 配置模块（从环境变量读取 API Key）
├── app.py                     # Streamlit Web 界面（6 个 Tab）
├── 考公助手.bat                # Windows 双击启动
├── 使用说明书.md               # 完整使用文档
├── modules/
│   ├── policy_analyzer.py     # 政策文件解析
│   ├── shenlun_reviewer.py    # 申论真题评阅（含 truncated 标记）
│   ├── interview_trainer.py   # 面试模拟训练（按时间戳命名）
│   ├── mistake_tracker.py     # 错题本（含手动补录）
│   ├── favorites.py           # 收藏本（原子写 + 备份 + 损坏隔离）
│   └── export_templates.py    # 导出模板
├── utils/
│   └── input_helper.py        # 统一多行输入
├── data/                      # 错题本 / 收藏本数据（本地）
├── output/                    # 分析报告输出（本地）
├── .env.example               # 环境变量模板（不含真实密钥）
└── requirements.txt
```

---

## 🔧 技术栈

| 层 | 技术 | 用途 |
|---|---|---|
| **语言** | Python 3.10+ | — |
| **AI** | DeepSeek API | 政策解析 / 申论评阅 / 面试对练 |
| **Web** | Streamlit | 6 Tab 图形界面 |
| **CLI** | Rich | 终端美化与表格输出 |
| **配置** | python-dotenv / 环境变量 | API Key 管理 |
| **存储** | 本地文件 + SQLite | 错题本 / 收藏本 / 历史归档 |

---

## 🔐 数据与隐私

- 🔑 **API Key 不入库**：只从 `.env` 或环境变量读取，`.env` 已被 `.gitignore` 忽略，仓库里只有 `sk-你的密钥` 这类占位符
- 📍 **数据全部本地**：分析报告在 `output/`，收藏与错题在 `data/`，不上传任何第三方
- 🛡️ **Web 界面无鉴权**：`launch.py` 显式绑定 `127.0.0.1`，**不要**把它暴露到局域网或公网（若确需远程访问，请自己加反代 + 认证）
- 💾 **收藏本防丢**：原子写入 + `favorites.bak` 轮转 + 损坏隔离，避免"一次写坏全没了"

---

## 🔮 路线图

- [ ] **导出增强**：错题本 / 收藏本导出为 Anki / Markdown 合集
- [ ] **题库扩充**：本地真题库接入，减少重复下载
- [ ] **多模型支持**：除 DeepSeek 外可切换其他 OpenAI 兼容端点
- [ ] **Web 鉴权**：为远程访问提供最小可行的登录保护
- [x] **面试记录防覆盖**（时间戳命名）
- [x] **收藏本数据安全**（原子写 + 备份 + 隔离）
- [x] **历史记录分类浏览**
- [x] **一键启动**（`launch.py` / `考公助手.bat`）

---

## 📄 License

[MIT](LICENSE) — 个人学习与备考使用自由。
