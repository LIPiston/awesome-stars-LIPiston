# AI 分类工具使用说明

本文档指导你如何使用工具对 `data.json` 中的 GitHub Star 项目进行自动分类。

## 准备工作

1.  **安装 Gemini CLI**:
    请根据官方文档[安装 Gemini CLI](https://google-gemini.github.io/gemini-cli/#-installation)，并完成 `Login with Google` 的身份验证。

2.  **准备数据 (`data.json`)**:
    - **来源**: `data.json` 文件是由本项目 `.github/workflows/star-list.yml` 中配置的 GitHub Action 自动生成的。该流程会定时（每天）或在代码推送时触发，获取你最新的 GitHub Star 列表，并将其保存为 `data.json`。
    - **手动更新**: 如果你需要立即获取最新的 Star 列表，可以手动触发 GitHub Actions 中的 `Update-stars-list` 工作流。
    - **本地运行**: 在本地运行分类前，请确保你已经从仓库拉取了最新的 `data.json` 文件。

## 运行步骤

分类过程分为两步，请按顺序执行。

### 步骤 1: 运行 AI 分类 (支持断点续传)

此步骤会调用 Gemini CLI 对 `data.json` 中的仓库进行分批处理和分类。

在项目根目录下，运行以下命令：
```bash
python tools/ai-classify.py
```

**功能说明**:
- **断点续传**: 脚本通过 `tools/classification_state.json` 文件记录进度。如果运行中断（例如因为网络问题或 API 速率限制），你只需重新运行此命令，脚本就会自动从上次中断的地方继续。
- **API 速率限制**: 脚本内置了延迟以应对 API 限制，但如果仍然遇到错误，请等待片刻后重新运行即可。
- **输出**: 此步骤会生成或追加内容到 `classified_stars.md.tmp` 文件。

### 步骤 2: 合并与最终生成

当 `ai-classify.py` 提示“所有仓库均已分类”后，执行此最后一步。它会整理临时文件，合并重复类别，并补充描述。

在项目根目录下，运行以下命令：
```bash
python tools/merge.py
```
完成后，`classified_stars.md` 文件将被创建或更新为一个干净、有序且包含完整信息的最终版本。

## 输出文件

- **`classified_stars.md`**: 这是最终生成的、分类好的 Markdown 文件，你可以直接使用。
- **`classified_stars.md.tmp`**: 分类脚本的原始输出，可用于调试 `merge.py` 是否丢失仓库。
- **`tools/classification_state.json`**: 状态记录文件。

**如何完全重新分类?**

如果你想从零开始一个全新的分类，请在运行**步骤 1**之前，手动删除以下两个文件：
1.  `classified_stars.md.tmp`
2.  `tools/classification_state.json`