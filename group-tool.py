import json
from pathlib import Path

# 文件名常量
DATA_FILE = 'data.json'
DEFAULT_CATEGORY_FILE = 'starflare_export.json'
OUTPUT_FILE = 'grouped.md'

# 检查数据文件
if not Path(DATA_FILE).is_file():
    print(f"❌ 未找到数据文件：{DATA_FILE}")
    exit(1)

# 尝试加载默认分类文件
category_path = Path(DEFAULT_CATEGORY_FILE)

if not category_path.is_file():
    user_input = input(f"⚠️ 未在当前目录找到 '{DEFAULT_CATEGORY_FILE}'，请输入分类文件路径： ").strip()
    category_path = Path(user_input)

    if not category_path.is_file():
        print(f"❌ 找不到你输入的文件：{category_path}")
        exit(1)

# 加载 data.json
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# 构建 repo_id -> repo 映射
repo_dict = {}
for lang, repos in raw_data.items():
    for repo in repos:
        repo_id = repo['id']
        repo_dict[repo_id] = repo

# 加载分类数据
with open(category_path, 'r', encoding='utf-8') as f:
    categories = json.load(f)

# 生成 Markdown 内容
lines = ["# 🌟 My Starred GitHub Repositories (Grouped by starflare.app)\n"]

for category in categories:
    cat_name = category['name']
    repo_ids = category['repos']
    lines.append(f"\n## 📂 {cat_name} ({len(repo_ids)} Repos)\n")

    for rid in repo_ids:
        repo = repo_dict.get(rid)
        if repo:
            name = repo['full_name']
            url = repo['html_url']
            desc_raw = repo.get('description')
            desc = (desc_raw or '').strip().replace('\n', ' ')
            stars = repo.get('stargazers_count', 0)
            owner = repo['owner']['login']
            lang = repo.get('language', 'Unknown')

            lines.append(f"- [`{name}`]({url}) ★{stars} — *{lang}* — _{owner}_")
            if desc:
                lines.append(f"  \n  > {desc}")
        else:
            lines.append(f"- ⚠️ Repo ID `{rid}` not found in data.json.")

# 写入文件
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"✅ Markdown 文件已生成：{OUTPUT_FILE}")
