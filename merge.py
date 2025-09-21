import re
from collections import defaultdict

def merge_markdown_files(input_file, output_file):
    """
    合并和去重 Markdown 文件中的类别和仓库。
    """
    categories = defaultdict(list)
    current_category = None

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('## '):
                # 匹配类别标题，例如 ## 📂 网页工具 (15 Repos)
                match = re.match(r'##\s*(.*?)\s*\(', line)
                if match:
                    current_category = match.group(1).strip()
                else:
                    current_category = line.replace('##','').strip()

            elif line.startswith('• '):
                if current_category:
                    # 添加仓库条目，避免重复
                    if line not in categories[current_category]:
                        categories[current_category].append(line)

    # 重新生成排序和合并后的 Markdown
    with open(output_file, 'w', encoding='utf-8') as f:
        # 按类别名称排序
        for category_name in sorted(categories.keys()):
            repos = categories[category_name]
            # 更新仓库数量
            f.write(f"## {category_name} ({len(repos)} Repos)\n\n\n")
            # 对仓库进行排序，确保一致性
            for repo_line in sorted(repos):
                f.write(f"{repo_line}\n\n")
            f.write("\n")

    print(f"合并完成！已将结果写入 {output_file}")

if __name__ == "__main__":
    merge_markdown_files('classified_stars.md', 'classified_stars.md')
