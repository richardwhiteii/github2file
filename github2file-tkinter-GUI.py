import os
import sys
import requests
import zipfile
import io
import ast
import tkinter as tk
from tkinter import filedialog, messagebox, font, ttk
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(verbose=False):
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create file handler
    file_handler = RotatingFileHandler(
        'github2file.log',
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Get logger
    logger = logging.getLogger('github2file')
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

def is_python_file(file_path):
    """Check if the file is a Python file."""
    return file_path.endswith(".py")

def is_likely_useful_file(file_path):
    """Determine if the file is likely to be useful by excluding certain directories and specific file types."""
    excluded_dirs = ["docs", "examples", "tests", "test", "__pycache__", "scripts", "utils", "benchmarks"]
    utility_or_config_files = ["hubconf.py", "setup.py"]
    github_workflow_or_docs = ["stale.py", "gen-card-", "write_model_card"]

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

    for doc_file in github_workflow_or_docs:
        if doc_file in file_path:
            return False

    return True

def is_test_file(file_content):
    """Determine if the file content suggests it is a test file."""
    test_indicators = ["import unittest", "import pytest", "from unittest", "from pytest"]
    return any(indicator in file_content for indicator in test_indicators)

def has_sufficient_content(file_content, min_line_count=10):
    """Check if the file has a minimum number of substantive lines."""
    lines = [line for line in file_content.split('\n') if line.strip() and not line.strip().startswith('#')]
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

def download_repo(repo_url, output_file, include_all=False):
    """Download and process files from a GitHub repository."""
    response = requests.get(repo_url + "/archive/master.zip")
    zip_file = zipfile.ZipFile(io.BytesIO(response.content))

    with open(output_file, "w", encoding="utf-8") as outfile:
        if include_all:
            manifest = []
            for file_path in zip_file.namelist():
                if not file_path.endswith("/") and not file_path.startswith(".") and not file_path.startswith("__"):
                    manifest.append(file_path)
            outfile.write("# Manifest of all non-binary files:\n")
            for file_path in manifest:
                outfile.write(f"# {file_path}\n")
            outfile.write("\n\n")

        for file_path in zip_file.namelist():
            # Skip directories, non-Python files, less likely useful files, hidden directories, and test files
            if file_path.endswith("/") or not is_python_file(file_path) or not is_likely_useful_file(file_path):
                continue

            file_content = zip_file.read(file_path).decode("utf-8")

            # Skip test files based on content and files with insufficient substantive content
            if is_test_file(file_content) or not has_sufficient_content(file_content):
                continue

            try:
                file_content = remove_comments_and_docstrings(file_content)
            except SyntaxError:
                # Skip files with syntax errors
                logger.warning(f"Skipping file {file_path} due to syntax error.")
                continue

            outfile.write(f"# File: {file_path}\n")
            outfile.write(file_content)
            outfile.write("\n\n")

def print_usage():
    logger.info("Usage: python github2file-tkinter-GUI.py <repo_url> [--lang <language>] [--keep-comments] [--branch_or_tag <branch_or_tag>] [--claude] [--all]")
    logger.info("Options:")
    logger.info("  <repo_url>               The URL of the GitHub repository")
    logger.info("  --lang <language>        The programming language of the repository (choices: go, python, md). Default: python")
    logger.info("  --keep-comments          Keep comments and docstrings in the source code (only applicable for Python)")
    logger.info("  --branch_or_tag <branch_or_tag>  The branch or tag of the repository to download. Default: master")
    logger.info("  --claude                 Format the output for Claude with document tags")
    logger.info("  --all                    Download all files, including those that are less likely to be useful")

def main():
    root = tk.Tk()
    root.title("GitHub Repo Downloader")
    root.geometry("500x180")  # Make the window 10% shorter
    root.configure(bg="#1c1c1c")  # Set the background color to a dark shade

    # Custom font
    custom_font = font.Font(family="Consolas", size=12)

    # Custom button style
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TButton", padding=6, relief="flat", background="#00d0ff", foreground="#1c1c1c", font=custom_font)
    style.map("TButton", background=[("active", "#00a0c0")])

    def browse_repo():
        repo_url = repo_entry.get()
        include_all = include_all_var.get()
        if repo_url:
            repo_name = repo_url.split("/")[-1]
            output_file = f"{repo_name}_python.txt"
            download_repo(repo_url, output_file, include_all=include_all)
            messagebox.showinfo("Success", f"Combined Python source code saved to {output_file}", parent=root)
        else:
            messagebox.showerror("Error", "Please enter a valid GitHub repository URL.", parent=root)

    def browse_file():
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")], parent=root)
        include_all = include_all_var.get()
        if file_path:
            repo_url = repo_entry.get()
            if repo_url:
                download_repo(repo_url, file_path, include_all=include_all)
                messagebox.showinfo("Success", f"Combined Python source code saved to {file_path}", parent=root)
            else:
                messagebox.showerror("Error", "Please enter a valid GitHub repository URL.", parent=root)

    repo_label = tk.Label(root, text="GitHub Repository URL:", font=custom_font, fg="#00d0ff", bg="#1c1c1c")  # Light blue text on dark background
    repo_label.pack(pady=10)

    repo_entry = tk.Entry(root, width=40, font=custom_font, bg="#333333", fg="#ffffff")  # Light text on dark background
    repo_entry.pack()

    include_all_var = tk.BooleanVar()
    include_all_check = tk.Checkbutton(root, text="Include all non-binary files", variable=include_all_var, font=custom_font, fg="#00d0ff", bg="#1c1c1c", selectcolor="#333333")
    include_all_check.pack(pady=5)

    button_frame = tk.Frame(root, bg="#1c1c1c")  # Dark background for the button frame
    button_frame.pack(pady=10)

    download_button = ttk.Button(button_frame, text="Download", command=browse_repo)
    download_button.pack(side=tk.LEFT, padx=10)

    save_button = ttk.Button(button_frame, text="Save As...", command=browse_file)
    save_button.pack(side=tk.LEFT)

    root.mainloop()

if __name__ == "__main__":
    main()
