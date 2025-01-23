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
        "python": [".py", ".pyw"],
        "go": [".go"],
        "md": [".md"],
    }
    return language_extensions.get(language.lower(), [])

def is_file_type(file_path: str, language: str) -> bool:
    """Check if the file has a valid extension for the specified language."""
    extensions = get_language_extensions(language)
    return any(file_path.endswith(ext) for ext in extensions)

def download_repo(repo_url, output_folder, branch_or_tag="master", keep_comments=False):
    """Download and process all files from a GitHub repository."""
    download_url = f"{repo_url}/archive/refs/heads/{branch_or_tag}.zip"

    print(f"Downloading from: {download_url}")
    response = requests.get(download_url)
    response.raise_for_status()  # Raise an exception for non-200 status codes

    try:
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
    except zipfile.BadZipFile:
        print(f"Error: The downloaded file is not a valid ZIP archive.")
        sys.exit(1)

    repo_name = repo_url.split('/')[-1]
    output_file = os.path.join(output_folder, f"{repo_name}_manifest.txt")

    with open(output_file, "w", encoding="utf-8") as outfile:
        # Write the manifest header
        outfile.write("<documents>\n")

        index = 0
        for file_path in zip_file.namelist():
            if file_path.endswith("/"):  # Skip directories
                continue

            try:
                file_content = zip_file.read(file_path).decode("utf-8", errors="replace")
            except UnicodeDecodeError:
                print(f"Warning: Skipping file {file_path} due to decoding error.")
                continue

            file_size = len(file_content.encode("utf-8"))

            # Add to manifest
            if index == 0:  # Create index 0 for manifest
                outfile.write("<document index=\"0\">\n")
                outfile.write(f"<source>{file_path}</source>\n")
                outfile.write(f"<file_size>{file_size}</file_size>\n")
                outfile.write("<document_content>\nManifest of all files in the repository:\n\n")
                outfile.write(f"{file_path} - {file_size} bytes\n")
                outfile.write("</document_content>\n")
                outfile.write("</document>\n\n")
                index += 1

            # Write content for each file
            outfile.write(f"<document index=\"{index}\">\n")
            outfile.write(f"<source>{file_path}</source>\n")
            outfile.write(f"<file_size>{file_size}</file_size>\n")
            outfile.write("<document_content>\n")
            outfile.write(file_content)
            outfile.write("\n</document_content>\n")
            outfile.write("</document>\n\n")
            index += 1

        outfile.write("</documents>")

def print_usage():
    print("Usage: python github2file.py <repo_url> [--branch_or_tag <branch_or_tag>] [--output_folder <output_folder>]")
    print("Options:")
    print("  <repo_url>               The URL of the GitHub repository")
    print("  --branch_or_tag          The branch or tag of the repository to download. Default: master")
    print("  --output_folder          The folder where output files will be saved. Default: repos")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Repository URL is required.")
        print_usage()
        sys.exit(1)

    parser = argparse.ArgumentParser(description='Download and process files from a GitHub repository.')
    parser.add_argument('repo_url', type=str, help='The URL of the GitHub repository')
    parser.add_argument('--branch_or_tag', type=str, help='The branch or tag of the repository to download', default="master")
    parser.add_argument('--output_folder', type=str, help='The folder to save output files', default="repos")

    args = parser.parse_args()
    os.makedirs(args.output_folder, exist_ok=True)

    try:
        download_repo(args.repo_url, args.output_folder, args.branch_or_tag)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Manifest and files saved to {args.output_folder}")
