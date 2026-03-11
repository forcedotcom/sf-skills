#!/usr/bin/env python3
"""
Analyze Salesforce Apex triggers for common anti-patterns.

Usage:
    python analyze_trigger.py <TriggerName>

Requirements:
    - Salesforce CLI authenticated to target org
    - Python 3.9+
"""

import sys
import subprocess
import json
import re
from typing import List, Dict, Tuple

class TriggerAnalyzer:
    def __init__(self, trigger_name: str):
        self.trigger_name = trigger_name
        self.trigger_body = ""
        self.issues = {
            'dml_in_loops': [],
            'soql_in_loops': [],
            'missing_bulk': [],
        }
        self.complexity_score = 0
        
    def retrieve_trigger(self) -> bool:
        """Retrieve trigger source code from Salesforce org."""
        try:
            cmd = [
                'sf', 'apex', 'get', 'trigger',
                '--trigger-name', self.trigger_name,
                '--json'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"Error retrieving trigger: {result.stderr}")
                return False
                
            data = json.loads(result.stdout)
            self.trigger_body = data.get('result', {}).get('body', '')
            return True
            
        except Exception as e:
            print(f"Failed to retrieve trigger: {e}")
            return False
    
    def analyze_dml_in_loops(self) -> None:
        """Detect DML operations inside for loops."""
        lines = self.trigger_body.split('\n')
        in_loop = False
        loop_start = 0
        
        dml_patterns = [
            r'\binsert\s+', r'\bupdate\s+', r'\bdelete\s+',
            r'\bundelete\s+', r'\bupsert\s+'
        ]
        
        for i, line in enumerate(lines, 1):
            # Track loop entry
            if re.search(r'\bfor\s*\(', line):
                in_loop = True
                loop_start = i
                
            # Track loop exit
            if in_loop and line.strip() == '}':
                # Check if this closes the loop (simplified heuristic)
                in_loop = False
                
            # Check for DML in loop
            if in_loop:
                for pattern in dml_patterns:
                    if re.search(pattern, line):
                        self.issues['dml_in_loops'].append({
                            'line': i,
                            'code': line.strip(),
                            'loop_start': loop_start
                        })
    
    def analyze_soql_in_loops(self) -> None:
        """Detect SOQL queries inside for loops."""
        lines = self.trigger_body.split('\n')
        in_loop = False
        loop_start = 0
        
        soql_pattern = r'\[SELECT\s+'
        
        for i, line in enumerate(lines, 1):
            if re.search(r'\bfor\s*\(', line):
                in_loop = True
                loop_start = i
                
            if in_loop and line.strip() == '}':
                in_loop = False
                
            if in_loop and re.search(soql_pattern, line, re.IGNORECASE):
                self.issues['soql_in_loops'].append({
                    'line': i,
                    'code': line.strip(),
                    'loop_start': loop_start
                })
    
    def analyze_bulkification(self) -> None:
        """Check for proper bulkification patterns."""
        # Simple heuristic: if we have DML in loops, bulkification is missing
        if self.issues['dml_in_loops']:
            self.issues['missing_bulk'].append({
                'message': 'DML operations should be collected and executed outside loops',
                'affected_lines': [issue['line'] for issue in self.issues['dml_in_loops']]
            })
            
        if self.issues['soql_in_loops']:
            self.issues['missing_bulk'].append({
                'message': 'SOQL queries should be moved outside loops or use Maps for lookups',
                'affected_lines': [issue['line'] for issue in self.issues['soql_in_loops']]
            })
    
    def calculate_complexity(self) -> None:
        """Calculate overall complexity score (1-10)."""
        score = 1
        
        # Add points for each issue type
        score += len(self.issues['dml_in_loops']) * 2
        score += len(self.issues['soql_in_loops']) * 2
        score += len(self.issues['missing_bulk']) * 1
        
        # Count trigger contexts
        contexts = len(re.findall(r'Trigger\.(isBefore|isAfter)', self.trigger_body))
        score += contexts
        
        # Count lines of code (normalized)
        loc = len([l for l in self.trigger_body.split('\n') if l.strip()])
        score += min(loc // 10, 3)
        
        self.complexity_score = min(score, 10)
    
    def recommend_approach(self) -> str:
        """Recommend refactoring approach based on analysis."""
        if self.complexity_score <= 3:
            return "Simple handler class with separate methods for each trigger context"
        elif self.complexity_score <= 6:
            return "Handler class with bulkified collections and helper methods"
        else:
            return "Unified handler framework with separate concern classes (validation, DML, etc.)"
    
    def generate_report(self) -> None:
        """Print analysis report."""
        print("\n" + "="*70)
        print(f"TRIGGER ANALYSIS REPORT: {self.trigger_name}")
        print("="*70 + "\n")
        
        print(f"Complexity Score: {self.complexity_score}/10")
        print(f"Recommended Approach: {self.recommend_approach()}\n")
        
        # DML in loops
        if self.issues['dml_in_loops']:
            print("⚠️  DML OPERATIONS IN LOOPS:")
            for issue in self.issues['dml_in_loops']:
                print(f"   Line {issue['line']}: {issue['code']}")
                print(f"   └─ Loop started at line {issue['loop_start']}")
            print()
        else:
            print("✓ No DML operations found in loops\n")
        
        # SOQL in loops
        if self.issues['soql_in_loops']:
            print("⚠️  SOQL QUERIES IN LOOPS:")
            for issue in self.issues['soql_in_loops']:
                print(f"   Line {issue['line']}: {issue['code']}")
                print(f"   └─ Loop started at line {issue['loop_start']}")
            print()
        else:
            print("✓ No SOQL queries found in loops\n")
        
        # Bulkification
        if self.issues['missing_bulk']:
            print("⚠️  BULKIFICATION RECOMMENDATIONS:")
            for issue in self.issues['missing_bulk']:
                print(f"   • {issue['message']}")
                print(f"     Affected lines: {', '.join(map(str, issue['affected_lines']))}")
            print()
        else:
            print("✓ Bulkification patterns look good\n")
        
        print("="*70)
        print("NEXT STEPS:")
        print("1. Review the handler patterns reference guide")
        print("2. Create handler class with bulk-safe collections")
        print("3. Extract trigger logic into handler methods")
        print("4. Generate comprehensive tests using the template")
        print("="*70 + "\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_trigger.py <TriggerName>")
        sys.exit(1)
    
    trigger_name = sys.argv[1]
    
    print(f"Analyzing trigger: {trigger_name}...")
    
    analyzer = TriggerAnalyzer(trigger_name)
    
    # For demo purposes, use inline example if retrieval fails
    if not analyzer.retrieve_trigger():
        print("⚠️  Could not retrieve from org. Using example trigger for demonstration.\n")
        # Use the example from the SKILL.md
        analyzer.trigger_body = """trigger OpportunityTrigger on Opportunity (before insert, before update, after update) {
    if (Trigger.isBefore && Trigger.isInsert) {
        for (Opportunity o : Trigger.new) {
            if (o.StageName == 'Closed Won' && (o.Amount == null || o.Amount < 1000)) {
                o.addError('Closed Won opportunities must have Amount ≥ 1000.');
            }
        }
    }
    if (Trigger.isBefore && Trigger.isUpdate) {
        for (Opportunity o : Trigger.new) {
            Opportunity oldO = Trigger.oldMap.get(o.Id);
            if (o.StageName != oldO.StageName) {
                o.Description = 'Stage changed from ' + oldO.StageName + ' to ' + o.StageName;
            }
        }
    }
    if (Trigger.isAfter && Trigger.isUpdate) {
        for (Opportunity o : Trigger.new) {
            Opportunity oldO = Trigger.oldMap.get(o.Id);
            if (o.StageName == 'Closed Won' && oldO.StageName != 'Closed Won') {
                Task t = new Task(
                    WhatId = o.Id,
                    OwnerId = o.OwnerId,
                    Subject = 'Send thank-you',
                    Status = 'Not Started',
                    Priority = 'Normal',
                    ActivityDate = Date.today()
                );
                insert t;
            }
        }
    }
}"""
    
    # Run analysis
    analyzer.analyze_dml_in_loops()
    analyzer.analyze_soql_in_loops()
    analyzer.analyze_bulkification()
    analyzer.calculate_complexity()
    
    # Generate report
    analyzer.generate_report()


if __name__ == '__main__':
    main()
