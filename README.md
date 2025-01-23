# GitHub Repository to File Converter

An enhanced Python tool that downloads and processes GitHub repositories, with optional LLM-powered analysis capabilities. This tool helps share code with chatbots that have large context capabilities but don't automatically download code from GitHub.

## Features

### Core Features
- Download and process files from GitHub and GitLab repositories
- Support for both public and private repositories
- Filter files based on programming language (Python, Markdown, Go, JavaScript)
- Exclude certain directories, file types, and test files
- Remove comments and docstrings from Python source code (optional)
- Specify a branch or tag to download from (default: "main")
- Format output for Claude with document tags

### New LLM Analysis Features
- Intelligent repository analysis using two-tier LLM processing
- Derived Compression (DC) to reduce context size while preserving functionality
- Dependency analysis with critical path identification
- XML/JSON artifact generation
- Configurable verbosity levels
- Progress tracking and rate limiting

## Installation

1. Create and activate a Python environment:
```bash
conda create -n g2f python=3.10
conda activate g2f
```

2. Install requirements:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.template .env
# Edit .env with your API keys and preferences
```

## Usage

### Basic Usage
To download and process files from a public GitHub repository:
```bash
python github2file.py https://github.com/username/repository
```

For a private repository:
```bash
python github2file.py https://<USERNAME>:<GITHUB_ACCESS_TOKEN>@github.com/username/repository
```

### LLM-Enhanced Analysis
To analyze a repository using LLM capabilities:
```bash
python github2file.py https://github.com/username/repository --llm
```

### Command Line Arguments

#### Core Arguments
- `--lang`: Specify programming language ("md", "go", "javascript", "python")
- `--keep-comments`: Keep comments and docstrings (Python only)
- `--branch_or_tag`: Specify repository branch/tag (default: "main")
- `--claude`: Format output for Claude with document tags

#### LLM Analysis Arguments
- `--llm`: Enable LLM analysis
- `--format`: Choose output format (xml/json)
- `--dry-run`: Show analysis plan without execution
- `--verbose`: Set verbosity level (0=quiet, 1=normal, 2=verbose, 3=debug)

### Examples

Basic repository download:
```bash
python github2file.py https://github.com/huggingface/transformers --lang python
```

LLM analysis with XML output:
```bash
python github2file.py https://github.com/username/repo --llm --format xml --verbose 2
```

Dry run of LLM analysis:
```bash
python github2file.py https://github.com/username/repo --llm --dry-run
```

## Output Formats

### Standard Output
Creates `repository_language.txt` containing combined source code.

### LLM Analysis Output
Creates a structured artifact in XML or JSON format containing:
- Repository metadata
- Dependency analysis
- Derived compression prompts
- Critical paths and cycles
- Recovery guide

## Derived Compression

Derived Compression (DC) is a feature that reduces context size by:
- Identifying content that can be recreated from prompts
- Storing prompts instead of full content
- Maintaining references to source files
- Providing recreation instructions

Common DC targets:
- Test files
- Documentation
- Example code
- Configuration templates

## Configuration

Create a `.env` file with the following settings:
```plaintext
ANTHROPIC_API_KEY=your_api_key
RATE_LIMIT=20
PLANNING_MODEL=claude-3-opus
EXECUTION_MODEL=claude-3-sonnet
```

See `.env.template` for all available configurations.

## Requirements
- Python 3.x
- `requests`
- `anthropic`
- Additional requirements in `requirements.txt`

## License
This project is open-source and available under the [MIT License](LICENSE).