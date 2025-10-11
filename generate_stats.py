import os
import re
import pathlib
import json
from urllib.parse import quote

def generate_stats():
    """
    遍历 categories 文件夹，统计仓库数量，验证数据完整性，并生成 README.md。
    """
    project_root = pathlib.Path(__file__).parent.resolve()
    categories_dir = project_root / 'categories'
    readme_path = categories_dir / 'README.md'
    data_json_path = project_root / 'stars.json'

    if not categories_dir.exists():
        print(f"错误: 目录 '{categories_dir}' 不存在。")
        return

    # --- 1. 从分类文件中统计仓库 ---
    category_stats = {}
    total_classified_repos = 0
    classified_repo_names = set()

    for md_file in sorted(categories_dir.glob('*.md')):
        if md_file.name == 'README.md':
            continue

        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 提取 full_name 以便后续比较
            found_repos = set(re.findall(r'\[`([^`]+)`\]\(https://github.com/([^)]+)\)', content))
            # found_repos is a set of tuples, e.g., {('repo-name', 'user/repo-name')}
            
            repo_count = len(found_repos)
            if repo_count > 0:
                category_name = md_file.stem
                category_stats[category_name] = {'count': repo_count, 'path': md_file.name}
                total_classified_repos += repo_count
                for _, full_name in found_repos:
                    classified_repo_names.add(full_name)

    # --- 2. 从 stars.json 加载源数据进行比对 ---
    try:
        with open(data_json_path, 'r', encoding='utf-8') as f:
            all_repos_by_lang = json.load(f)
        source_repo_names = {repo['full_name'] for repo in all_repos_by_lang}
    except (FileNotFoundError, json.JSONDecodeError):
        source_repo_names = set()
        print(f"警告: 无法加载或解析 {data_json_path}，跳过完整性检查。")

    missing_repos = source_repo_names - classified_repo_names
    
    # --- 3. 生成 README.md 内容 ---
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write("# AI 分类索引\n\n")
        f.write(f"> ✨ 目前总共分类了 **{total_classified_repos} / {len(source_repo_names)}** 个仓库。\n\n")
        f.write("## 目录\n\n")

        for category_name, stats in category_stats.items():
            f.write(f"- [{category_name}]({quote(stats['path'])}) - ({stats['count']} 个仓库)\n")
        
        f.write("\n---\n\n")
        f.write("## 数据完整性报告\n\n")

        if not missing_repos:
            f.write("✅ **数据完整**：所有在 `stars.json` 中的仓库都已成功分类。\n")
        else:
            f.write(f"⚠️ **发现 {len(missing_repos)} 个丢失的仓库！**\n\n")
            f.write("以下仓库存在于 `stars.json` 但未在任何分类文件中找到。请检查 `tools/classification_state.json` 并重新运行 `ai-classify.py` 来处理它们。\n\n")
            for repo_name in sorted(list(missing_repos)):
                f.write(f"- `{repo_name}`\n")

    print(f"统计完成！已生成索引文件: {readme_path}")
    if missing_repos:
        print(f"警告：发现 {len(missing_repos)} 个丢失的仓库。详情请查看 categories/README.md。")

if __name__ == "__main__":
    generate_stats()