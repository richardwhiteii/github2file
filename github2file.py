import os
import sys
import requests
import zipfile
import io
import ast
import argparse
from typing import List

def get_language_extensions(language: str) -> List[str]:
    """Return a list of file extensions for the specified programming language."""
    language_extensions = {
        "python": [".py", ".pyw"],  # Add .ipynb extension for Python notebooks
        #TODO convert python notebooks to python files or some format that allow conversion between notebook and python file.
        "go": [".go"],
        "md": [".md"],  # Markdown files
    }
    return language_extensions[language.lower()]

def is_file_type(file_path: str, language: str) -> bool:
    """Check if the file has a valid extension for the specified language."""
    extensions = get_language_extensions(language)
    return any(file_path.endswith(ext) for ext in extensions)

def is_likely_useful_file(file_path, lang):
    """Determine if the file is likely useful by applying filters."""
    # Only exclude git-related and test files
    excluded_dirs = ["tests", "test"]
    github_workflow_or_docs = [".github", ".gitignore", "LICENSE"]

    if lang == "python":
        excluded_dirs.append("__pycache__")
        github_workflow_or_docs.extend(["stale.py", "gen-card-", "write_model_card"])
    elif lang == "go":
        excluded_dirs.append("vendor")

    if any(part.startswith('.') for part in file_path.split('/')):
        return False
    if 'test' in file_path.lower():
        return False
    for excluded_dir in excluded_dirs:
        if f"/{excluded_dir}/" in file_path or file_path.startswith(excluded_dir + "/"):
            return False
    for doc_file in github_workflow_or_docs:
        if doc_file in file_path:
            return False
    return True

def is_test_file(file_content, lang):
    """Determine if the file content suggests it is a test file."""
    test_indicators = {
        "python": ["import unittest", "import pytest", "from unittest", "from pytest"],
        "go": ["import testing", "func Test"]
    }
    indicators = test_indicators.get(lang, [])
    return any(indicator in file_content for indicator in indicators)

def has_sufficient_content(file_content, min_line_count=10):
    """Check if the file has a minimum number of substantive lines."""
    lines = [line for line in file_content.split('\n') if line.strip() and not line.strip().startswith(('#', '//'))]
    return len(lines) >= min_line_count

