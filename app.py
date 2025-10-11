from nicegui import ui, app
import json
import os
import re
import pathlib
import time
import shutil
import subprocess
import sys
import random
import asyncio

# --- Core Logic & Setup ---
app_path = pathlib.Path(__file__).parent.resolve()
categories_dir = app_path / 'categories'
data_json_path = app_path / 'stars.json'
state_file_path = app_path / 'classification_state.json' 

all_repos, pending_repos, processed_repos = {}, [], set()
app.state.selected_list = []
app.state.candidate_list = []

def call_gemini_cli(prompt_text):
    print("-> call_gemini_cli: a new call")
    gemini_executable = shutil.which('gemini')
    if not gemini_executable:
        print("[ERROR] Gemini CLI not found in PATH.")
        return None, "Gemini_Not_Found"
    
    print(f"Gemini executable found at: {gemini_executable}")

    try:
        process = subprocess.run(
            [gemini_executable, "prompt"],
            input=prompt_text,
            capture_output=True,
            text=True,
            encoding='utf-8',
            shell=True
        )
        
        stdout = process.stdout.strip()
        stderr = process.stderr.strip()

        if process.returncode != 0:
            print(f"[ERROR] Gemini CLI failed with return code {process.returncode}")
            print(f"[ERROR] Stderr: {stderr}")
            return None, f"Gemini_CLI_Error: {stderr}"

        if not stdout:
            print("[ERROR] Gemini CLI returned empty output.")
            return None, "Empty_Output"
        
        print(f"Gemini CLI successful. Raw output: {stdout}")
        return stdout, None

    except Exception as e:
        print(f"[ERROR] An exception occurred in call_gemini_cli: {e}")
        return None, f"Python_Exception: {e}"

def write_repo_to_category_file(repo, category_name):
    try:
        safe_category_name = re.sub(r'[\\/*?:"<>|]', "", category_name).strip()
        if not safe_category_name:
            print(f"[ERROR] Category name '{category_name}' became empty after sanitization.")
            return False
        
        category_file = categories_dir / f"{safe_category_name}.md"
        print(f"Attempting to write to category file: {category_file}")

        is_new_file = not category_file.exists()
        if is_new_file:
            print(f"Creating new category file: {category_file}")
            with open(category_file, 'w', encoding='utf-8') as f: f.write(f"# {category_name}\n\n")
        
        repo_name, repo_url, repo_stars, repo_lang, repo_owner, repo_desc = (repo.get(k, '') for k in ['name', 'html_url', 'stargazers_count', 'language', 'owner', 'description'])
        if isinstance(repo_owner, dict): repo_owner = repo_owner.get('login', '')
        markdown_entry = f"## [`{repo_name}`]({repo_url}) ★{repo_stars} - _{repo_lang}_ - @{repo_owner}\n> {repo_desc if repo_desc else '暂无描述。'}\n\n"
        
        with open(category_file, 'a', encoding='utf-8') as f: f.write(markdown_entry)
        print(f"Successfully appended '{repo_name}' to {category_file}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write to category file {category_file}: {e}")
        return False

def load_data():
    global all_repos, pending_repos, processed_repos
    print("--- Loading data ---")
    os.makedirs(categories_dir, exist_ok=True)
    print(f"Ensured 'categories' directory exists at: {categories_dir}")

    if state_file_path.exists():
        try:
            with open(state_file_path, 'r', encoding='utf-8') as f: processed_repos = set(json.load(f))
            print(f"Loaded {len(processed_repos)} processed repos from state file.")
        except Exception as e:
            print(f"[WARNING] Could not load state file: {e}")
            processed_repos = set()
    
    try:
        with open(data_json_path, 'r', encoding='utf-8') as f: all_repos_by_lang = json.load(f)
        all_repos = {repo['full_name']: repo for repo in all_repos_by_lang}
        pending_repos = [repo for repo in all_repos.values() if repo.get('full_name') not in processed_repos]
        random.shuffle(pending_repos)
        print(f"Loaded {len(all_repos)} total repos.")
        print(f"Found {len(pending_repos)} pending repos.")
    except Exception as e:
        print(f"[ERROR] Could not load stars.json: {e}")
        all_repos, pending_repos = {}, []
    print("--- Data loading complete ---")

