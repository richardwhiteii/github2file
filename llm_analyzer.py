"""
LLM Analyzer Module for github2file

This module provides LLM-based repository analysis capabilities, including:
- Two-tier analysis (planning with high-tier model, execution with lower-tier model)
- Dependency analysis and critical path identification
- Derived compression with prompt generation
- XML/JSON artifact generation

Future Modularization Plan:
- repository_analyzer/: Repository structure and content analysis
- dependency_analyzer/: Dependency graph and critical path analysis
- compression_analyzer/: Derived compression logic
- artifact_generator/: XML/JSON artifact generation
- llm_providers/: LLM API interfaces

Rate Limiting:
- Implements exponential backoff
- Configurable through .env settings
"""

import os
import json
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime
from dotenv import load_dotenv
import anthropic
import backoff

# Load environment variables
load_dotenv()

class LLMInterface:
    """
    Manages interactions with LLM APIs.
    
    Future Modularization:
    -> llm_providers/
        - anthropic.py: Anthropic-specific implementation
        - base.py: Base interface
        - factory.py: Provider factory
    """
    def __init__(self):
        self.client = anthropic.Client(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.rate_limit = int(os.getenv('RATE_LIMIT', '20'))
        self.last_call = 0

    @backoff.on_exception(backoff.expo, anthropic.RateLimitError, max_tries=8)
    def call_llm(self, prompt: str, model: str = "claude-3-5-sonnet-latest") -> str:
        """Make a rate-limited call to the LLM API."""
        current_time = time.time()
        if current_time - self.last_call < (1 / self.rate_limit):
            time.sleep(1 / self.rate_limit)
        
        self.last_call = time.time()
        response = self.client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

class AnalysisPlan:
    """
    Represents the high-level analysis plan created by the planning model.
    
    Future Modularization:
    -> planning_engine/
        - strategy.py: Analysis strategy generation
        - validation.py: Plan validation
        - execution.py: Plan execution
    """
    def __init__(self, repository_path: str):
        self.repository_path = repository_path
        self.steps = []
        self.decisions = {}
        self.llm = LLMInterface()

    def create_plan(self) -> Dict:
        """Generate analysis plan using high-tier model."""
        prompt = f"""Analyze the repository at {self.repository_path} and create a detailed plan for:
        1. Identifying core components and dependencies
        2. Determining which content can be derived
        3. Creating efficient prompts for derivable content"""
        
        response = self.llm.call_llm(prompt, "claude-3-5-sonnet-latest")
        return json.loads(response)

class DependencyGraph:
    """
    Manages repository dependency analysis and critical path identification.
    
    Future Modularization:
    -> dependency_analyzer/
        - graph.py: Graph structure and traversal
        - critical_path.py: Critical path algorithms
        - cycle_detection.py: Cycle detection
    """
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.critical_paths = []
        self.cycles = []

    def add_dependency(self, source: str, target: str, dep_type: str):
        """Add a dependency between two files."""
        if source not in self.nodes:
            self.nodes[source] = set()
        self.nodes[source].add(target)
        self.edges.append({"source": source, "target": target, "type": dep_type})

    def detect_cycles(self) -> List[List[str]]:
        """Detect cyclic dependencies in the graph."""
        visited = set()
        path = []
        self.cycles = []

        def dfs(node):
            if node in path:
                cycle = path[path.index(node):]
                self.cycles.append(cycle)
                return
            if node in visited:
                return

            visited.add(node)
            path.append(node)
            for neighbor in self.nodes.get(node, []):
                dfs(neighbor)
            path.pop()

        for node in self.nodes:
            if node not in visited:
                dfs(node)

        return self.cycles

class DerivedCompression:
    """
    Handles identification and compression of derivable content.
    
    Future Modularization:
    -> compression_engine/
        - analyzer.py: Content analysis
        - prompt_generator.py: Prompt creation
        - validator.py: Content validation
    """
    def __init__(self, llm: LLMInterface):
        self.llm = llm
        self.derived_content = {}

    def analyze_content(self, file_path: str, content: str) -> Dict:
        """Analyze file content for potential derivation."""
        prompt = f"""Analyze this file content and determine if it can be derived from other files:
        Path: {file_path}
        Content: {content[:1000]}...
        
        Consider:
        1. Is this test code, documentation, or example code?
        2. What files would be needed to recreate this content?
        3. What prompt would enable accurate recreation?"""
        
        response = self.llm.call_llm(prompt)
        return json.loads(response)

# class LLMAnalyzer:
#     """
#     Main analyzer class that orchestrates the LLM-based repository analysis process.
    
#     Future Modularization:
#     -> core/
#         - analyzer.py: Main analysis logic
#         - config.py: Configuration management
#         - utils.py: Utility functions
#     """
#     def __init__(self, repository_url: str, verbose_level: int = 1):
#         self.repository_url = repository_url
#         self.verbose_level = verbose_level
#         self.llm = LLMInterface()
#         self.plan = AnalysisPlan(repository_url)
#         self.dependency_graph = DependencyGraph()
#         self.compression = DerivedCompression(self.llm)
        
#     def analyze(self, dry_run: bool = False) -> Dict:
#         """Perform complete repository analysis."""
#         # Create analysis plan
#         analysis_plan = self.plan.create_plan()
#         if dry_run:
#             return {"analysis_plan": analysis_plan}

#         # Execute analysis
#         self.log("Starting repository analysis...", 1)
#         results = self._execute_analysis(analysis_plan)
        
#         # Generate artifact
#         artifact = self._generate_artifact(results)
#         return artifact
class LLMAnalyzer:
    def __init__(self, repository_url: str, verbose_level: int = 1):
        self.repository_url = repository_url
        self.verbose_level = verbose_level
        self.client = anthropic.Client(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
    def analyze(self, dry_run: bool = False) -> Dict:
        try:
            # Simple test analysis
            prompt = f"""Please output a valid JSON object with this structure:
            {{
                "repository": "{self.repository_url}",
                "analysis": {{
                    "components": [],
                    "dependencies": []
                }}
            }}"""
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = response.content[0].text
            print(f"Raw response: {result}")  # Debug print
            
            return json.loads(result)
            
        except Exception as e:
            print(f"Error: {str(e)}")  # Debug print
            return {
                "error": str(e),
                "repository": self.repository_url
            }
        
    def _generate_artifact(self, results: Dict) -> Dict:
        """Generate the repository analysis artifact."""
        artifact = {
            "schema_version": "1.0",
            "metadata": {
                "repository_url": self.repository_url,
                "analysis_date": datetime.now().isoformat(),
                "llm_analyzer_version": "1.0"
            },
            "analysis_plan": results["analysis_plan"],
            "preserved_content": results["preserved_content"],
            "dependency_graph": {
                "critical_paths": self.dependency_graph.critical_paths,
                "cycles": self.dependency_graph.cycles
            },
            "derived_content": self.compression.derived_content,
            "recovery_guide": {
                "overview": "Guide to using this artifact and recreating derived content",
                "examples": [
                    {
                        "title": "Recreating Unit Tests",
                        "description": "Example of recreating tests using preserved content"
                    },
                    {
                        "title": "Generating Documentation",
                        "description": "Example of regenerating documentation"
                    }
                ]
            }
        }
        return artifact

    def log(self, message: str, level: int):
        """Log messages based on verbosity level."""
        if level <= self.verbose_level:
            print(f"[LLMAnalyzer] {message}")

    def _execute_analysis(self, analysis_plan: Dict) -> Dict:
        """Execute the analysis plan using lower-tier model."""
        try:
            # Initialize basic structure
            results = {
                "analysis_plan": analysis_plan,
                "preserved_content": {},
                "derived_content": {}
            }
            
            # Execute each step in the plan
            for step in analysis_plan.get("steps", []):
                step_result = self._execute_step(step)
                results[step["type"]] = step_result
                
            return results
            
        except Exception as e:
            self.log(f"Error executing analysis: {str(e)}", 1)
            return {
                "error": str(e),
                "analysis_plan": analysis_plan
            }