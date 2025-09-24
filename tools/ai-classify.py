import json
import subprocess
import os
import re
import pathlib
import time

# 获取项目根目录和工具目录
script_path = pathlib.Path(__file__).resolve()
tools_dir = script_path.parent
project_root = tools_dir.parent

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

1. **阅读README**: 在分类前，请访问每个仓库的 `html_url` 链接，并阅读其 `README.md` 文件的内容。这是分类的最重要参考。
2. 读取仓库信息: 获取每个仓库的名称、描述、主要语言、星标数、作者和链接。
3. 关键词匹配: 优先结合 `README.md` 内容和仓库描述中的关键词及用途，匹配到最合适的现有类别。
4. 创建新类别: 如果仓库不匹配任何现有类别，基于 `README.md` 和描述内容创建新类别。新类别名称应简洁明了。
5. 输出格式: 使用Markdown格式输出，每个类别以##开头，仓库列表使用无序列表（•），每个仓库包括名称（链接）、星标数、语言、作者和描述。

"""

def call_gemini_cli(prompt_text):
    """
    通过 os.system 调用 Gemini CLI，并将输出重定向到临时文件，然后读取该文件。
    """
    gemini_cmd_path = r'C:\Users\LIPiston\AppData\Roaming\npm\gemini.cmd'
    # 在 tools 文件夹内创建临时文件
    output_tmp_file = tools_dir / 'gemini_output.tmp'
    prompt_tmp_file = tools_dir / 'prompt.tmp'
    
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
    data_json_path = project_root / 'data.json'
    classified_stars_path = project_root / 'classified_stars.md.tmp'
    # 使用独立的状态文件
    state_file_path = tools_dir / 'classification_state.json'

    # 1. 加载状态文件，获取已处理的仓库
    processed_repos = set()
    if state_file_path.exists():
        try:
            with open(state_file_path, 'r', encoding='utf-8') as f:
                processed_repos = set(json.load(f))
            print(f"检测到状态文件，已加载 {len(processed_repos)} 个已处理的仓库。")
        except json.JSONDecodeError:
            print("警告: 状态文件为空或格式错误，将重新开始。")
            processed_repos = set()
    
    # 2. 从 data.json 加载所有仓库，并过滤
    try:
        with open(data_json_path, 'r', encoding='utf-8') as f:
            all_repos_by_lang = json.load(f)
    except FileNotFoundError:
        print(f"错误：未找到 {data_json_path} 文件。")
        return

    all_repos = [repo for lang_repos in all_repos_by_lang.values() for repo in lang_repos]
    pending_repos = [repo for repo in all_repos if repo.get('full_name') not in processed_repos]

    if not pending_repos:
        print("\n所有仓库均已分类，无需操作。")
        print(f"如需重新分类，请删除 {state_file_path} 和 {classified_stars_path}")
        return

    print(f"总共有 {len(all_repos)} 个仓库，其中 {len(pending_repos)} 个待分类。")

    # 3. 对待办仓库进行分块处理
    chunk_size = 20
    all_chunks = [pending_repos[i:i + chunk_size] for i in range(0, len(pending_repos), chunk_size)]
    total_chunks = len(all_chunks)

    print(f"将分 {total_chunks} 个批次进行处理...")

    for i, chunk in enumerate(all_chunks):
        print(f"\n--- 正在处理批次 {i + 1}/{total_chunks} ---")
        
        repo_list_json = json.dumps(chunk, indent=4)
        full_prompt = (
            PROMPT_GUIDE + 
            "\n\n请严格按照上述指南对以下GitHub仓库列表进行分类并输出 Markdown 文档。不要添加任何额外的介绍或总结，只需输出分类好的 Markdown 列表：\n" +
            "```json\n" + repo_list_json + "\n```"
        )
        
        print(f"正在调用 Gemini CLI 处理 {len(chunk)} 个仓库...")
        
        markdown_output = call_gemini_cli(full_prompt)
        
        if markdown_output:
            # 以追加模式写入文件
            with open(classified_stars_path, 'a', encoding='utf-8') as f:
                if markdown_output.startswith("```markdown"):
                    markdown_output = markdown_output[len("```markdown"):].strip()
                if markdown_output.endswith("```"):
                    markdown_output = markdown_output[:-len("```")].strip()
                
                f.write(markdown_output + "\n\n")
            print(f"批次 {i + 1} 处理完成。")
            # 在两次请求之间加入延迟，以避免达到速率限制
            print("等待 10 秒钟...")
            time.sleep(10)
        else:
            print(f"批次 {i + 1} 处理失败，请检查错误并手动重新运行。")
            # 由于不再有断点续传，遇到失败就直接退出
            return

    print("\n所有批次处理完成！结果已写入 classified_stars.md.tmp 文件中。")

if __name__ == "__main__":
    main()