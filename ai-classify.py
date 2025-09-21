import json
import subprocess
import os

# 您的分类指南，作为提示词的一部分
PROMPT_GUIDE = """
GitHub仓库分类指南

作为AI，当你收到一个GitHub仓库列表时，请根据以下指南对仓库进行分类。如果仓库不符合任何现有类别，请基于仓库内容创建新类别。输出应为完整的Markdown文档，包括所有类别和仓库信息。

现有类别及关键词

以下是预定义类别及其常见关键词，用于匹配仓库：
• 网页工具: 与Web开发、在线服务、浏览器扩展、前端/后端工具相关。关键词：web、前端、后端、浏览器、扩展、工具、在线、代理、监控、API、云服务、部署。

• 安卓app: 针对Android平台的应用程序。关键词：android、app、应用、移动、手机、播放器、下载器、工具、ROM、模块。

• fonts: 字体设计、字体库或字体相关工具。关键词：font、字体、typography、bitmap、像素字体。

• libs: 库、框架或开发工具。关键词：library、framework、库、框架、开发工具、SDK、API、组件。

• Minecraft: 与Minecraft游戏相关的项目。关键词：minecraft、游戏、服务器、插件、模组、启动器、联机。

• tg: 与Telegram相关的项目。关键词：telegram、tg、机器人、客户端、消息、聊天。

• qq: 与QQ或腾讯相关的项目。关键词：qq、腾讯、机器人、客户端、插件、QQ频道。

• magisk: 与Magisk相关的项目。关键词：magisk、root、模块、系统、优化、安全、刷机。

• lsposed: 与LSPosed或Xposed相关的项目。关键词：lsposed、xposed、模块、hook、注入、修改。

• themes: 主题、皮肤或UI定制相关。关键词：theme、主题、皮肤、UI、美化、定制。

分类规则

1. 读取仓库信息: 获取每个仓库的名称、描述、主要语言、星标数、作者和链接。
2. 关键词匹配: 根据描述中的关键词和仓库用途，匹配到最合适的现有类别。优先使用描述中的关键词，其次考虑语言和项目类型。
3. 创建新类别: 如果仓库不匹配任何现有类别，基于仓库内容创建新类别。新类别名称应简洁明了，反映仓库的主要用途（如“硬件”、“AI”、“游戏”等）。
4. 输出格式: 使用Markdown格式输出，每个类别以##开头，仓库列表使用无序列表（•），每个仓库包括名称（链接）、星标数、语言、作者和描述。

输出格式要求

对于每个类别，输出如下：
## 📂 类别名称 (数量 Repos)

• [`仓库名称`](仓库链接) ★星标数 — *主要语言* — _作者_

> 描述

"""

def call_gemini_cli(prompt_text):
    """
    通过 os.system 调用 Gemini CLI，并将输出重定向到临时文件，然后读取该文件。
    """
    gemini_cmd_path = r'C:\Users\LIPiston\AppData\Roaming\npm\gemini.cmd'
    output_tmp_file = 'gemini_output.tmp'
    
    # 为了防止 prompt_text 中的特殊字符（如 "）破坏命令，我们先将其写入一个临时文件
    prompt_tmp_file = 'prompt.tmp'
    try:
        with open(prompt_tmp_file, 'w', encoding='utf-8') as f:
            f.write(prompt_text)

        # 构建命令
        # 使用 type 命令读取 prompt 文件内容，并通过管道传给 gemini cli
        command = f'type "{prompt_tmp_file}" | "{gemini_cmd_path}" prompt > "{output_tmp_file}"'
        
        # 执行命令
        return_code = os.system(command)
        
        if return_code != 0:
            print(f"调用 Gemini CLI 失败，返回码: {return_code}")
            # 尝试读取错误输出（如果 gemini cli 将其输出到 stderr，os.system 无法直接捕获）
            # 这里我们只能给一个通用提示
            if os.path.exists(output_tmp_file):
                with open(output_tmp_file, 'r', encoding='utf-8') as f:
                    error_output = f.read()
                    if error_output:
                        print(f"Gemini CLI 可能的输出: {error_output}")
            return None

        # 读取输出文件
        with open(output_tmp_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
            
    except Exception as e:
        print(f"执行 Gemini CLI 时发生未知错误: {e}")
        return None
    finally:
        # 清理临时文件
        if os.path.exists(output_tmp_file):
            os.remove(output_tmp_file)
        if os.path.exists(prompt_tmp_file):
            os.remove(prompt_tmp_file)

def main():
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            all_repos_by_lang = json.load(f)
    except FileNotFoundError:
        print("错误：未找到 data.json 文件。请确保您的GitHub star数据已保存到该文件中。")
        return

    # 将所有语言的仓库合并到一个列表中
    all_repos = []
    for lang, repos in all_repos_by_lang.items():
        all_repos.extend(repos)

    chunk_size = 50  # 每个分块处理50个仓库
    all_chunks = [all_repos[i:i + chunk_size] for i in range(0, len(all_repos), chunk_size)]
    
    final_markdown = ""
    total_chunks = len(all_chunks)

    print(f"总共有 {len(all_repos)} 个仓库，将分 {total_chunks} 个批次进行处理...")

    # 清空或创建最终的输出文件
    with open('classified_stars.md', 'w', encoding='utf-8') as f:
        f.write("") # 写入空字符串以清空文件

    for i, chunk in enumerate(all_chunks):
        print(f"\n--- 正在处理批次 {i + 1}/{total_chunks} ---")
        
        # 为当前分块构建提示语
        # 注意：这里我们不再按语言分组，而是让AI对整个列表分类
        repo_list_json = json.dumps(chunk, indent=4)
        full_prompt = (
            PROMPT_GUIDE +
            "\n\n请严格按照上述指南对以下GitHub仓库列表进行分类并输出 Markdown 文档。不要添加任何额外的介绍或总结，只需输出分类好的 Markdown 列表：\n" +
            "```json\n" + repo_list_json + "\n```"
        )
        
        print(f"正在调用 Gemini CLI 处理 {len(chunk)} 个仓库...")
        
        # 调用 Gemini CLI
        markdown_output = call_gemini_cli(full_prompt)
        
        if markdown_output:
            # 将结果追加到文件
            with open('classified_stars.md', 'a', encoding='utf-8') as f:
                # 移除可能存在的 ```markdown 包装
                if markdown_output.startswith("```markdown"):
                    markdown_output = markdown_output[len("```markdown"):].strip()
                if markdown_output.endswith("```"):
                    markdown_output = markdown_output[:-len("```")].strip()
                
                f.write(markdown_output + "\n\n")
            print(f"批次 {i + 1} 处理完成。")
        else:
            print(f"批次 {i + 1} 处理失败，跳过此批次。")
            continue

    print("\n所有批次处理完成！结果已聚合到 classified_stars.md 文件中。")

if __name__ == "__main__":
    main()