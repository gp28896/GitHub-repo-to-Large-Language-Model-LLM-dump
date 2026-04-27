import requests
import base64
import os

# ===== CONFIG =====
OUTPUT_FILE = "repo_dump.txt"
INCLUDE_EXTENSIONS = {
    ".ipynb", ".py", ".js", ".ts", ".java", ".html", ".css", ".json", ".md", ".yaml", ".yml"
}
EXCLUDE_DIRS = {
    ".git", "node_modules", "venv", "__pycache__", "dist", "build"
}
MAX_FILE_SIZE = 200 * 1024  # 200 KB
GITHUB_API = "https://api.github.com"

# ==================

def is_valid_file(path):
    _, ext = os.path.splitext(path)
    return ext.lower() in INCLUDE_EXTENSIONS


def should_skip(path):
    return any(part in EXCLUDE_DIRS for part in path.split("/"))


def get_repo_tree(owner, repo, branch="main"):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    res = requests.get(url)
    res.raise_for_status()
    return res.json()["tree"]


def get_file_content(owner, repo, path):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    res = requests.get(url)
    res.raise_for_status()
    data = res.json()

    if data.get("encoding") == "base64":
        content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        return content
    return None


def generate_structure(tree):
    lines = ["===== REPO STRUCTURE ====="]
    for item in tree:
        if item["type"] == "blob":
            lines.append(item["path"])
    return "\n".join(lines)


def dump_repo(owner, repo, branch="main"):
    tree = get_repo_tree(owner, repo, branch)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        # Structure
        out.write(generate_structure(tree))

        out.write("\n\n===== FILE CONTENTS =====\n")

        for item in tree:
            if item["type"] != "blob":
                continue

            path = item["path"]

            if should_skip(path) or not is_valid_file(path):
                continue

            if item.get("size", 0) > MAX_FILE_SIZE:
                out.write(f"\n===== SKIPPED (TOO LARGE): {path} =====\n")
                continue

            try:
                content = get_file_content(owner, repo, path)
                if content:
                    out.write(f"\n===== FILE: {path} =====\n")
                    out.write(content + "\n")
            except Exception as e:
                out.write(f"\n===== ERROR: {path} =====\n{str(e)}\n")

    print(f"Dump created: {OUTPUT_FILE}")


if __name__ == "__main__":
    repo_url = input("Enter GitHub repo URL: ").strip()

    # Parse URL
    parts = repo_url.replace("https://github.com/", "").split("/")
    owner, repo = parts[0], parts[1]

    dump_repo(owner, repo)
