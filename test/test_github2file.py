#!/usr/bin/env python3
import os
import sys
import subprocess
import unittest
import json
import shutil
from pathlib import Path

class TestGithub2File(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Add parent directory to Python path to import github2file
        cls.repo_root = Path(__file__).parent.parent
        sys.path.append(str(cls.repo_root))
        
        # Set up test directories
        cls.test_dir = Path(__file__).parent
        cls.output_dir = cls.test_dir / 'output'
        cls.repos_dir = cls.test_dir / 'repos'
        
        # Create directories
        cls.output_dir.mkdir(exist_ok=True)
        cls.repos_dir.mkdir(exist_ok=True)
        
        # Create test repositories
        print("Setting up test repositories...")
        subprocess.run(['chmod', '+x', cls.test_dir / 'create-basic-repo.sh'])
        subprocess.run(['chmod', '+x', cls.test_dir / 'create-edge-repo.sh'])
        
        # Run repository creation scripts from the repos directory
        os.chdir(cls.repos_dir)
        subprocess.run([str(cls.test_dir / 'create-basic-repo.sh')])
        subprocess.run([str(cls.test_dir / 'create-edge-repo.sh')])
        
        # Return to original directory
        os.chdir(cls.test_dir)

    def setUp(self):
        # Clear output directory before each test
        for file in self.output_dir.glob('*'):
            file.unlink()

    @classmethod
    def tearDownClass(cls):
        # Clean up repositories and output
        shutil.rmtree(cls.repos_dir, ignore_errors=True)
        shutil.rmtree(cls.output_dir, ignore_errors=True)

    def run_github2file(self, args):
        """Helper method to run github2file.py with correct paths"""
        github2file_path = self.repo_root / 'github2file.py'
        cmd = [sys.executable, str(github2file_path)] + args
        subprocess.run(cmd, check=True)

    def test_basic_python_filtering(self):
        """Test Python file filtering in basic repository"""
        self.run_github2file([
            '--lang', 'python',
            str(self.repos_dir / 'test-repo-basic'),
            '--output', str(self.output_dir / 'basic_python.txt')
        ])
        
        with open(self.output_dir / 'basic_python.txt') as f:
            content = f.read()
            
        # Check that main source files are included
        self.assertIn('calculator.py', content)
        self.assertIn('utils.py', content)
        
        # Check that test files are excluded
        self.assertNotIn('test_calculator.py', content)
        self.assertNotIn('test_utils.py', content)
        
        # Check that example files are excluded
        self.assertNotIn('python_examples.py', content)

    def test_basic_go_filtering(self):
        """Test Go file filtering in basic repository"""
        self.run_github2file([
            '--lang', 'go',
            str(self.repos_dir / 'test-repo-basic'),
            '--output', str(self.output_dir / 'basic_go.txt')
        ])
        
        with open(self.output_dir / 'basic_go.txt') as f:
            content = f.read()
            
        # Check core files are included
        self.assertIn('calculator.go', content)
        self.assertIn('utils.go', content)
        
        # Check test files are excluded
        self.assertNotIn('calculator_test.go', content)
        self.assertNotIn('utils_test.go', content)

    def test_edge_case_unicode(self):
        """Test handling of Unicode content and filenames"""
        self.run_github2file([
            '--lang', 'python',
            str(self.repos_dir / 'test-repo-edge-cases'),
            '--output', str(self.output_dir / 'edge_unicode.txt')
        ])
        
        with open(self.output_dir / 'edge_unicode.txt', encoding='utf-8') as f:
            content = f.read()
            
        # Check Unicode content is preserved
        self.assertIn('こんにちは', content)
        self.assertIn('Привет', content)
        self.assertIn('مرحبا', content)

    def test_edge_case_deep_paths(self):
        """Test handling of deeply nested paths"""
        self.run_github2file([
            '--lang', 'python',
            str(self.repos_dir / 'test-repo-edge-cases'),
            '--output', str(self.output_dir / 'edge_paths.txt')
        ])
        
        with open(self.output_dir / 'edge_paths.txt') as f:
            content = f.read()
            
        # Check deeply nested file is included
        self.assertIn('deeply/nested/directory/module.py', content)

    def test_keep_comments_flag(self):
        """Test the --keep-comments flag"""
        # First without keep-comments
        self.run_github2file([
            '--lang', 'python',
            str(self.repos_dir / 'test-repo-basic'),
            '--output', str(self.output_dir / 'no_comments.txt')
        ])
        
        # Then with keep-comments
        self.run_github2file([
            '--lang', 'python',
            '--keep-comments',
            str(self.repos_dir / 'test-repo-basic'),
            '--output', str(self.output_dir / 'with_comments.txt')
        ])
        
        with open(self.output_dir / 'no_comments.txt') as f:
            no_comments = f.read()
        with open(self.output_dir / 'with_comments.txt') as f:
            with_comments = f.read()
            
        # Comments should be present in with_comments but not in no_comments
        self.assertNotIn('"""Format a numeric value for display"""', no_comments)
        self.assertIn('"""Format a numeric value for display"""', with_comments)

    def test_claude_output_format(self):
        """Test Claude output format"""
        self.run_github2file([
            '--lang', 'python',
            '--claude',
            str(self.repos_dir / 'test-repo-basic'),
            '--output', str(self.output_dir / 'claude_format.txt')
        ])
        
        with open(self.output_dir / 'claude_format.txt') as f:
            content = f.read()
            
        # Check Claude format elements
        self.assertIn('<documents>', content)
        self.assertIn('<document index=', content)
        self.assertIn('<source>', content)
        self.assertIn('<document_content>', content)
        self.assertIn('</documents>', content)

    def test_include_all_flag(self):
        """Test the --all flag for including all files"""
        self.run_github2file([
            '--lang', 'python',
            '--all',
            str(self.repos_dir / 'test-repo-basic'),
            '--output', str(self.output_dir / 'include_all.txt')
        ])
        
        with open(self.output_dir / 'include_all.txt') as f:
            content = f.read()
            
        # Should include files that would normally be filtered
        self.assertIn('test_calculator.py', content)
        self.assertIn('python_examples.py', content)

    def test_binary_file_handling(self):
        """Test handling of binary files"""
        self.run_github2file([
            '--lang', 'python',
            '--all',
            str(self.repos_dir / 'test-repo-basic'),
            '--output', str(self.output_dir / 'binary_handling.txt')
        ])
        
        with open(self.output_dir / 'binary_handling.txt') as f:
            content = f.read()
            
        # Binary files should be noted but not included
        self.assertIn('Binary file', content)
        self.assertIn('logo.png', content)
        self.assertIn('sample.bin', content)

if __name__ == '__main__':
    # Set up logging for the tests
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the tests
    unittest.main(verbosity=2)
