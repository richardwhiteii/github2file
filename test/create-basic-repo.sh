#!/bin/bash

# Set up main repository directory
REPO_NAME="test-repo-basic"
rm -rf "$REPO_NAME"
mkdir -p "$REPO_NAME"
cd "$REPO_NAME"

# Initialize git repository
git init
git checkout -b main

# Create directory structure
mkdir -p src/{python,go}
mkdir -p tests/{python,go}
mkdir -p examples
mkdir -p assets/{images,fonts,binaries}
mkdir -p docs
mkdir -p .github/workflows

# Create root level files
cat > README.md << 'EOF'
# Test Repository - Basic Test Case

This repository contains a basic test structure for repository processing tools.
It includes both Python and Go code examples.

## Structure
- src/: Source code in Python and Go
- tests/: Test files
- examples/: Example code
- docs/: Documentation
EOF

cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name="test-repo-basic",
    version="1.0.0",
    packages=find_packages(),
)
EOF

cat > go.mod << 'EOF'
module test-repo-basic

go 1.16
EOF

# Create main Python file
cat > main.py << 'EOF'
import sys
from src.python.calculator import Calculator
from src.python.utils import format_output

def main():
    calc = Calculator()
    result = calc.add(10, 20)
    formatted = format_output(result)
    print(formatted)

if __name__ == "__main__":
    main()
EOF

# Create main Go file
cat > server.go << 'EOF'
package main

import (
    "fmt"
    "net/http"
    "./src/go/calculator"
    "./src/go/utils"
)

func main() {
    calc := calculator.NewCalculator()
    result := calc.Add(10, 20)
    formatted := utils.FormatOutput(result)
    fmt.Println(formatted)
}
EOF

# Create Python source files
cat > src/python/__init__.py << 'EOF'
# Package initializer
EOF

cat > src/python/calculator.py << 'EOF'
class Calculator:
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        result = a + b
        self.history.append(f"Added {a} + {b} = {result}")
        return result
    
    def subtract(self, a, b):
        result = a - b
        self.history.append(f"Subtracted {a} - {b} = {result}")
        return result
    
    def multiply(self, a, b):
        result = a * b
        self.history.append(f"Multiplied {a} * {b} = {result}")
        return result
    
    def divide(self, a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self.history.append(f"Divided {a} / {b} = {result}")
        return result
EOF

cat > src/python/utils.py << 'EOF'
def format_output(value):
    """Format a numeric value for display"""
    if isinstance(value, (int, float)):
        return f"Result: {value:,.2f}"
    return f"Result: {value}"

def validate_input(value):
    """Validate numeric input"""
    try:
        return float(value)
    except ValueError:
        raise ValueError("Invalid numeric input")

def get_operation_symbol(operation):
    """Get the mathematical symbol for an operation"""
    symbols = {
        'add': '+',
        'subtract': '-',
        'multiply': '*',
        'divide': '/'
    }
    return symbols.get(operation, '?')
EOF

# Create Go source files
cat > src/go/calculator.go << 'EOF'
package calculator

import "fmt"

type Calculator struct {
    history []string
}

func NewCalculator() *Calculator {
    return &Calculator{
        history: make([]string, 0),
    }
}

func (c *Calculator) Add(a, b int) int {
    result := a + b
    c.history = append(c.history, fmt.Sprintf("Added %d + %d = %d", a, b, result))
    return result
}

func (c *Calculator) Subtract(a, b int) int {
    result := a - b
    c.history = append(c.history, fmt.Sprintf("Subtracted %d - %d = %d", a, b, result))
    return result
}

func (c *Calculator) GetHistory() []string {
    return c.history
}
EOF

cat > src/go/utils.go << 'EOF'
package utils

import "fmt"

func FormatOutput(value int) string {
    return fmt.Sprintf("Result: %d", value)
}

func ValidateInput(value string) (int, error) {
    var result int
    _, err := fmt.Sscanf(value, "%d", &result)
    return result, err
}

func GetVersion() string {
    return "1.0.0"
}
EOF

# Create test files
cat > tests/python/test_calculator.py << 'EOF'
import unittest
from src.python.calculator import Calculator

class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = Calculator()

    def test_add(self):
        self.assertEqual(self.calc.add(2, 3), 5)

    def test_subtract(self):
        self.assertEqual(self.calc.subtract(5, 3), 2)

if __name__ == '__main__':
    unittest.main()
EOF

cat > tests/python/test_utils.py << 'EOF'
import pytest
from src.python.utils import format_output, validate_input

def test_format_output():
    assert format_output(42) == "Result: 42.00"
    assert format_output(3.14159) == "Result: 3.14"

def test_validate_input():
    assert validate_input("42") == 42.0
    with pytest.raises(ValueError):
        validate_input("not a number")
EOF

cat > tests/go/calculator_test.go << 'EOF'
package calculator

import "testing"

func TestCalculator_Add(t *testing.T) {
    calc := NewCalculator()
    result := calc.Add(2, 3)
    if result != 5 {
        t.Errorf("Expected 5, got %d", result)
    }
}
EOF

cat > tests/go/utils_test.go << 'EOF'
package utils

import "testing"

func TestFormatOutput(t *testing.T) {
    result := FormatOutput(42)
    expected := "Result: 42"
    if result != expected {
        t.Errorf("Expected %s, got %s", expected, result)
    }
}
EOF

# Create example files
cat > examples/python_examples.py << 'EOF'
from src.python.calculator import Calculator

# Example usage of the Calculator class
calc = Calculator()
print(calc.add(5, 3))
print(calc.subtract(10, 4))
EOF

cat > examples/go_examples.go << 'EOF'
package main

import (
    "fmt"
    "./src/go/calculator"
)

func main() {
    calc := calculator.NewCalculator()
    fmt.Println(calc.Add(5, 3))
}
EOF

# Create documentation files
cat > docs/api.md << 'EOF'
# API Documentation

## Python API
- Calculator class
- Utility functions

## Go API
- Calculator struct
- Utility functions
EOF

cat > docs/setup.md << 'EOF'
# Setup Instructions

1. Install dependencies
2. Run tests
3. Use the calculator
EOF

cat > docs/contributing.md << 'EOF'
# Contributing Guidelines

Please follow these guidelines when contributing to the project.
EOF

# Create binary files
convert -size 100x100 xc:white assets/images/logo.png
convert -size 200x200 xc:white assets/images/diagram.jpg
dd if=/dev/urandom of=assets/binaries/sample.bin bs=1024 count=100

# Create GitHub workflow
cat > .github/workflows/ci.yml << 'EOF'
name: CI
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Run tests
      run: |
        python -m pytest tests/python/
        go test ./tests/go/...
EOF

# Create .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
*.pyo
.pytest_cache/
EOF

# Initialize git repo
git add .
git commit -m "Initial commit with basic test structure"

echo "Repository created successfully at: $(pwd)"
