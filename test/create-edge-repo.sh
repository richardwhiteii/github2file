#!/bin/bash

# Set up main repository directory
REPO_NAME="test-repo-edge-cases"
rm -rf "$REPO_NAME"
mkdir -p "$REPO_NAME"
cd "$REPO_NAME"

# Initialize git repository
git init
git checkout -b development

# Create directory structure
mkdir -p src/{python/{deeply/nested/directory,notebooks},typescript,web}
mkdir -p docs/{technical,images,specs}
mkdir -p .vscode .github/{workflows,ISSUE_TEMPLATE}
mkdir -p test_data

# Create root level files
cat > README.md << 'EOF'
# Test Repository - Edge Cases

This repository contains various edge cases for testing repository processing tools.
Contains Unicode: Hello, 世界! šŸķ
EOF

cat > CONTRIBUTING.md << 'EOF'
# Contributing Guidelines
Line with CRLF ending`r`n
Line with LF ending`n
EOF

cat > setup.cfg << 'EOF'
[metadata]
name = edge-case-test
version = 1.0.0
EOF

cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "es5",
    "jsx": "react"
  }
}
EOF

touch .gitignore
echo ".env" > .gitignore

# Create Python source files
cat > src/python/unicode_handler.py << 'EOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module for handling Unicode text processing.
Includes examples in multiple languages: 
- Japanese: こんにちは
- Russian: Привет
- Arabic: مرحبا
"""

class UnicodeHandler:
    def __init__(self):
        self.greetings = {
            'ja': 'こんにちは',
            'ru': 'Привет',
            'ar': 'مرحبا'
        }
    
    def get_greeting(self, lang_code):
        return self.greetings.get(lang_code, 'Hello')

    def process_special_chars(self):
        """Test handling of special characters: θ, π, λ, ∑, ∫"""
        return "Processing: θ + π = mathematical_constants"
EOF

cat > src/python/deeply/nested/directory/module.py << 'EOF'
"""
A deeply nested module to test path handling.
"""
def nested_function():
    return "I am deeply nested!"
EOF

# Create TypeScript/JavaScript files
cat > src/typescript/component.tsx << 'EOF'
import React, { useState } from 'react';

interface Props {
    name: string;
    age?: number;
}

const UnicodeDisplay: React.FC<Props> = ({ name, age }) => {
    const [text, setText] = useState<string>('Hello, 世界!');
    
    return (
        <div className="unicode-wrapper">
            <h1>{text}</h1>
            <p>Name: {name}</p>
            {age && <p>Age: {age}</p>}
        </div>
    );
};

export default UnicodeDisplay;
EOF

cat > src/typescript/utils.ts << 'EOF'
export function formatGreeting(name: string): string {
    return `Hello, ${name}!`;
}
EOF

cat > src/web/app.jsx << 'EOF'
import React from 'react';

const App = () => {
    return (
        <div>Hello World!</div>
    );
};

export default App;
EOF

# Create documentation files
cat > docs/technical/api.md << 'EOF'
# API Documentation

## Special Characters Test
The API handles these special characters: æøå θΣπ

## Code Blocks
```python
def unicode_example():
    return "Hello, 世界!"
```

```typescript
const greeting: string = "Привет, мир!";
```
EOF

# Create file with Unicode filename (might need locale support)
echo "Unicode content in file with Unicode name" > "docs/specs/RFC-åøß.txt"
echo "使用手册内容" > "docs/technical/使用手册.md"

# Create test data files
touch test_data/empty.txt
echo "   
   " > test_data/only_whitespace.txt
echo -e "Windows line\r\nUnix line\nMixed content" > test_data/mixed_endings.txt

# Generate a large test file
yes "This is a test line for the large file.\n" | head -n 10000 > test_data/huge_file.log

# Create Jupyter notebook files
cat > src/python/notebooks/analysis.ipynb << 'EOF'
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Analysis Notebook"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "print('Hello, 世界!')"
   ]
  }
 ]
}
EOF

# Create GitHub workflow file
cat > .github/workflows/custom-workflow.yml << 'EOF'
name: CI
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
EOF

# Create VS Code settings
cat > .vscode/settings.json << 'EOF'
{
    "editor.formatOnSave": true
}
EOF

# Create issue template
cat > .github/ISSUE_TEMPLATE/bug_report.md << 'EOF'
---
name: Bug report
about: Create a report to help us improve
---

**Describe the bug**
A clear and concise description of what the bug is.
EOF

# Create environment file with "sensitive" data
cat > .env << 'EOF'
API_KEY=test_key_12345
SECRET_TOKEN=secret_token_67890
EOF

# Initialize git repo and create branches
git add .
git commit -m "Initial commit with edge cases"

# Create feature branch with Unicode content
git checkout -b feature/unicode
echo "Unicode branch specific content" > unicode_specific.txt
git add unicode_specific.txt
git commit -m "Add Unicode branch content"

# Create experiments branch
git checkout -b experiments
echo "Experimental content" > experimental.txt
git add experimental.txt
git commit -m "Add experimental content"

# Return to development branch
git checkout development

echo "Repository created successfully at: $(pwd)"
