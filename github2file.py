import os
import sys
import requests
import zipfile
import io
import ast
import argparse
import logging
from logging.handlers import RotatingFileHandler
from typing import List

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

def get_language_extensions(language: str) -> List[str]:
    """Return a list of file extensions for the specified programming language."""
    language_extensions = {
        "python": [".py", ".pyw"],  # Add .ipynb extension for Python notebooks
        #TODO convert python notebooks to python files or some format that allow conversion between notebook and python file.
        "go": [".go"],
        "javascript": [".js", ".jsx", ".ts", ".tsx"],
        "java": [".java"],
        "md": [".md"],  # Add .md extension for Markdown files
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

def remove_comments_and_docstrings(source):
    """Remove comments and docstrings from the Python source code."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and ast.get_docstring(node):
            node.body = node.body[1:]  # Remove docstring
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            node.value.value = ""  # Remove comments
    return ast.unparse(tree)

def construct_download_url(repo_url, branch_or_tag):
    """Construct the appropriate download URL for GitHub or GitLab based on the provided URL."""
    if "github.com" in repo_url:
        return f"{repo_url}/archive/refs/heads/{branch_or_tag}.zip"
    elif "gitlab.com" in repo_url:
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        return f"{repo_url.rstrip('.git')}/-/archive/{branch_or_tag}/{repo_name}-{branch_or_tag}.zip"
    else:
        raise ValueError("Unsupported repository URL. Only GitHub and GitLab URLs are supported.")

def is_binary_file(content_sample):
    """
    Check if a file appears to be binary based on its content.
    """
    try:
        content_sample.decode('utf-8')
        return '\0' in content_sample.decode('utf-8')
    except UnicodeDecodeError:
        return True
    
def check_default_branches(repo_url, token=None):
    """Check for the presence of 'main' and 'master' branches in the repository."""
    headers = {}
    if token:
        if "gitlab.com" in repo_url:
            headers['PRIVATE-TOKEN'] = token
        elif "github.com" in repo_url:
            headers['Authorization'] = f'token {token}'
    
    # Modify the URL to use GitHub's API
    if "github.com" in repo_url:
        api_url = repo_url.replace("github.com", "api.github.com/repos")
        branches_url = f"{api_url}/branches"
    elif "gitlab.com" in repo_url:
        branches_url = f"{repo_url}/branches"
    else:
        raise ValueError("Unsupported repository URL. Only GitHub and GitLab URLs are supported.")

    response = requests.get(branches_url, headers=headers)
    
    if response.status_code != 200:
        logger.warning(f"Unable to fetch branches (Status code: {response.status_code})")
        # Fall back to trying 'main' first, then 'master'
        return "main"
    
    try:
        branches = response.json()
        if not isinstance(branches, list):
            logger.warning("Unexpected API response format")
            return "main"
            
        branch_names = [branch['name'] for branch in branches]
        
        if "main" in branch_names:
            return "main"
        elif "master" in branch_names:
            return "master"
        else:
            logger.warning("Neither 'main' nor 'master' branches found")
            return "main"
    except (ValueError, KeyError) as e:
        logger.warning(f"Error parsing branch information: {str(e)}")
        return "main"

def format_manifest_entry(file_path, description, doc_index, max_path_len=40):
    """Format a manifest entry with description and indented link."""
    # Format the first line with path and description
    padded_path = file_path.ljust(max_path_len)
    first_line = f"{padded_path}  {description}"
    
    # Create the indented link or skipped line
    if doc_index is not None:
        second_line = f"  <link target=\"{doc_index}\">{file_path}</link>"
    else:
        second_line = f"  <skipped>{file_path}</skipped>"
        
    return f"{first_line}\n{second_line}"

def format_manifest_line(file_path, description, doc_index, max_path_len=50):
    """Format a single manifest line with clean padding and wrapping."""
    # Truncate and pad the path if it's too long
    display_path = file_path
    if len(display_path) > max_path_len:
        parts = display_path.split('/')
        while len(display_path) > max_path_len and len(parts) > 2:
            parts = parts[1:]  # Remove leading directories
            display_path = ".../" + "/".join(parts)
    
    padded_path = display_path.ljust(max_path_len)
    
    # Add the description and link
    if doc_index is not None:
        link = f"<link target=\"{doc_index}\">{file_path}</link>"
    else:
        link = f"<skipped>{file_path}</skipped>"
        
    return f"{padded_path}  {description}  {link}"

def process_repository_files(zip_file, outfile, lang, keep_comments=False, claude=False, include_all=False):
    """Process all files from the repository based on specified options."""
    if claude:
        outfile.write("Here are some documents for you to reference for your task:\n\n")
        outfile.write("<documents>\n")

    # Document 0: README
    readme_file_path, readme_content = find_readme_content(zip_file)
    if claude:
        outfile.write("<document index=\"0\">\n")
        outfile.write(f"<source>{readme_file_path}</source>\n")
        outfile.write(f"<document_content>\n{readme_content}\n</document_content>\n")
        outfile.write("</document>\n\n")
    else:
        outfile.write(f"{'// ' if lang == 'go' else '# '}File: {readme_file_path}\n")
        outfile.write(readme_content)
        outfile.write("\n\n")

    # First pass: analyze files and prepare manifest data
    manifest_entries = []
    included_files = []
    next_doc_index = 2  # Start at 2 since 0 is README and 1 will be manifest

    for file_path in sorted(zip_file.namelist()):
        if file_path.endswith('/'):  # Skip directories
            continue

        try:
            # Determine if file is binary
            content_sample = zip_file.read(file_path)[:1024]
            is_binary = is_binary_file(content_sample)
            
            description = "Binary file" if is_binary else "Source file"
            
            if not is_binary:
                file_content = zip_file.read(file_path).decode('utf-8', errors='replace')
                
                # Check if file should be included
                should_include = include_all or (
                    is_file_type(file_path, lang) and
                    is_likely_useful_file(file_path, lang) and
                    not is_test_file(file_content, lang) and
                    has_sufficient_content(file_content)
                )
                
                if should_include:
                    manifest_entries.append((file_path, description, next_doc_index))
                    included_files.append((file_path, file_content))
                    next_doc_index += 1
                else:
                    manifest_entries.append((file_path, "Excluded file", None))
            else:
                manifest_entries.append((file_path, description, None))
                
        except Exception as e:
            logger.warning(f"Error processing file {file_path}: {str(e)}")
            manifest_entries.append((file_path, "Error processing file", None))

    # Document 1: Manifest with links
    manifest_content = "<manifest>\n# Repository Contents:\n"
    
    # Add each file to manifest with clean formatting
    for file_path, description, doc_index in manifest_entries:
        manifest_line = format_manifest_line(file_path, description, doc_index)
        manifest_content += manifest_line + "\n"
    
    manifest_content += "</manifest>"
    
    if claude:
        outfile.write("<document index=\"1\">\n")
        outfile.write("<source>manifest.txt</source>\n")
        outfile.write(f"<document_content>\n{manifest_content}\n</document_content>\n")
        outfile.write("</document>\n\n")
    else:
        outfile.write("# File: manifest.txt\n")
        outfile.write(manifest_content)
        outfile.write("\n\n")

    # Write remaining documents
    for file_path, file_content in included_files:
        if lang == "python" and not keep_comments and file_path.endswith('.py'):
            try:
                file_content = remove_comments_and_docstrings(file_content)
            except Exception as e:
                logger.warning(f"Could not remove comments from {file_path}: {str(e)}")

        doc_index = next(entry[2] for entry in manifest_entries if entry[0] == file_path)
        
        if claude:
            outfile.write(f"<document index=\"{doc_index}\">\n")
            outfile.write(f"<source>{file_path}</source>\n")
            outfile.write(f"<document_content>\n{file_content}\n</document_content>\n")
            outfile.write("</document>\n\n")
        else:
            outfile.write(f"{'// ' if lang == 'go' else '# '}File: {file_path}\n")
            outfile.write(file_content)
            outfile.write("\n\n")

    if claude:
        outfile.write("</documents>")

def download_repo(repo_url, output_file, lang, keep_comments=False, branch_or_tag="main", token=None, claude=False, include_all=False):
    """
    Download and process files from a GitHub or GitLab repository.
    
    Args:
        repo_url (str): URL of the GitHub/GitLab repository
        output_file (str): Base path for the output file
        lang (str): Programming language to filter for
        keep_comments (bool): Whether to preserve comments in Python files
        branch_or_tag (str): Branch or tag to download
        token (str): Authentication token for private repos
        claude (bool): Whether to format output for Claude
        include_all (bool): Whether to include all repository files
    """
    try:
        # Only try to check branches if no specific branch/tag was provided
        if branch_or_tag in ["main", "master"]:
            branch_or_tag = check_default_branches(repo_url, token)
    except Exception as e:
        logger.warning(f"Error checking default branches: {str(e)}")
        # Continue with the provided branch_or_tag

    # Construct appropriate download URL
    download_url = construct_download_url(repo_url, branch_or_tag)
    
    # Set up authentication headers if token provided
    headers = {}
    if token:
        if "gitlab.com" in repo_url:
            headers['PRIVATE-TOKEN'] = token
        elif "github.com" in repo_url:
            headers['Authorization'] = f'token {token}'

    # Download the repository
    logger.info(f"Downloading repository from: {download_url}")
    try:
        response = requests.get(download_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download repository: {e}")
        sys.exit(1)

    # Process the zip file
    try:
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
    except zipfile.BadZipFile:
        logger.error(f"The downloaded file is not a valid ZIP archive.")
        sys.exit(1)

    # Set up output file path
    repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    output_file = os.path.join(output_folder, f"{repo_name}_{lang}.txt")
    if claude:
        output_file = os.path.join(output_folder, f"{repo_name}_{lang}-claude.txt")

    # Process and write the files
    logger.info(f"Processing repository files...")
    try:
        with open(output_file, "w", encoding="utf-8") as outfile:
            process_repository_files(
                zip_file=zip_file,
                outfile=outfile,
                lang=lang,
                keep_comments=keep_comments,
                claude=claude,
                include_all=include_all
            )
    except Exception as e:
        logger.error(f"Error while processing repository files: {str(e)}")
        sys.exit(1)
    finally:
        zip_file.close()

    logger.info(f"Successfully processed repository.")
    logger.info(f"Output saved to: {output_file}")
    
    # Print summary of what was included
    if include_all:
        logger.info("Included: Complete manifest of all files and content of all non-binary files")
    else:
        logger.info(f"Included: Filtered {lang} files meeting usefulness criteria")

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
                logger.warning(f"Skipping README.md file due to decoding error.")

    if not readme_content:
        for file_path in zip_file.namelist():
            if file_path.endswith("/README") or file_path == "README":
                try:
                    readme_content = zip_file.read(file_path).decode("utf-8", errors="replace")
                    readme_file_path = file_path
                    break
                except UnicodeDecodeError:
                    logger.warning(f"Skipping README file due to decoding error.")

    if not readme_content:
        readme_content = "No README file found in the repository."

    return readme_file_path, readme_content

def print_usage():
    logger.info("Usage: python github2file.py <repo_url> [--lang <language>] [--keep-comments] [--branch_or_tag <branch_or_tag>] [--claude] [--all]")
    logger.info("Options:")
    logger.info("  <repo_url>               The URL of the GitHub repository")
    logger.info("  --lang <language>        The programming language of the repository (choices: go, python, md). Default: python")
    logger.info("  --keep-comments          Keep comments and docstrings in the source code (only applicable for Python)")
    logger.info("  --branch_or_tag <branch_or_tag>  The branch or tag of the repository to download. Default: master")
    logger.info("  --claude                 Format the output for Claude with document tags")
    logger.info("  --all                    Include all non-binary files in the output file")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Download and process files from a GitHub or GitLab repository.')
    parser.add_argument('repo_url', type=str, help='The URL of the GitHub or GitLab repository')
    parser.add_argument('--lang', type=str, choices=['go', 'python', 'md'], default='python', help='The programming language of the repository')
    parser.add_argument('--keep-comments', action='store_true', help='Keep comments and docstrings in the source code (only applicable for Python)')
    parser.add_argument('--branch_or_tag', type=str, help='The branch or tag of the repository to download', default="main")
    parser.add_argument('--token', type=str, help='Personal access token for private repositories', default=None)
    parser.add_argument('--claude', action='store_true', help='Format the output for Claude with document tags')
    parser.add_argument('--all', action='store_true', help='Include all non-binary files in the output file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()
    logger = setup_logging(args.verbose)
    output_folder = "repos"
    os.makedirs(output_folder, exist_ok=True)
    output_file_base = f"{args.repo_url.split('/')[-1]}_{args.lang}.txt"
    output_file = output_file_base if not args.claude else f"{output_file_base}-claude.txt"

    download_repo(repo_url=args.repo_url, output_file=output_folder, lang=args.lang, keep_comments=args.keep_comments, branch_or_tag=args.branch_or_tag, token=args.token, claude=args.claude, include_all=args.all)

    logger.info(f"Combined {args.lang.capitalize()} source code saved to {output_file}")
