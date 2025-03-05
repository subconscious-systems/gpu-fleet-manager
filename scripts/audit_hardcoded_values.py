#!/usr/bin/env python3
"""
Hardcoded Values Auditor

This script scans the codebase for potentially hardcoded configuration values
that should be moved to the centralized configuration system.

Usage:
    python audit_hardcoded_values.py [directory]

Arguments:
    directory - Path to the directory to scan (default: current directory)
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Set, Tuple
import json
from collections import defaultdict
import csv

# Patterns to match for potential hardcoded values
PATTERNS = {
    # URL patterns
    "urls": r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/[a-zA-Z0-9_./-]+)*',
    
    # IP addresses
    "ip_addresses": r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    
    # Database connection strings
    "db_connections": r'(mysql|postgresql|mongodb|redis)://[a-zA-Z0-9:._-]+@[a-zA-Z0-9._-]+:[0-9]+',
    
    # API keys (various formats)
    "api_keys": r'(api[_-]?key|apikey|key|token|secret)[=: ]["\'`]([a-zA-Z0-9]{16,})["\'`]',
    
    # Credentials
    "credentials": r'(username|password|user|pass)[=: ]["\'`]([^"\'`\s]+)["\'`]',
    
    # Ports
    "ports": r'(port)[=: ]["\']?(\d{2,5})["\']?',
    
    # File paths
    "file_paths": r'["\']/(var|etc|usr|opt|tmp|home)/[a-zA-Z0-9._/-]+["\']',
    
    # AWS keys
    "aws_keys": r'(AKIA[0-9A-Z]{16})',
    
    # Email addresses
    "emails": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
}

# List of directories to exclude
EXCLUDE_DIRS = [
    ".git",
    "__pycache__",
    "venv",
    "node_modules",
    "build",
    "dist",
    ".vscode",
    ".idea",
]

# List of file extensions to exclude
EXCLUDE_EXTENSIONS = [
    ".pyc",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".ttf",
    ".woff",
    ".woff2",
    ".eot",
    ".mp3",
    ".mp4",
    ".zip",
    ".pdf",
    ".gz",
    ".tar",
]

# Exclude test files and documentation
EXCLUDE_PATTERNS = [
    r"test_.*\.py$",
    r".*_test\.py$",
    r"conftest\.py$",
    r".*\.md$",
    r".*\.rst$",
]

class HardcodedValuesFinder:
    """Finds hardcoded values in a codebase"""
    
    def __init__(self, directory: str):
        """Initialize with the directory to scan"""
        self.directory = Path(directory).resolve()
        self.findings = defaultdict(list)
        self.total_files = 0
        self.scanned_files = 0
        self.excluded_files = 0
        
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if a file should be excluded from scanning"""
        # Check if parent directory should be excluded
        for parent in file_path.parents:
            if parent.name in EXCLUDE_DIRS:
                return True
                
        # Check file extension
        if file_path.suffix in EXCLUDE_EXTENSIONS:
            return True
            
        # Check filename patterns
        file_name = file_path.name
        for pattern in EXCLUDE_PATTERNS:
            if re.match(pattern, file_name):
                return True
                
        return False
        
    def scan_file(self, file_path: Path) -> Dict[str, List[Tuple[int, str]]]:
        """
        Scan a single file for hardcoded values
        
        Returns a dictionary of pattern_name -> list of (line_number, line_content) tuples
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.readlines()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return {}
            
        results = defaultdict(list)
        
        for i, line in enumerate(content, 1):
            # Skip comments
            if line.strip().startswith(('#', '//', '/*', '*', '*/')):
                continue
                
            # Check each pattern
            for pattern_name, pattern in PATTERNS.items():
                if re.search(pattern, line):
                    results[pattern_name].append((i, line.strip()))
                    
        return results
        
    def scan_directory(self) -> Dict[str, Dict[str, List[Tuple[int, str]]]]:
        """
        Scan the directory recursively for hardcoded values
        
        Returns a dictionary of file_path -> pattern_name -> list of (line_number, line_content) tuples
        """
        for root, dirs, files in os.walk(self.directory):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            # Process each file
            for file in files:
                self.total_files += 1
                file_path = Path(root) / file
                
                if self.should_exclude_file(file_path):
                    self.excluded_files += 1
                    continue
                    
                self.scanned_files += 1
                relative_path = file_path.relative_to(self.directory)
                
                file_results = self.scan_file(file_path)
                if file_results:
                    self.findings[str(relative_path)] = file_results
                    
        return self.findings
        
    def generate_summary(self) -> Dict[str, Dict[str, int]]:
        """Generate a summary of findings by pattern type"""
        summary = defaultdict(lambda: defaultdict(int))
        
        for file_path, patterns in self.findings.items():
            for pattern_name, findings in patterns.items():
                file_extension = Path(file_path).suffix
                if not file_extension:
                    file_extension = '(no extension)'
                    
                summary[pattern_name][file_extension] += len(findings)
                
        return summary
        
    def export_to_csv(self, output_file: str) -> None:
        """Export findings to a CSV file"""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['File', 'Pattern Type', 'Line Number', 'Content'])
            
            for file_path, patterns in self.findings.items():
                for pattern_name, findings in patterns.items():
                    for line_number, content in findings:
                        writer.writerow([file_path, pattern_name, line_number, content])
                        
    def export_to_json(self, output_file: str) -> None:
        """Export findings to a JSON file"""
        # Convert defaultdict to regular dict for JSON serialization
        output = {}
        for file_path, patterns in self.findings.items():
            output[file_path] = {}
            for pattern_name, findings in patterns.items():
                output[file_path][pattern_name] = [
                    {"line": line_number, "content": content}
                    for line_number, content in findings
                ]
                
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
            
    def print_report(self) -> None:
        """Print a report of findings to stdout"""
        total_findings = sum(len(findings) for patterns in self.findings.values() for findings in patterns.values())
        
        print("\n=== Hardcoded Values Audit Report ===\n")
        print(f"Directory: {self.directory}")
        print(f"Total files: {self.total_files}")
        print(f"Scanned files: {self.scanned_files}")
        print(f"Excluded files: {self.excluded_files}")
        print(f"Files with potential hardcoded values: {len(self.findings)}")
        print(f"Total potential hardcoded values found: {total_findings}")
        
        # Print summary by pattern type
        summary = self.generate_summary()
        print("\n=== Findings by Pattern Type ===\n")
        
        for pattern_name, extensions in sorted(summary.items(), key=lambda x: sum(x[1].values()), reverse=True):
            total = sum(extensions.values())
            print(f"{pattern_name}: {total} findings")
            for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
                print(f"  {ext}: {count}")
                
        # Print top files with the most findings
        print("\n=== Top Files with Hardcoded Values ===\n")
        
        top_files = sorted(
            [(file_path, sum(len(findings) for findings in patterns.values()))
             for file_path, patterns in self.findings.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        for file_path, count in top_files[:10]:  # Show top 10 files
            print(f"{file_path}: {count} findings")
            
        print("\nRecommendation: Review these findings and migrate hardcoded values to the configuration system.")

def main():
    """Parse arguments and run the audit"""
    parser = argparse.ArgumentParser(description="Scan codebase for hardcoded values")
    parser.add_argument('directory', nargs='?', default='.', help='Directory to scan (default: current directory)')
    parser.add_argument('--output-csv', help='Export findings to a CSV file')
    parser.add_argument('--output-json', help='Export findings to a JSON file')
    
    args = parser.parse_args()
    
    finder = HardcodedValuesFinder(args.directory)
    finder.scan_directory()
    finder.print_report()
    
    if args.output_csv:
        finder.export_to_csv(args.output_csv)
        print(f"\nFindings exported to CSV: {args.output_csv}")
        
    if args.output_json:
        finder.export_to_json(args.output_json)
        print(f"\nFindings exported to JSON: {args.output_json}")

if __name__ == '__main__':
    main()
