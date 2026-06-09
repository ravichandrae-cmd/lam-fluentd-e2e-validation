#!/usr/bin/env python3
import argparse
import subprocess
import sys
import json
import os
from datetime import datetime, timezone

# Add the current directory to sys.path to import from compare_logs.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from compare_logs import load_scenario, check_integrity, compare_entries, get_nested, normalize_text

def fetch_logs(project, log_name, extra_filter=None, freshness=None, start_time=None, end_time=None):
    print(f"Fetching logs from project '{project}' with logName '{log_name}'...")
    query_parts = [f'logName="projects/{project}/logs/{log_name}"']
    if extra_filter:
        query_parts.append(f'({extra_filter})')
    if start_time:
        query_parts.append(f'timestamp>="{start_time}"')
    if end_time:
        query_parts.append(f'timestamp<="{end_time}"')
        
    query = " AND ".join(query_parts)
    
    cmd = ["gcloud", "logging", "read", query, f"--project={project}", "--format=json"]
    if freshness and not (start_time or end_time):
        cmd.append(f"--freshness={freshness}")
        
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if not result.stdout.strip():
            return []
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error fetching logs for {log_name}: {e.stderr}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Directly compare logs from GCP without exporting them locally.")
    parser.add_argument("--project", required=True, help="GCP Project ID")
    parser.add_argument("--baseline-log-name", required=True, help="Baseline log name")
    parser.add_argument("--upstream-log-name", required=True, help="Upstream log name")
    parser.add_argument("--scenario", required=True, help="Path to scenario YAML")
    parser.add_argument("--filter", help="Additional GCP filter string for both")
    parser.add_argument("--freshness", help="Time range (e.g., '1h'). Ignored if exact timings are provided.")
    parser.add_argument("--baseline-start", help="Exact start time for baseline logs (e.g. '2023-10-01T12:00:00Z')")
    parser.add_argument("--baseline-end", help="Exact end time for baseline logs")
    parser.add_argument("--upstream-start", help="Exact start time for upstream logs")
    parser.add_argument("--upstream-end", help="Exact end time for upstream logs")
    parser.add_argument("--output-dir", default="outputs/reports")
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    
    # Fetch logs in memory
    b_logs = fetch_logs(args.project, args.baseline_log_name, args.filter, args.freshness, args.baseline_start, args.baseline_end)
    u_logs = fetch_logs(args.project, args.upstream_log_name, args.filter, args.freshness, args.upstream_start, args.upstream_end)
    
    print(f"Found {len(b_logs)} baseline logs and {len(u_logs)} upstream logs.")
    
    integrity_errors = check_integrity(b_logs, scenario, "Baseline") + check_integrity(u_logs, scenario, "Upstream")
    
    keys = scenario.get("comparison_keys", [])
    corr_key = scenario.get("correlation_key")

    report = {
        "scenario": scenario.get("name", "Unknown"),
        "baseline_file": f"gcloud: {args.baseline_log_name}",
        "upstream_file": f"gcloud: {args.upstream_log_name}",
        "status": "PASS",
        "baseline_count": len(b_logs),
        "upstream_count": len(u_logs),
        "integrity_errors": integrity_errors,
        "mismatches": [],
        "missing_in_upstream": 0 if corr_key else max(0, len(b_logs) - len(u_logs)),
        "extra_in_upstream": 0 if corr_key else max(0, len(u_logs) - len(b_logs)),
        "notes": scenario.get("notes", "")
    }

    
    if corr_key:
        b_dict = {str(normalize_text(get_nested(l, corr_key))): l for l in b_logs if get_nested(l, corr_key) is not None}
        u_dict = {str(normalize_text(get_nested(l, corr_key))): l for l in u_logs if get_nested(l, corr_key) is not None}
        
        all_corr = sorted(set(b_dict.keys()) | set(u_dict.keys()))
        for k in all_corr:
            if k not in b_dict:
                report["extra_in_upstream"] += 1
            elif k not in u_dict:
                report["missing_in_upstream"] += 1
            else:
                diffs = compare_entries(b_dict[k], u_dict[k], keys)
                if diffs:
                    report["mismatches"].append({"correlation": k, "diffs": diffs})
    else:
        # Fallback to sequential pairing
        for i in range(min(len(b_logs), len(u_logs))):
            diffs = compare_entries(b_logs[i], u_logs[i], keys)
            if diffs:
                report["mismatches"].append({"index": i, "diffs": diffs})
                
    if integrity_errors or report["mismatches"] or report["missing_in_upstream"] or report["extra_in_upstream"]:
        report["status"] = "FAIL"
        
    os.makedirs(args.output_dir, exist_ok=True)
    out_file = os.path.join(args.output_dir, f"report_{scenario.get('id', 'test')}_gcloud_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json")
    with open(out_file, 'w') as f:
        json.dump(report, f, indent=2)
        
    print(f"\n=== E2E VALIDATION: {report['scenario']} ===")
    status_color = "\033[92m" if report['status'] == "PASS" else "\033[91m"
    status_icon = "✅" if report['status'] == "PASS" else "❌"
    print(f"{status_icon} Status: {status_color}{report['status']}\033[0m")
    print(f"Logs Checked: Baseline ({len(b_logs)}) 🆚 Upstream ({len(u_logs)})")
    
    if report["missing_in_upstream"] or report["extra_in_upstream"]:
        print(f"Missing: {report['missing_in_upstream']} | Extra: {report['extra_in_upstream']}")

    if integrity_errors:
        print(f"\n⚠️  Integrity Errors ({len(integrity_errors)}):")
        for e in integrity_errors[:5]: print(f"  - 🔴 {e}")
        if len(integrity_errors) > 5:
            print(f"  ... and {len(integrity_errors) - 5} more.")
            
    if report["mismatches"]:
        print(f"\n🔍 Mismatches Found in {len(report['mismatches'])} logs:")
        for m in report["mismatches"][:3]:
            ident = m.get("correlation", f"Index {m.get('index')}")
            print(f"  - 🧩 Log {ident} has {len(m['diffs'])} field difference(s)")
        if len(report["mismatches"]) > 3:
            print(f"  ... and {len(report['mismatches']) - 3} more logs.")
            
    print(f"\n📝 Full Report saved to: {out_file}\n")
    sys.exit(1 if report["status"] == "FAIL" else 0)

if __name__ == "__main__":
    main()
