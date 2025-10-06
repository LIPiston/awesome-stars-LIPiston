import json
import os
import re
import pathlib
import time
import shutil
import subprocess
import sys

# --- Setup Paths ---
script_path = pathlib.Path(__file__).resolve()
tools_dir = script_path.parent
project_root = tools_dir.parent
categories_dir = project_root / 'categories'
data_json_path = project_root / 'data.json'
state_file_path = tools_dir / 'classification_state.json'
rules_file_path = project_root / 'custom_rules.json'

# --- AI Prompt Guide ---
PROMPT_GUIDE = """
你是一个精准的 GitHub 仓库分类助手。
你的任务是根据我提供的仓库信息和建议类别，为**每一个**仓库分配一个最合适的最终类别。

# 现有类别
- 网页工具
- 安卓app
- fonts
- rime
- Minecraft
- tg
- qq
- magisk
- lsposed
- themes
- AI工具
- Awesome List
- CLI工具
- 桌面应用
- 游戏

# 分类规则
1.  **参考建议**: 我可能会在每个仓库信息中提供一个“建议类别”。请优先考虑这个建议。
2.  **阅读README**: 访问 `html_url`，阅读 `README.md` 内容，这是最重要的参考。
3.  **综合判断**: 结合建议类别、README内容和仓库元数据，做出最专业的判断。
4.  **最重要：你的回答必须是一个 JSON 数组，每个元素是一个对象，包含 `full_name` 和 `category` 两个键。不要包含任何其他文字或解释。**

# JSON 输出格式示例
[
  {
    "full_name": "user/repo1",
    "category": "网页工具"
  }
]
"""

def call_gemini_cli(prompt_text):
    """
    通过 os.system 调用 Gemini CLI，并将 stdout 和 stderr 都重定向到临时文件。
    """
    gemini_executable = shutil.which('gemini')
    if not gemini_executable:
        return None, "Gemini_Not_Found"

    output_tmp_file = tools_dir / 'gemini_output.tmp'
    prompt_tmp_file = tools_dir / 'prompt.tmp'
    
    try:
        with open(prompt_tmp_file, 'w', encoding='utf-8') as f:
            f.write(prompt_text)
        
        command = f'type "{prompt_tmp_file}" | "{gemini_executable}" prompt --output-format json 1> "{output_tmp_file}" 2>&1'
        
        os.system(command)
        
        if not os.path.exists(output_tmp_file):
            return None, "No_Output_File"

        with open(output_tmp_file, 'r', encoding='utf-8') as f:
            raw_output = f.read().strip()
        
        if not raw_output:
            return None, "Empty_Output"

        try:
            # 尝试直接解析
            json.loads(raw_output)
            return raw_output, None # 如果成功，返回原始JSON文本
        except json.JSONDecodeError as e:
            # 如果直接解析失败，尝试提取
            json_match = re.search(r'\[.*\]', raw_output, re.DOTALL)
            if json_match:
                try:
                    # 验证提取的部分是否是有效的JSON
                    json.loads(json_match.group(0))
                    return json_match.group(0), None
                except json.JSONDecodeError:
                    # 提取了但仍然不是有效的JSON，返回整个原始输出作为错误
                    return None, f"Extracted_But_Invalid_JSON: {raw_output}"
            else:
                # 如果连提取都失败了，返回整个原始输出作为错误
                return None, f"No_JSON_Found: {raw_output}"
            
    except Exception as e:
        return None, f"Python_Exception: {e}"
    finally:
        if os.path.exists(output_tmp_file):
            os.remove(output_tmp_file)
        if os.path.exists(prompt_tmp_file):
            os.remove(prompt_tmp_file)

def write_repo_to_category_file(repo, category_name):
    # ... (此函数保持不变)
    try:
        safe_category_name = "".join(c for c in category_name if c.isalnum() or c in " -").strip()
        if not safe_category_name: return False
        category_file = categories_dir / f"{safe_category_name}.md"
        if not category_file.exists():
            with open(category_file, 'w', encoding='utf-8') as f: f.write(f"# {category_name}\n\n")
        repo_name, repo_url, repo_stars, repo_lang, repo_owner, repo_desc = (repo.get(k, '') for k in ['name', 'html_url', 'stargazers_count', 'language', 'owner', 'description'])
        if isinstance(repo_owner, dict): repo_owner = repo_owner.get('login', '')
        markdown_entry = f"## [`{repo_name}`]({repo_url}) ★{repo_stars} - _{repo_lang}_ - @{repo_owner}\n> {repo_desc if repo_desc else '暂无描述。'}\n\n"
        with open(category_file, 'a', encoding='utf-8') as f: f.write(markdown_entry)
        return True
    except Exception: return False

