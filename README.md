# 公考智能解析助手 (PolicyLens)

面向全体公考备考者的通用 AI 工具，可从政策文件、申论真题、面试题库中智能提取考点、生成解析与模拟训练素材。

## 项目结构

```
gongkao_ai/
├── main.py                    # 主程序入口（菜单式交互）
├── config.py                  # 配置模块（环境变量读取）
├── app.py                     # Streamlit Web 界面
├── modules/
│   ├── policy_analyzer.py     # 政策文件解析模块
│   ├── shenlun_reviewer.py    # 申论真题评阅模块
│   ├── interview_trainer.py   # 面试模拟训练模块
│   ├── mistake_tracker.py     # 错题本
│   ├── favorites.py           # 收藏本
│   └── export_templates.py    # 导出模板
├── utils/
│   └── input_helper.py        # 统一多行输入工具
├── data/                      # 错题本/收藏本数据
├── output/                    # 分析报告输出
├── .env.example               # 环境变量模板
├── requirements.txt           # 项目依赖
└── README.md
```

## 配置说明

> ⚠️ **绝对不要将 `.env` 文件提交到 GitHub 或公开分享。**
> 请使用环境变量或本地 `.env` 文件管理您的 API Key。
> 项目中的 `.env.example` 仅作为模板参考，不含真实密钥。

在项目根目录创建 `.env` 文件（可参考 `.env.example`）：

```
DEEPSEEK_API_KEY=your_api_key_here
```

## 快速开始

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 配置 API Key（如上，创建 `.env` 文件）

3. 运行主程序：
   ```bash
   python main.py
   ```

## 功能模块

| 模块 | 功能 | 状态 |
|------|------|------|
| 政策文件解析 | 提取政策考点与结构化信息 | 🚧 开发中 |
| 申论真题评阅 | AI 评分与写作建议 | 🚧 开发中 |
| 面试模拟训练 | AI 模拟面试对话练习 | 🚧 开发中 |

## 技术栈

- Python 3.10+
- DeepSeek API
- Rich（终端美化）
- python-dotenv（环境变量管理）
