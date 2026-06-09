#!/usr/bin/env python3
import argparse

def main():
    parser = argparse.ArgumentParser(description="Export logs from GCP.")
    parser.add_argument("--project", required=True, help="GCP Project ID")
    parser.add_argument("--log-name", required=True, help="Log name to filter")
    parser.add_argument("--filter", help="Additional GCP filter string")
    parser.add_argument("--freshness", help="Time range (e.g., '1h')")
    parser.add_argument("--output", required=True, help="Output file path")
    args = parser.parse_args()

    print(f"Exporting logs from project '{args.project}' with logName '{args.log_name}'...")
    
    # Construct the base filter
    query_parts = []
    # Using logName fully qualified as expected by Cloud Logging
    query_parts.append(f'logName="projects/{args.project}/logs/{args.log_name}"')
    
    if args.filter:
        query_parts.append(f'({args.filter})')
        
    query = " AND ".join(query_parts)
    
    cmd = [
        "gcloud", "logging", "read", query,
        f"--project={args.project}",
        "--format=json"
    ]
    
    if args.freshness:
        cmd.append(f"--freshness={args.freshness}")
        
    print(f"Running command: {' '.join(cmd)}")
    
    # Ensure the output directory exists
    import os
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    
    import subprocess
    import sys
    try:
        with open(args.output, "w") as out_file:
            subprocess.run(cmd, stdout=out_file, check=True)
        print(f"Successfully exported logs to {args.output}")
    except subprocess.CalledProcessError as e:
        print(f"Error executing gcloud command: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: 'gcloud' command not found. Please ensure Google Cloud SDK is installed and in your PATH.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
