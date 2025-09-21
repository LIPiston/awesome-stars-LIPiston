import json
import re

def find_missing_repos():
    """
    比较 data.json 和 classified_stars.md，找出丢失的仓库。
    """
    # 1. 从 data.json 中提取所有仓库的 full_name
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            all_repos_by_lang = json.load(f)
        
        source_repos = set()
        for lang, repos in all_repos_by_lang.items():
            for repo in repos:
                if 'full_name' in repo:
                    source_repos.add(repo['full_name'])
        
        print(f"源文件 data.json 中共有 {len(source_repos)} 个唯一仓库。")

    except FileNotFoundError:
        print("错误：未找到 data.json 文件。")
        return

    # 2. 从 classified_stars.md 中提取所有已分类的仓库 full_name
    try:
        with open('classified_stars.md', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 正则表达式直接从URL中捕获 full_name
        # 例如: [Some Repo](https://github.com/user/repo) -> 提取 'user/repo'
        classified_repos = set(re.findall(r'\(https://github.com/([^)]+)\)', content))
        
        print(f"分类文件 classified_stars.md 中共有 {len(classified_repos)} 个唯一仓库。")

    except FileNotFoundError:
        print("错误：未找到 classified_stars.md 文件。")
        return

    # 3. 计算差集
    missing_repos = source_repos - classified_repos
    
    if not missing_repos:
        print("\n恭喜！没有发现丢失的仓库。")
    else:
        print(f"\n诊断完成！发现 {len(missing_repos)} 个丢失的仓库。")
        
        # 4. 将丢失的仓库列表写入文件
        with open('missing_repos.txt', 'w', encoding='utf-8') as f:
            f.write("以下仓库存在于 data.json 但未在 classified_stars.md 中找到：\n")
            f.write("="*60 + "\n")
            for repo_name in sorted(list(missing_repos)):
                f.write(f"{repo_name}\n")
        
        print("详细列表已保存到 missing_repos.txt 文件中，请查看。")


if __name__ == "__main__":
    find_missing_repos()