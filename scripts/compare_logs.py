#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime, timezone
import yaml

def load_scenario(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def load_logs(path):
    logs = []
    if not os.path.exists(path):
        return logs
    with open(path, 'r') as f:
        content = f.read().strip()
        if not content: return logs
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
        except:
            pass
        for line in content.splitlines():
            if line.strip():
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return logs

def get_nested(d, path):
    for p in path.split('.'):
        if isinstance(d, dict) and p in d: d = d.get(p)
        else: return None
    return d

def check_integrity(logs, scenario, agent_name):
    errors = []
    exp_log_name = scenario.get("expected_log_name")
    exp_res_type = scenario.get("expected_resource_type")
    exp_payload = scenario.get("expected_payload_type")
    exp_fields = scenario.get("expected_fields", [])
    
    insert_ids = set()
    
    for idx, log in enumerate(logs):
        # Timestamps
        if "timestamp" not in log:
            errors.append(f"[{agent_name}] Log {idx} missing timestamp")
            
        # InsertId Uniqueness
        iid = log.get("insertId")
        if iid:
            if iid in insert_ids:
                errors.append(f"[{agent_name}] Duplicate insertId: {iid}")
            insert_ids.add(iid)
        else:
            errors.append(f"[{agent_name}] Log {idx} missing insertId")
            
        # LogName
        if exp_log_name and exp_log_name not in log.get("logName", ""):
            errors.append(f"[{agent_name}] Log {idx} logName doesn't contain '{exp_log_name}'")
            
        # Resource Type
        if exp_res_type and log.get("resource", {}).get("type") != exp_res_type:
            errors.append(f"[{agent_name}] Log {idx} resource.type isn't '{exp_res_type}'")
            
        # Payload and Fields
        has_json = "jsonPayload" in log
        has_text = "textPayload" in log
        
        if exp_payload == "json" and not has_json:
            errors.append(f"[{agent_name}] Log {idx} missing jsonPayload")
        elif exp_payload == "text" and not has_text:
            errors.append(f"[{agent_name}] Log {idx} missing textPayload")
            
        if has_json and exp_fields:
            payload = log.get("jsonPayload", {})
            for f in exp_fields:
                if f not in payload:
                    errors.append(f"[{agent_name}] Log {idx} missing expected field: {f}")
                    
    return errors

def compare_entries(baseline, upstream, keys):
    b_norm = {k: get_nested(baseline, k) for k in keys if get_nested(baseline, k) is not None}
    u_norm = {k: get_nested(upstream, k) for k in keys if get_nested(upstream, k) is not None}
    
    diffs = {}
    for k in set(b_norm.keys()) | set(u_norm.keys()):
        if k not in b_norm: diffs[k] = {"type": "missing_in_baseline", "upstream": u_norm[k]}
        elif k not in u_norm: diffs[k] = {"type": "missing_in_upstream", "baseline": b_norm[k]}
        elif b_norm[k] != u_norm[k]: diffs[k] = {"type": "mismatch", "baseline": b_norm[k], "upstream": u_norm[k]}
    return diffs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--upstream", required=True)
    parser.add_argument("--output-dir", default="outputs/reports")
    args = parser.parse_args()
    
    scenario = load_scenario(args.scenario)
    b_logs = load_logs(args.baseline)
    u_logs = load_logs(args.upstream)
    
    integrity_errors = check_integrity(b_logs, scenario, "Baseline") + check_integrity(u_logs, scenario, "Upstream")
    
    report = {
        "scenario": scenario.get("name", "Unknown"),
        "baseline_file": args.baseline,
        "upstream_file": args.upstream,
        "status": "PASS",
        "baseline_count": len(b_logs),
        "upstream_count": len(u_logs),
        "integrity_errors": integrity_errors,
        "mismatches": [],
        "missing_in_upstream": max(0, len(b_logs) - len(u_logs)),
        "extra_in_upstream": max(0, len(u_logs) - len(b_logs)),
        "notes": scenario.get("notes", "")
    }
    
    keys = scenario.get("comparison_keys", [])
    corr_key = scenario.get("correlation_key")
    
    if corr_key:
        b_dict = {str(get_nested(l, corr_key)): l for l in b_logs if get_nested(l, corr_key) is not None}
        u_dict = {str(get_nested(l, corr_key)): l for l in u_logs if get_nested(l, corr_key) is not None}
        
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
    out_file = os.path.join(args.output_dir, f"report_{scenario.get('id', 'test')}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json")
    with open(out_file, 'w') as f:
        json.dump(report, f, indent=2)
        
    print(f"\n--- E2E VALIDATION: {report['scenario']} ---")
    print(f"Status: {report['status']}")
    print(f"Baseline Logs: {len(b_logs)} | Upstream Logs: {len(u_logs)}")
    if integrity_errors:
        print(f"Integrity Errors ({len(integrity_errors)}):")
        for e in integrity_errors[:5]: print(f"  - {e}")
    if report["mismatches"]:
        print(f"Mismatches in {len(report['mismatches'])} logs.")
    print(f"Report saved to {out_file}\n")
    sys.exit(1 if report["status"] == "FAIL" else 0)

if __name__ == "__main__":
    main()