def remove_comments_and_docstrings(source):
    """Remove comments and docstrings from the Python source code."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and ast.get_docstring(node):
            node.body = node.body[1:]  # Remove docstring
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
            node.value.s = ""  # Remove comments
    return ast.unparse(tree)

def download_repo(repo_url, output_folder, lang, keep_comments=False, branch_or_tag="master", claude=False):
    """Download and process files from a GitHub repository."""
    download_url = f"{repo_url}/archive/refs/heads/{branch_or_tag}.zip"

    print(f"Downloading from: {download_url}")
    response = requests.get(download_url)
    response.raise_for_status()

    try:
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
    except zipfile.BadZipFile:
        print(f"Error: The downloaded file is not a valid ZIP archive.")
        sys.exit(1)

    repo_name = repo_url.split('/')[-1]
    output_file = os.path.join(output_folder, f"{repo_name}_{lang}.txt")
    if claude:
        output_file = os.path.join(output_folder, f"{repo_name}_{lang}-claude.txt")

    with open(output_file, "w", encoding="utf-8") as outfile:
        if claude and isinstance(claude, bool):
            outfile.write("Here are some documents for you to reference for your task:\n\n")
            outfile.write("<documents>\n")

            # Create file structure as document index 0
            outfile.write("<document index=\"0\">\n")
            outfile.write("<source>file_structure.txt</source>\n")
            outfile.write("<document_content>\n")
            outfile.write("Repository File Structure:\n")
            outfile.write("========================\n\n")
            
            # List all files in the repository
            for file_path in sorted(zip_file.namelist()):
                if not file_path.endswith('/'):  # Skip directory entries
                    outfile.write(f"{file_path}\n")
            
            outfile.write("</document_content>\n")
            outfile.write("</document>\n\n")

            # Include the README file as document index 1
            readme_file_path, readme_content = find_readme_content(zip_file)
            outfile.write("<document index=\"1\">\n")
            outfile.write(f"<source>{readme_file_path}</source>\n")
            outfile.write(f"<document_content>\n{readme_content}\n</document_content>\n")
            outfile.write("</document>\n\n")

            # Process remaining files
            index = 2
            for file_path in zip_file.namelist():
                # Skip directories and non-language files
                if file_path.endswith("/") or not is_file_type(file_path, lang) or not is_likely_useful_file(file_path, lang):
                    continue

                try:
                    file_content = zip_file.read(file_path).decode("utf-8", errors="replace")
                except UnicodeDecodeError:
                    print(f"Warning: Skipping file {file_path} due to decoding error.")
                    continue

                # Skip test files based on content
                if is_test_file(file_content, lang):
                    continue

                if lang == "python" and not keep_comments:
                    try:
                        file_content = remove_comments_and_docstrings(file_content)
                    except:
                        # If comment removal fails, keep original content
                        pass

                outfile.write(f"<document index=\"{index}\">\n")
                outfile.write(f"<source>{file_path}</source>\n")
                outfile.write(f"<document_content>\n{file_content}\n</document_content>\n")
                outfile.write("</document>\n\n")
                index += 1

            outfile.write("</documents>")

def find_readme_content(zip_file):
    """
    Recursively search for the README file within the ZIP archive and return its content and file path.
    """
    readme_file_path = ""
    readme_content = ""
    for file_path in zip_file.namelist():
        if file_path.endswith("/README.md") or file_path == "README.md":
            try:
                readme_content = zip_file.read(file_path).decode("utf-8", errors="replace")
                readme_file_path = file_path
                break
            except UnicodeDecodeError:
                print(f"Warning: Skipping README.md file due to decoding error.")

    if not readme_content:
        for file_path in zip_file.namelist():
            if file_path.endswith("/README") or file_path == "README":
                try:
                    readme_content = zip_file.read(file_path).decode("utf-8", errors="replace")
                    readme_file_path = file_path
                    break
                except UnicodeDecodeError:
                    print(f"Warning: Skipping README file due to decoding error.")

    if not readme_content:
        readme_content = "No README file found in the repository."

    return readme_file_path, readme_content

def print_usage():
    print("Usage: python github2file.py <repo_url> [--lang <language>] [--keep-comments] [--branch_or_tag <branch_or_tag>] [--claude]")
    print("Options:")
    print("  <repo_url>               The URL of the GitHub repository")
    print("  --lang <language>        The programming language of the repository (choices: go, python, md). Default: python")
    print("  --keep-comments          Keep comments and docstrings in the source code (only applicable for Python)")
    print("  --branch_or_tag <branch_or_tag>  The branch or tag of the repository to download. Default: master")
    print("  --claude                 Format the output for Claude with document tags")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Repository URL is required.")
        print_usage()
        sys.exit(1)

    parser = argparse.ArgumentParser(description='Download and process files from a GitHub repository.')
    parser.add_argument('repo_url', type=str, help='The URL of the GitHub repository')
    parser.add_argument('--lang', type=str, choices=['go', 'python', 'md'], default='python', help='The programming language of the repository')
    parser.add_argument('--keep-comments', action='store_true', help='Keep comments and docstrings in the source code (only applicable for Python)')
    parser.add_argument('--branch_or_tag', type=str, help='The branch or tag of the repository to download', default="master")
    parser.add_argument('--claude', action='store_true', help='Format the output for Claude with document tags')

    args = parser.parse_args()
    output_folder = "repos"
    os.makedirs(output_folder, exist_ok=True)
    output_file_base = f"{args.repo_url.split('/')[-1]}_{args.lang}.txt"
    output_file = output_file_base if not args.claude else f"{output_file_base}-claude.txt"

    try:
        download_repo(args.repo_url, output_folder, args.lang, args.keep_comments, args.branch_or_tag, args.claude)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Combined {args.lang.capitalize()} source code saved to repos/{output_file}")