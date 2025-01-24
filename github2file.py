#!/usr/bin/env python3
"""
Enhanced github2file tool with LLM analysis capabilities.
Original functionality preserved with additional LLM-powered repository analysis.
"""

import os
import sys
import requests
import zipfile
import io
#import ast
import argparse
import asyncio
from typing import List, Optional
from datetime import datetime
import json
import xml.etree.ElementTree as ET
from llm_analyzer import LLMAnalyzer

def get_language_extensions(language: str) -> List[str]:
    """Return a list of file extensions for the specified programming language."""
    language_extensions = {
        "python": [".py", ".pyw"],
        "go": [".go"],
        "javascript": [".js", ".jsx", ".ts", ".tsx"],
        "java": [".java"],
        "md": [".md"],
    }
    return language_extensions[language.lower()]

def is_file_type(file_path: str, language: str) -> bool:
    """Check if the file has a valid extension for the specified language."""
    extensions = get_language_extensions(language)
    return any(file_path.endswith(ext) for ext in extensions)

def is_likely_useful_file(file_path, lang):
    """Determine if the file is likely useful by applying various filters."""
    excluded_dirs = ["examples", "tests", "test", "scripts", "utils", "benchmarks"]
    utility_or_config_files = []
    workflow_or_docs = [".github", ".gitlab-ci.yml", ".gitignore", "LICENSE", "README"]

    if lang == "python":
        excluded_dirs.append("__pycache__")
        utility_or_config_files.extend(["hubconf.py", "setup.py"])
        workflow_or_docs.extend(["stale.py", "gen-card-", "write_model_card"])
    elif lang == "go":
        excluded_dirs.append("vendor")
        utility_or_config_files.extend(["go.mod", "go.sum", "Makefile"])

    if any(part.startswith('.') for part in file_path.split('/')):
        return False
    if 'test' in file_path.lower():
        return False
    for excluded_dir in excluded_dirs:
        if f"/{excluded_dir}/" in file_path or file_path.startswith(excluded_dir + "/"):
            return False
    for file_name in utility_or_config_files:
        if file_name in file_path:
            return False
    for doc_file in workflow_or_docs:
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

# def remove_comments_and_docstrings(source):
#     """Remove comments and docstrings from the Python source code without executing."""
#     try:
#         tree = ast.parse(source)
#         for node in ast.walk(tree):
#             if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and ast.get_docstring(node):
#                 node.body = node.body[1:]
#             elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
#                 node.value.value = ""
#         return ast.unparse(tree)
#     except:
#         return source  # Return original source if parsing fails

def construct_download_url(repo_url, branch_or_tag):
    """Construct the appropriate download URL for GitHub or GitLab."""
    if "github.com" in repo_url:
        return f"{repo_url}/archive/refs/heads/{branch_or_tag}.zip"
    elif "gitlab.com" in repo_url:
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        return f"{repo_url.rstrip('.git')}/-/archive/{branch_or_tag}/{repo_name}-{branch_or_tag}.zip"
    else:
        raise ValueError("Unsupported repository URL. Only GitHub and GitLab URLs are supported.")

def process_with_llm(repo_url: str, output_file: str, args) -> None:
    """Process repository using LLM analysis."""
    analyzer = LLMAnalyzer(repo_url, args.verbose)
    
    try:
        results = analyzer.analyze(dry_run=args.dry_run)
        
        # Save results based on format preference
        if args.format == 'json':
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
        else:  # XML format
            root = ET.Element('repository')
            # Convert dict to XML structure
            def dict_to_xml(parent, data):
                for key, value in data.items():
                    child = ET.SubElement(parent, key)
                    if isinstance(value, dict):
                        dict_to_xml(child, value)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, dict):
                                item_elem = ET.SubElement(child, 'item')
                                dict_to_xml(item_elem, item)
                            else:
                                ET.SubElement(child, 'item').text = str(item)
                    else:
                        child.text = str(value)
            
            dict_to_xml(root, results)
            tree = ET.ElementTree(root)
            tree.write(output_file, encoding='utf-8', xml_declaration=True)
        
        print(f"Analysis complete. Results saved to {output_file}")
        return

    except Exception as e:
        print(f"Error during LLM analysis: {str(e)}")
        sys.exit(1)