def get_categories_snapshot(max_chars_per_file: int = 800):
    """读取 `categories` 目录中每个 md 文件的前若干字符，并返回一个结构化的字符串快照。

    目的：在构造 AI prompt 时附带现有分类文件的摘要，帮助 AI 避免重复或生成不一致的类别名。
    """
    try:
        if not categories_dir.exists():
            return "(categories 目录为空)"
        parts = []
        for md in sorted(categories_dir.glob('*.md')):
            try:
                text = md.read_text(encoding='utf-8')
            except Exception:
                continue
            # 取文件名（不含扩展）和前若干字符作为摘要
            name = md.stem
            snippet = text.replace('\n', ' ')[:max_chars_per_file].strip()
            parts.append(f"文件: {name}.md\n摘要: {snippet}\n---\n")
        if not parts:
            return "(categories 目录为空)"
        return "\n".join(parts)
    except Exception as e:
        print(f"[WARNING] 无法读取 categories 快照: {e}")
        return "(无法读取 categories)"

# --- UI ---
@ui.page('/')
async def main_page():
    
    def update_ui():
        stats_label.set_text(f"总条目: {len(all_repos)} | 已分类: {len(processed_repos)} | 待分类: {len(pending_repos)}")
        selected_view.clear()
        with selected_view:
            ui.label(f"已选列表 ({len(app.state.selected_list)} 个)").classes('text-lg font-bold')
            for repo in app.state.selected_list:
                with ui.row().classes('w-full items-center'):
                    ui.label(repo['full_name']).classes('flex-grow')
                    ui.button('移除', on_click=lambda r=repo: remove_from_selection(r), color='red').props('flat round dense')
        
        candidate_view.clear()
        search_term = search_input.value.lower() if search_input.value else ""
        
        filtered_candidates = [
            repo for repo in app.state.candidate_list 
            if not search_term or search_term in repo['full_name'].lower() or (repo.get('description') and search_term in repo.get('description', '').lower())
        ]

        with candidate_view:
            if not app.state.candidate_list and not pending_repos:
                 ui.label("所有条目都已分类！🎉").classes('text-h6 text-green-500')
            
            for repo in filtered_candidates:
                with ui.card().classes('w-full'):
                    with ui.row().classes('w-full justify-between items-center'):
                        with ui.column().classes('gap-0'):
                            ui.link(repo['full_name'], target=repo['html_url'], new_tab=True).classes('font-semibold')
                            ui.label(repo.get('description', 'No description')).classes('text-xs text-gray-500')
                        ui.button('选择', on_click=lambda r=repo: add_to_selection(r), color='green').props('flat round dense')

    def refresh_candidates():
        search_term = search_input.value.lower() if search_input.value else ""
        
        if not pending_repos:
            app.state.candidate_list = []
            ui.notify("所有仓库都已分类！")
        elif search_term:
            # If there's a search term, search the entire pending list
            print(f"Refreshing with search term: '{search_term}'")
            matching_repos = [
                repo for repo in pending_repos
                if search_term in repo['full_name'].lower() or (repo.get('description') and search_term in repo.get('description', '').lower())
            ]
            app.state.candidate_list = matching_repos[:50] # Show up to 50 matches
            ui.notify(f"找到 {len(matching_repos)} 个匹配项，已显示前 {len(app.state.candidate_list)} 个。")
        else:
            # Otherwise, get a random sample
            print("Refreshing with random sample.")
            app.state.candidate_list = random.sample(pending_repos, k=min(50, len(pending_repos)))
        
        update_ui()

    def add_to_selection(repo):
        if repo in pending_repos:
            pending_repos.remove(repo)
        if repo in app.state.candidate_list:
            app.state.candidate_list.remove(repo)
        app.state.selected_list.append(repo)
        update_ui()

    def remove_from_selection(repo):
        if repo in app.state.selected_list:
            app.state.selected_list.remove(repo)
            pending_repos.append(repo)
            update_ui()

    async def process_selection():
        print("\n--- Processing selection ---")
        if not app.state.selected_list:
            print("Selection list is empty. Aborting.")
            ui.notify("已选列表是空的！", color='warning'); return
        
        direction = direction_input.value
        if not direction:
            print("Direction not provided. Aborting.")
            ui.notify("请输入一个分类方向！", color='warning'); return

        print(f"Direction: '{direction}'")
        print(f"Selected repos: {[r['full_name'] for r in app.state.selected_list]}")

        # 获取 categories 文件夹快照，限制为较短摘要以避免过长 prompt
        categories_snapshot = get_categories_snapshot(500)

        prompt = (
            f"下面是当前项目中 'categories' 目录下各分类文件的摘要（文件名与前若干字符），用于帮助避免生成重复或不一致的分类名称：\n\n"
            f"{categories_snapshot}\n\n"
            f"这几个仓库是同一类别，分类方向是 '{direction}'。请结合你对这些仓库 README 的理解，以及上面已存在的分类文件内容，给出一个最精准且不与现有分类冲突的最终类别名称。只返回类别名称，不要包含标点或代码格式。\n\n"
        )
        for repo in app.state.selected_list:
            prompt += f"- {repo['full_name']}: {repo.get('description')}\n  URL: {repo.get('html_url')}\n"
        
        ui.notify("已提交给 AI，正在后台处理...")
        print("Submitting to AI...")
        name_button.disable()
        category_name, err = await asyncio.to_thread(call_gemini_cli, prompt)
        name_button.enable()

        if err or not category_name:
            print(f"AI naming failed. Error: {err or 'Empty response'}")
            ui.notify(f"AI 命名失败: {err or '返回为空'}", color='negative'); return
            
        category_name = category_name.strip().replace('`', '').replace('"', '')
        print(f"AI returned category name: '{category_name}'")
        ui.notify(f"AI 已命名为 '{category_name}'，正在写入文件...", color='positive')

        successful_writes = 0
        for repo in app.state.selected_list:
            if write_repo_to_category_file(repo, category_name):
                processed_repos.add(repo['full_name'])
                successful_writes += 1
            else:
                ui.notify(f"写入 {repo['full_name']} 到文件失败！", color='negative')
        
        if successful_writes > 0:
            print(f"Successfully wrote {successful_writes} repos to category '{category_name}'.")
            print("Updating state file...")
            with open(state_file_path, 'w', encoding='utf-8') as f: json.dump(list(processed_repos), f)
            print("State file updated.")
        
        app.state.selected_list.clear()
        refresh_candidates()
        print("--- Processing complete ---")

    # --- Page Layout ---
    with ui.splitter(value=70).classes('w-full h-[98vh]') as splitter:
        with splitter.before:
            with ui.column().classes('w-full h-full p-4 gap-2'):
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('待选列表').classes('text-h4')
                    search_input = ui.input(placeholder='搜索...', on_change=update_ui).props('dense clearable').classes('flex-grow')
                    ui.button('刷新', on_click=refresh_candidates).props('icon=refresh')
                stats_label = ui.label()
                with ui.scroll_area().classes('w-full grow'):
                    candidate_view = ui.column().classes('w-full gap-2')
        with splitter.after:
            with ui.column().classes('w-full h-full p-4 gap-4'):
                selected_view = ui.column()
                direction_input = ui.input(label="分类方向/提示", placeholder="例如：Minecraft 模组")
                name_button = ui.button('让 AI 命名此分组', on_click=process_selection).props('color=primary')

    # --- Initial Load ---
    load_data()
    refresh_candidates()

ui.run()