def main():
    if not shutil.which('gemini'):
        print("错误：在系统的 PATH 环境变量中找不到 'gemini' 命令。")
        sys.exit(1)

    # ... (加载规则、状态、数据的逻辑保持不变)
    custom_rules, processed_repos, all_repos, pending_repos_names = {}, set(), {}, []
    if rules_file_path.exists():
        try:
            with open(rules_file_path, 'r', encoding='utf-8') as f: custom_rules = json.load(f)
        except json.JSONDecodeError: pass
    if state_file_path.exists():
        try:
            with open(state_file_path, 'r', encoding='utf-8') as f: processed_repos = set(json.load(f))
        except (json.JSONDecodeError, FileNotFoundError): pass
    try:
        with open(data_json_path, 'r', encoding='utf-8') as f: all_repos_by_lang = json.load(f)
        all_repos = {repo['full_name']: repo for lang_repos in all_repos_by_lang.values() for repo in lang_repos}
        pending_repos_names = [name for name in all_repos.keys() if name not in processed_repos]
    except FileNotFoundError:
        print(f"错误：未找到 {data_json_path} 文件。"); return
    
    if not pending_repos_names: print("\n所有仓库均已分类。"); return
    print(f"总共有 {len(all_repos)} 个仓库，其中 {len(pending_repos_names)} 个待分类。")

    repos_to_ask_ai = []
    for name in pending_repos_names:
        repo = all_repos[name]
        text = f"{repo.get('name','')} {repo.get('description','')} {' '.join(repo.get('topics',[]))}".lower()
        matched = False
        for category, keywords in custom_rules.items():
            if any(kw.lower() in text for kw in keywords):
                if write_repo_to_category_file(repo, category): processed_repos.add(name); matched = True
                break
        if not matched: repos_to_ask_ai.append(repo)
    with open(state_file_path, 'w', encoding='utf-8') as f: json.dump(list(processed_repos), f)

    chunk_size = 10
    ai_chunks = [repos_to_ask_ai[i:i + chunk_size] for i in range(0, len(repos_to_ask_ai), chunk_size)]
    
    for i, chunk in enumerate(ai_chunks):
        print(f"\n--- 正在处理 AI 批次 {i + 1}/{len(ai_chunks)} ---")
        batch_data = []
        for repo in chunk:
            s_cat = next((cat for cat, kws in custom_rules.items() if any(kw.lower() in f"{repo.get('name','')} {repo.get('description','')} {' '.join(repo.get('topics',[]))}".lower() for kw in kws)), None)
            info = {k: repo.get(k) for k in ['full_name', 'name', 'description', 'topics', 'language', 'html_url']}
            if s_cat: info["suggested_category"] = s_cat
            batch_data.append(info)
        
        prompt = f"{PROMPT_GUIDE}\n\n# 待分类的仓库列表:\n```json\n{json.dumps(batch_data, indent=2)}\n```\n\n请严格按照 JSON 数组格式返回所有仓库的分类结果。"
        
        ai_result_text, err_msg = call_gemini_cli(prompt)
        
        if err_msg:
            print(f"调用 Gemini CLI 时捕获到错误: \n---\n{err_msg}\n---")
        elif ai_result_text:
            try:
                classified_chunk = json.loads(ai_result_text)
                for item in classified_chunk:
                    repo_name, category_name = item.get("full_name"), item.get("category")
                    if repo_name in all_repos and category_name:
                        if write_repo_to_category_file(all_repos[repo_name], category_name):
                             processed_repos.add(repo_name)
            except json.JSONDecodeError as e:
                print(f"最终解析AI返回的JSON失败: {e}")
        
        with open(state_file_path, 'w', encoding='utf-8') as f: json.dump(list(processed_repos), f)
        print(f"批次 {i + 1} 处理完成，等待 10 秒...")
        time.sleep(10)
            
    print("\n所有待办仓库处理完成！")

if __name__ == "__main__":
    main()