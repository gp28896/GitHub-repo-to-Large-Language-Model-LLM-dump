import requests
import base64
import os
import sys

# ===== CONFIG =====
OUTPUT_FILE = "repo_dump.txt"
# INCLUDE_EXTENSIONS = {
#     ".ipynb", ".py", ".js", ".ts", ".java", ".html", ".css", ".json", ".md", ".yaml", ".yml"
# }
INCLUDE_EXTENSIONS = {
# Common programming languages
".py", ".pyw", ".pyx", ".pyi", ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx",
".java", ".class", ".kt", ".kts", ".scala", ".sc", ".groovy", ".groovy", ".swift", ".m", ".mm",
".rs", ".go", ".erl", ".ex", ".exs", ".elm", ".hs", ".jl", ".pm", ".pl", ".t", ".r",
".dart", ".ipynb",

# Web / frontend
".html", ".htm", ".xhtml", ".css", ".scss", ".sass", ".less", ".js", ".mjs", ".cjs", ".ts", ".tsx",
".jsx", ".vue", ".svelte", ".astro",

# Markup / docs / text
".txt", ".md", ".markdown", ".rst", ".adoc", ".asciidoc", ".docx", ".odt", ".rtf",

# Config / data / serialization
".json", ".json5", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".props", ".env", ".csv", ".tsv",

# Build / package / lockfiles
"package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Pipfile", "Pipfile.lock",
"requirements.txt", "setup.py", "pyproject.toml", "Makefile", "CMakeLists.txt", "Gemfile", "Gemfile.lock",

# Shell / scripts
".sh", ".bash", ".zsh", ".fish", ".ps1", ".psm1", ".cmd", ".bat",

# SQL / DB
".sql", ".psql", ".pgsql", ".sqlite", ".db", ".dml",

# Templates
".tpl", ".tmpl", ".jinja", ".j2", ".ejs", ".hbs", ".mustache", ".liquid", ".erb",

# Logs / telemetry
".log",

# Binary-not-plain but editable with hex/text editors (include common text-editable formats)
".pem", ".key", ".crt", ".csr", ".der",

# Image metadata / icons / SVG (SVG is XML text)
".svg", ".ico",

# Shell scripting / make / docker
"Dockerfile", ".dockerfile", ".dockerignore", ".k8s", ".kube", "kustomization.yaml", "helm-chart.yaml",

# CI / CI configs
".github", ".gitlab-ci.yml", ".circleci", ".travis.yml", ".azure-pipelines.yml", ".jenkinsfile",

# License / legal
"LICENSE", "LICENSE.md", "COPYING", "NOTICE", "CODE\_OF\_CONDUCT.md",

# Editors / project files (text-editable)
".vscode", ".editorconfig", ".sln", ".csproj", ".suo", ".proj", ".projitems",

# .NET / C#
".cs", ".fs", ".vb",

# JavaScript package managers / lockfiles already included; other files:
".esm", ".cjs",

# Mobile
".xml", ".plist", ".gradle", ".gradle.kts", ".keystore", ".apk" ,

# Binary/executable names that are text-editable configs
".service", ".socket", ".target",

# Misc scripting / templating / DSLs
".psv", ".ttl", ".rdf", ".dot", ".gv", ".graphql", ".gql",

# Fonts/encoding text-based
".ttf", ".otf", ".woff", ".woff2",

# Package manifests / descriptors
".nuspec", ".pom", ".pom.xml",

# Misc
".mdx", ".bib", ".tex", ".sty", ".cls", ".makefile",

# Include common hidden config names
".gitignore", ".gitattributes", ".env.example",

# Ensure basic extensions from original set remain
".ipynb", ".py", ".js", ".ts", ".java", ".html", ".css", ".json", ".md", ".yaml", ".yml"

}
EXCLUDE_DIRS = {
    ".git", "node_modules", "venv", "__pycache__", "dist", "build"
}
MAX_FILE_SIZE = 200 * 1024  # 200 KB
GITHUB_API = "https://api.github.com"
# ==================