# def download_repo(repo_url, output_file, lang, keep_comments=False, branch_or_tag="main", token=None, claude=False):
#     """Download and process files from a GitHub or GitLab repository."""
def download_repo(repo_url, output_folder, lang, keep_comments=False, branch_or_tag="main", token=None, claude=False):
    """Download and process files from a GitHub or GitLab repository."""
    # Original download_repo implementation remains unchanged
    download_url = construct_download_url(repo_url, branch_or_tag)
    headers = {}

    if token:
        if "gitlab.com" in repo_url:
            headers['PRIVATE-TOKEN'] = token
        elif "github.com" in repo_url:
            headers['Authorization'] = f'token {token}'

    print(f"Downloading from: {download_url}")
    response = requests.get(download_url, headers=headers)

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
        # Include the README file
        readme_file_path, readme_content = find_readme_content(zip_file)

        if claude and isinstance(claude, bool):
            outfile.write("Here are some documents for you to reference for your task:\n\n")
            outfile.write("<documents>\n")

            outfile.write("<document index=\"0\">\n")
            outfile.write(f"<source>{readme_file_path}</source>\n")
            outfile.write(f"<document_content>\n{readme_content}\n</document_content>\n")
            outfile.write("</document>\n\n")
        else:
            outfile.write(f"{'// ' if lang == 'go' else '# '}File: {readme_file_path}\n")
            outfile.write(readme_content)
            outfile.write("\n\n")

        index = 1
        for file_path in zip_file.namelist():
            # Skip directories, non-language files, less likely useful files, hidden directories, and test files
            if file_path.endswith("/") or not is_file_type(file_path, lang) or not is_likely_useful_file(file_path, lang):
                continue

            try:
                file_content = zip_file.read(file_path).decode("utf-8", errors="replace")
            except UnicodeDecodeError:
                print(f"Warning: Skipping file {file_path} due to decoding error.")
                continue

            # Skip test files based on content and files with insufficient substantive content
            # if is_test_file(file_content, lang) or not has_sufficient_content(file_content):
            #     continue
            # if lang == "python" and not keep_comments:
            #     file_content = remove_comments_and_docstrings(file_content)

            if claude and isinstance(claude, bool):
                outfile.write(f"<document index=\"{index}\">\n")
                outfile.write(f"<source>{file_path}</source>\n")
                outfile.write(f"<document_content>\n{file_content}\n</document_content>\n")
                outfile.write("</document>\n\n")
                index += 1
            else:
                outfile.write(f"{'// ' if lang == 'go' else '# '}File: {file_path}\n")
                outfile.write(file_content)
                outfile.write("\n\n")

        if claude and isinstance(claude, bool):
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


def main():
    # Create output directory if it doesn't exist
    output_folder = "repos"
    os.makedirs(output_folder, exist_ok=True)
    """Main entry point with enhanced argument parsing."""
    parser = argparse.ArgumentParser(description='Download and analyze GitHub/GitLab repositories with optional LLM processing.')
    parser.add_argument('repo_url', type=str, help='The URL of the GitHub or GitLab repository')
    
    # Original arguments
    parser.add_argument('--lang', type=str, choices=['go', 'python', 'md'], default='python',
                      help='The programming language of the repository')
    parser.add_argument('--keep-comments', action='store_true',
                      help='Keep comments and docstrings in the source code (only applicable for Python)')
    parser.add_argument('--branch_or_tag', type=str, default="main",
                      help='The branch or tag of the repository to download')
    parser.add_argument('--token', type=str, help='Personal access token for private repositories')
    parser.add_argument('--claude', action='store_true',
                      help='Format the output for Claude with document tags')
    
    # New LLM-related arguments
    parser.add_argument('--llm', action='store_true',
                      help='Enable LLM analysis of the repository')
    parser.add_argument('--format', choices=['xml', 'json'], default='xml',
                      help='Output format for LLM analysis results')
    parser.add_argument('--dry-run', action='store_true',
                      help='Show analysis plan without execution')
    parser.add_argument('--verbose', type=int, choices=[0, 1, 2, 3], default=1,
                      help='Verbosity level (0=quiet, 1=normal, 2=verbose, 3=debug)')

    args = parser.parse_args()

    # Determine output filename based on processing mode
    base_filename = f"{args.repo_url.split('/')[-1]}_{args.lang}"
    if args.llm:
        output_file = os.path.join(output_folder, f"{base_filename}_llm.{args.format}")
        asyncio.run(process_with_llm(args.repo_url, output_file, args))
    else:
        output_file = os.path.join(output_folder, f"{base_filename}.txt")
        if args.claude:
            output_file = output_file.replace('.txt', '-claude.txt')
        download_repo(
            repo_url=args.repo_url,
            output_folder=output_folder,
            lang=args.lang,
            #keep_comments=args.keep_comments,
            branch_or_tag=args.branch_or_tag,
            token=args.token,
            claude=args.claude
        )

    print(f"Processing complete. Output saved to {output_file}")

if __name__ == "__main__":
    main()