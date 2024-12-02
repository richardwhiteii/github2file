import os
import sys
import requests
import zipfile
import io
import ast
import argparse
from typing import List, Set

def get_language_extensions(language: str) -> List[str]:
    """Return a list of file extensions for the specified programming language/category."""
    language_extensions = {
        # Python-related files
        "python": [
            ".py", ".pyw", ".pyc", ".pyo", ".pyd",  # Python source and compiled
            ".ipynb",  # Jupyter notebooks
            ".pyx", ".pxd",  # Cython
            ".cfg", ".ini",  # Configuration
            ".toml",  # Project configuration (pyproject.toml)
            ".requirements.txt", ".constraints.txt",  # Dependencies
            ".jinja", ".jinja2", ".j2",  # Templates
        ],
        
        # Web development
        "web": [
            ".html", ".htm", ".xhtml",  # HTML
            ".css", ".scss", ".sass", ".less",  # Stylesheets
            ".js", ".jsx", ".ts", ".tsx",  # JavaScript/TypeScript
            ".vue", ".svelte",  # Component frameworks
            ".json", ".jsonld",  # JSON files
            ".xml", ".xsl", ".xslt",  # XML files
            ".wasm",  # WebAssembly
        ],
        
        # Documentation and text
        "docs": [
            ".md", ".markdown", ".mdown",  # Markdown
            ".rst", ".asciidoc", ".adoc",  # Other doc formats
            ".txt", ".text",  # Plain text
            ".pdf", ".doc", ".docx",  # Rich documents
            ".yaml", ".yml",  # YAML files
        ],
        
        # Go-related files
        "go": [
            ".go", ".mod", ".sum",  # Go source and modules
            ".tmpl", ".gohtml",  # Go templates
        ],
        
        # Java/JVM languages
        "java": [
            ".java", ".class", ".jar",  # Java
            ".kt", ".kts",  # Kotlin
            ".scala", ".sc",  # Scala
            ".gradle", ".groovy",  # Gradle/Groovy
            ".clj", ".cljs",  # Clojure
        ],
        
        # C-family languages
        "c": [
            ".c", ".h",  # C
            ".cpp", ".hpp", ".cc", ".hh", ".cxx", ".hxx",  # C++
            ".m", ".mm",  # Objective-C
        ],
        
        # Shell and scripting
        "shell": [
            ".sh", ".bash", ".zsh", ".fish",  # Shell scripts
            ".ps1", ".psm1", ".psd1",  # PowerShell
            ".bat", ".cmd", ".btm",  # Windows batch
        ],
        
        # Configuration and data
        "config": [
            ".env", ".env.*",  # Environment variables
            ".conf", ".config",  # Configuration files
            ".ini", ".cfg",  # INI files
            ".properties",  # Properties files
            ".json", ".yaml", ".yml", ".toml", ".xml",  # Structured data
            ".lock", ".lock.*",  # Lock files
            ".dockerfile", "Dockerfile.*",  # Docker
            "Makefile", ".mk",  # Make
            ".editorconfig", ".gitignore", ".gitattributes",  # Tool config
        ],
        
        "all": []  # Special category that includes all file types
    }
    
    # For 'all' category, combine all extensions
    if language.lower() == 'all':
        all_extensions = set()
        for extensions in language_extensions.values():
            all_extensions.update(extensions)
        return list(all_extensions)
    
    return language_extensions.get(language.lower(), [])

def get_all_supported_languages() -> List[str]:
    """Return a list of all supported language/category names."""
    return [
        "python", "web", "docs", "go", "java", "c", "shell", 
        "config", "all"
    ]

def is_file_type(file_path: str, languages: List[str]) -> bool:
    """Check if the file has a valid extension for any of the specified languages."""
    all_extensions = set()
    for lang in languages:
        all_extensions.update(get_language_extensions(lang))
    
    # Handle files without extensions
    if '.' not in file_path:
        return os.path.basename(file_path) in ['Makefile', 'Dockerfile']
    
    # Check if the file matches any of the extensions
    return any(file_path.endswith(ext) for ext in all_extensions)

def is_likely_useful_file(file_path: str) -> bool:
    """Determine if the file is likely useful by applying filters."""
    excluded_dirs = ["__pycache__", "node_modules"]
    
    # Skip hidden files/directories unless they're common config files
    if any(part.startswith('.') for part in file_path.split('/')):
        allowed_dotfiles = ['.gitignore', '.env', '.dockerignore', '.editorconfig']
        if not any(file_path.endswith(dotfile) for dotfile in allowed_dotfiles):
            return False
    
    # Skip excluded directories
    for excluded_dir in excluded_dirs:
        if f"/{excluded_dir}/" in file_path or file_path.startswith(excluded_dir + "/"):
            return False
            
    return True

