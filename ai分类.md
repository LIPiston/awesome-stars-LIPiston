# AI 分类工具使用说明

本文档指导你如何使用工具对 `data.json` 中的 GitHub Star 项目进行自动分类。

## 准备工作

1.  **安装 Gemini CLI**:
    请根据官方文档[安装 Gemini CLI](https://google-gemini.github.io/gemini-cli/#-installation)，并完成 `Login with Google` 的身份验证。

2.  **准备数据 (`data.json`)**:
    - **来源**: `data.json` 文件是由本项目的 GitHub Action 自动生成的，包含了你最新的 GitHub Star 列表。
    - **本地运行**: 在分类前，请确保你已经从仓库拉取了最新的 `data.json` 文件。

3.  **配置自定义规则 (可选)**:
    - 你可以编辑根目录下的 `custom_rules.json` 文件来定义关键词和分类的映射。
    - **工作原理**: 脚本在调用 AI 之前，会先用这些规则进行匹配。如果匹配成功，它不会直接分类，而是将匹配到的类别作为一个“建议类别”提供给 AI。
    - **优势**: 这相当于你为 AI 提供了一个强有力的提示，引导它做出更符合你预期的分类，同时 AI 仍有机会根据它对仓库 `README` 的理解进行修正，实现了人机协同，达到最佳分类效果。

## 运行步骤

现在，整个分类过程只需要一个命令。

在项目根目录下，运行以下命令：
```bash
python tools/ai-classify.py
```

### 功能说明

- **自动分类**: 脚本会逐一处理 `data.json` 中的每个仓库，调用 AI 判断其类别。
- **动态生成文件**: 脚本会根据 AI 的分类结果，在 `categories` 文件夹下自动创建或追加内容到对应的 `.md` 文件中。例如，一个被分类为“网页工具”的仓库，其信息会被写入 `categories/网页工具.md`。
- **断点续传**: 脚本通过 `tools/classification_state.json` 文件来记录已处理的仓库。如果运行中途因网络或 API 限额问题中断，你只需**重新运行同一命令**，脚本就会自动从上次中断的地方继续，不会重复处理。

### 输出文件

- **`categories/` 文件夹**: 包含所有最终的分类文件，每个文件代表一个类别。
- **`tools/classification_state.json`**: 用于断点续传的状态文件。

### 如何完全重新分类?

如果你希望忽略进度，从零开始对所有仓库进行一次全新的分类，请在运行脚本前**手动删除**以下内容：
1.  `tools/classification_state.json` 文件。
2.  `categories` 文件夹下的所有 `.md` 文件。