import json
import re
from collections import defaultdict
import pathlib

# 获取项目根目录
project_root = pathlib.Path(__file__).parent.parent.resolve()

def merge_markdown_files(classified_file, data_file, output_file):
    """
    从 classified_file 中读取分类和仓库，并从 data_file 中补充描述。
    """
    # 1. 从 data.json 创建 description 的速查字典
    descriptions = {}
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            all_repos_by_lang = json.load(f)
        for lang, repos in all_repos_by_lang.items():
            for repo in repos:
                if 'full_name' in repo and 'description' in repo:
                    descriptions[repo['full_name']] = repo.get('description')
    except FileNotFoundError:
        print(f"错误: 未找到数据文件 {data_file}")
        return

    # 2. 解析分类文件
    categories = defaultdict(set) # 使用 set 自动去重
    current_category = None
    try:
        with open(classified_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('## '):
                    match = re.match(r'##\s*(.*?)\s*\(', line)
                    current_category = match.group(1).strip() if match else line.replace('##','').strip()
                elif line.startswith(('• ', '* ', '- ')):
                    if current_category:
                        categories[current_category].add(line)
    except FileNotFoundError:
        print(f"错误: 未找到分类文件 {classified_file}")
        return

    # 3. 重新生成包含描述的 Markdown
    with open(output_file, 'w', encoding='utf-8') as f:
        for category_name in sorted(categories.keys()):
            # 从 set 转换为 list 并排序
            repos = sorted(list(categories[category_name]))
            f.write(f"## {category_name} ({len(repos)} Repos)\n\n")
            
            for repo_line in repos:
                f.write(f"{repo_line}\n")
                # 从链接中提取 full_name
                match = re.search(r'\(https://github.com/([^)]+)\)', repo_line)
                if match:
                    full_name = match.group(1).strip('/')
                    # 查找并写入描述
                    description = descriptions.get(full_name)
                    if description:
                        f.write(f"> {description}\n")
                f.write("\n")

    print(f"合并完成！已将包含描述的结果写入 {output_file}")

if __name__ == "__main__":
    tmp_classified_path = project_root / 'classified_stars.md.tmp'
    final_classified_path = project_root / 'classified_stars.md'
    data_json_path = project_root / 'data.json'
    merge_markdown_files(tmp_classified_path, data_json_path, final_classified_path)