def download_repo(repo_url: str, output_folder: str, languages: List[str], 
                 keep_comments: bool = False, branch_or_tag: str = "master",
                 claude: bool = False) -> None:
    """Download and process files from a GitHub repository."""
    # Convert repo URL to API format if needed
    if repo_url.endswith("/"):
        repo_url = repo_url[:-1]
    if repo_url.startswith("https://github.com/"):
        repo_url = repo_url[len("https://github.com/"):]
    
    download_url = f"https://github.com/{repo_url}/archive/refs/heads/{branch_or_tag}.zip"

    print(f"Downloading from: {download_url}")
    response = requests.get(download_url)
    response.raise_for_status()

    try:
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
    except zipfile.BadZipFile:
        print(f"Error: The downloaded file is not a valid ZIP archive.")
        sys.exit(1)

    repo_name = repo_url.split('/')[-1]
    lang_str = "_".join(languages)
    output_file = os.path.join(output_folder, f"{repo_name}_{lang_str}.txt")
    if claude:
        output_file = os.path.join(output_folder, f"{repo_name}_{lang_str}-claude.txt")

    with open(output_file, "w", encoding="utf-8") as outfile:
        if claude:
            outfile.write("Here are some documents for you to reference for your task:\n\n")
            outfile.write("<documents>\n")

            # File structure (index 0)
            outfile.write("<document index=\"0\">\n")
            outfile.write("<source>file_structure.txt</source>\n")
            outfile.write("<document_content>\n")
            outfile.write("Repository File Structure:\n")
            outfile.write("========================\n\n")
            
            # List all files that match the requested languages
            for file_path in sorted(zip_file.namelist()):
                if not file_path.endswith('/'):  # Skip directory entries
                    if is_file_type(file_path, languages):
                        outfile.write(f"{file_path}\n")
            
            outfile.write("</document_content>\n")
            outfile.write("</document>\n\n")

            # README file (index 1)
            readme_file_path, readme_content = find_readme_content(zip_file)
            outfile.write("<document index=\"1\">\n")
            outfile.write(f"<source>{readme_file_path}</source>\n")
            outfile.write(f"<document_content>\n{readme_content}\n</document_content>\n")
            outfile.write("</document>\n\n")

            # Process remaining files
            index = 2
            for file_path in sorted(zip_file.namelist()):
                if (file_path.endswith("/") or 
                    not is_file_type(file_path, languages) or 
                    not is_likely_useful_file(file_path)):
                    continue

                try:
                    file_content = zip_file.read(file_path).decode("utf-8", errors="replace")
                except UnicodeDecodeError:
                    print(f"Warning: Skipping file {file_path} due to decoding error.")
                    continue

                # Remove comments only from Python files if requested
                if file_path.endswith('.py') and not keep_comments:
                    try:
                        file_content = remove_comments_and_docstrings(file_content)
                    except:
                        pass  # Keep original content if comment removal fails

                outfile.write(f"<document index=\"{index}\">\n")
                outfile.write(f"<source>{file_path}</source>\n")
                outfile.write(f"<document_content>\n{file_content}\n</document_content>\n")
                outfile.write("</document>\n\n")
                index += 1

            outfile.write("</documents>")
        else:
            # Non-Claude format output
            for file_path in sorted(zip_file.namelist()):
                if (not file_path.endswith("/") and 
                    is_file_type(file_path, languages) and 
                    is_likely_useful_file(file_path)):
                    try:
                        file_content = zip_file.read(file_path).decode("utf-8", errors="replace")
                        outfile.write(f"# File: {file_path}\n")
                        outfile.write(file_content)
                        outfile.write("\n\n")
                    except UnicodeDecodeError:
                        print(f"Warning: Skipping file {file_path} due to decoding error.")

def main():
    parser = argparse.ArgumentParser(
        description='Download and process files from a GitHub repository.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Download Python files:
    python github2file.py username/repo --lang python
    
  Download multiple types:
    python github2file.py username/repo --lang python web docs
    
  Download all supported file types:
    python github2file.py username/repo --lang all
    
Supported languages/categories:
  """ + ", ".join(get_all_supported_languages())
    )
    
    parser.add_argument('repo_url', type=str, help='The URL or path of the GitHub repository')
    parser.add_argument('--lang', nargs='+', default=['all'], 
                        choices=get_all_supported_languages(),
                        help='One or more language/category to process')
    parser.add_argument('--keep-comments', action='store_true',
                        help='Keep comments and docstrings in Python files')
    parser.add_argument('--branch_or_tag', type=str, default="master",
                        help='The branch or tag to download')
    parser.add_argument('--claude', action='store_true',
                        help='Format output for Claude with document tags')
    
    args = parser.parse_args()
    
    output_folder = "repos"
    os.makedirs(output_folder, exist_ok=True)
    
    try:
        download_repo(args.repo_url, output_folder, args.lang,
                     args.keep_comments, args.branch_or_tag, args.claude)
        print(f"Processing complete. Files saved in the '{output_folder}' directory.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()