import pyeapi
import argparse
import urllib3
import os
import json
from datetime import datetime

# Disable SSL warnings for lab environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_args():
    parser = argparse.ArgumentParser(
        description="Arista EOS Inventory Collector with Raw JSON Dump",
        epilog="Example: python script.py --file inventory.txt"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--hosts", nargs="+", help="Space-separated list of hostnames/IPs")
    group.add_argument("--file", help="Path to a text file containing hostnames")
    
    parser.add_argument("--user", default="admin", help="eAPI username")
    parser.add_argument("--password", default="arista", help="eAPI password")
    
    return parser.parse_args()

def get_switch_info(hostname, user, password):
    connection = pyeapi.client.connect(
        transport="https",
        host=hostname,
        username=user,
        password=password,
        port=443,
        verify=False
    )
    node = pyeapi.client.Node(connection)
    try:
        # Execute 'show version'
        response = node.enable("show version")
        raw_data = response[0]['result']
        
        mem_total = raw_data.get('memTotal')
        mem_free = raw_data.get('memFree')
        mem_pct = (mem_free / mem_total) * 100 if mem_total else 0
        
        boot_epoch = raw_data.get('bootupTimestamp')
        boot_readable = datetime.fromtimestamp(boot_epoch).strftime('%Y-%m-%d %H:%M:%S') if boot_epoch else "N/A"
        
        # Summary for the table
        summary = {
            "host": hostname,
            "model": raw_data.get('modelName'),
            "version": raw_data.get('version'),
            "bootTime": boot_readable,
            "memFreePct": round(mem_pct, 2),
            "status": "success"
        }
        
        return summary, raw_data
        
    except Exception as e:
        return {"host": hostname, "error": str(e), "status": "failed"}, None

def main():
    args = get_args()
    target_hosts = []
    summaries = []
    raw_dumps = {}

    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File {args.file} not found.")
            return
        with open(args.file, "r") as f:
            target_hosts = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        target_hosts = args.hosts

    for host in target_hosts:
        summary, raw = get_switch_info(host, args.user, args.password)
        summaries.append(summary)
        if raw:
            raw_dumps[host] = raw

    # 1. Print the Summary Table
    header = f"{'HOSTNAME':<22} | {'MODEL':<12} | {'VERSION':<10} | {'BOOT TIME':<20} | {'MEM %'}"
    print(f"\n{'='*15} INVENTORY SUMMARY {'='*15}")
    print(header)
    print("-" * len(header))
    for info in summaries:
        if info["status"] == "failed":
            print(f"{info['host']:<22} | ERROR: {info['error']}")
        else:
            print(f"{info['host']:<22} | {info['model']:<12} | {info['version']:<10} | {info['bootTime']:<20} | {info['memFreePct']}%")
    print("-" * len(header))

    # 2. Print the Raw JSON Dumps
    print(f"\n{'='*15} RAW eAPI DATA (JSON) {'='*15}")
    for host, data in raw_dumps.items():
        print(f"\n[ Host: {host} ]")
        # Pretty print with indent=4
        print(json.dumps(data, indent=4))
    print(f"\n{'='*50}\n")

if __name__ == "__main__":
    main()