# Optional token support (set GITHUB_TOKEN env var)
HEADERS = {}
_token = os.getenv("GITHUB_TOKEN")
if _token:
    HEADERS["Authorization"] = f"token {_token}"


def is_valid_file(path):
    _, ext = os.path.splitext(path)
    return ext.lower() in INCLUDE_EXTENSIONS


def should_skip(path):
    return any(part in EXCLUDE_DIRS for part in path.split("/"))


def get_default_branch(owner, repo):
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return res.json().get("default_branch", "main")


def get_repo_tree(owner, repo, branch="main"):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return res.json().get("tree", [])


def get_file_content(owner, repo, path):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    data = res.json()

    if data.get("encoding") == "base64" and "content" in data:
        content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")
        return content
    # For raw blobs (rare via this endpoint) or missing content return None
    return None


def generate_structure(tree):
    lines = ["===== REPO STRUCTURE ====="]
    for item in tree:
        if item.get("type") == "blob":
            lines.append(item.get("path", ""))
    return "\n".join(lines)


def sanitize_repo_parts(url):
    url = url.strip()
    # Remove possible .git and trailing slash
    if url.endswith(".git"):
        url = url[:-4]
    url = url.rstrip("/")
    # Accept URLs like "https://github.com/owner/repo" or "owner/repo"
    if url.startswith("https://github.com/"):
        url = url.replace("https://github.com/", "")
    if url.startswith("http://github.com/"):
        url = url.replace("http://github.com/", "")
    parts = url.split("/")
    if len(parts) < 2:
        raise ValueError("Invalid GitHub repo URL or path. Expected owner/repo.")
    return parts[0], parts[1]


def dump_repo(owner, repo, branch=None):
    try:
        if not branch:
            branch = get_default_branch(owner, repo)
    except requests.exceptions.HTTPError as e:
        print(f"Failed to get repo metadata: {e}", file=sys.stderr)
        if e.response is not None:
            print(f"Response status: {e.response.status_code}", file=sys.stderr)
            try:
                print(e.response.json(), file=sys.stderr)
            except Exception:
                print(e.response.text, file=sys.stderr)
        return

    try:
        tree = get_repo_tree(owner, repo, branch)
    except requests.exceptions.HTTPError as e:
        print(f"Failed to get repo tree for branch '{branch}': {e}", file=sys.stderr)
        if e.response is not None:
            print(f"Response status: {e.response.status_code}", file=sys.stderr)
            try:
                print(e.response.json(), file=sys.stderr)
            except Exception:
                print(e.response.text, file=sys.stderr)
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        out.write(generate_structure(tree))
        out.write("\n\n===== FILE CONTENTS =====\n")

        for item in tree:
            if item.get("type") != "blob":
                continue

            path = item.get("path", "")
            if not path:
                continue

            if should_skip(path) or not is_valid_file(path):
                continue

            if item.get("size", 0) > MAX_FILE_SIZE:
                out.write(f"\n===== SKIPPED (TOO LARGE): {path} =====\n")
                continue

            try:
                content = get_file_content(owner, repo, path)
                if content is not None:
                    out.write(f"\n===== FILE: {path} =====\n")
                    out.write(content + "\n")
                else:
                    out.write(f"\n===== SKIPPED (NO CONTENT): {path} =====\n")
            except requests.exceptions.HTTPError as e:
                out.write(f"\n===== ERROR HTTP: {path} =====\n{e}\n")
                if e.response is not None:
                    try:
                        out.write(str(e.response.json()) + "\n")
                    except Exception:
                        out.write(e.response.text + "\n")
            except Exception as e:
                out.write(f"\n===== ERROR: {path} =====\n{str(e)}\n")

    print(f"Dump created: {OUTPUT_FILE}")


if __name__ == "__main__":
    repo_url = input("Enter GitHub repo URL or owner/repo: ").strip()
    try:
        owner, repo = sanitize_repo_parts(repo_url)
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    dump_repo(owner, repo)
