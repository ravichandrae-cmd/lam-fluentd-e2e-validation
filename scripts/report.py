#!/usr/bin/env python3
import os
import glob
import json

def generate_report(reports_dir="outputs/reports", output_file="outputs/reports/summary.md"):
    report_files = glob.glob(os.path.join(reports_dir, "*.json"))
    
    if not report_files:
        print("No JSON reports found in outputs/reports.")
        return

    markdown = "# E2E Log Validation Summary\n\n"
    
    for file_path in report_files:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        status = data.get("status", "UNKNOWN")
        emoji = "✅" if status == "PASS" else "❌"
        
        markdown += f"## {emoji} Scenario: {data.get('scenario', 'Unknown')}\n"
        markdown += f"- **Status**: {status}\n"
        markdown += f"- **Baseline File**: `{data.get('baseline_file', 'N/A')}`\n"
        markdown += f"- **Upstream File**: `{data.get('upstream_file', 'N/A')}`\n"
        
        matches = data.get("baseline_count", 0) - len(data.get("mismatches", []))
        markdown += f"- **Matched Logs**: {matches} / {data.get('baseline_count', 0)}\n"
        
        if data.get("notes"):
            markdown += f"- **Notes**: {data.get('notes')}\n"
            
        markdown += "\n### Discrepancies\n"
        
        integrity_errors = data.get("integrity_errors", [])
        mismatches = data.get("mismatches", [])
        
        if not integrity_errors and not mismatches:
            markdown += "None. All checks passed!\n\n"
        else:
            if integrity_errors:
                markdown += "**Integrity Errors:**\n"
                for err in integrity_errors:
                    markdown += f"- {err}\n"
            
            if mismatches:
                markdown += "**Field Mismatches:**\n"
                for m in mismatches:
                    identifier = m.get("correlation", m.get("index", "Unknown"))
                    markdown += f"- Log {identifier}:\n"
                    for field, diff in m.get("diffs", {}).items():
                        markdown += f"  - `{field}`: Baseline=`{diff.get('baseline')}` | Upstream=`{diff.get('upstream')}`\n"
        markdown += "---\n\n"
        
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(markdown)
    print(f"Summary report generated at: {output_file}")

if __name__ == "__main__":
    generate_report()
