import pyeapi
import argparse
import urllib3
import os
import json

# Disable SSL warnings for lab environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_args():
    parser = argparse.ArgumentParser(
        description="Arista EOS Inventory & Memory Collector",
        epilog="Example: python script.py --hosts ceos1 --json"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--hosts", nargs="+", help="Space-separated list of hostnames/IPs")
    group.add_argument("--file", help="Path to a text file containing hostnames")
    
    parser.add_argument("--user", default="admin", help="eAPI username")
    parser.add_argument("--password", default="arista", help="eAPI password")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    
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
        data = response[0]['result']
        
        mem_total = data.get('memTotal')
        mem_free = data.get('memFree')
        
        # Calculate percentage free for the table view
        mem_pct = (mem_free / mem_total) * 100 if mem_total else 0
        
        return {
            "host": hostname,
            "model": data.get('modelName'),
            "version": data.get('version'),
            "mac": data.get('systemMacAddress'),
            "memTotal": mem_total,
            "memFree": mem_free,
            "memFreePct": round(mem_pct, 2),
            "status": "success"
        }
    except Exception as e:
        return {"host": hostname, "error": str(e), "status": "failed"}

def main():
    args = get_args()
    target_hosts = []
    results = []

    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File {args.file} not found.")
            return
        with open(args.file, "r") as f:
            target_hosts = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        target_hosts = args.hosts

    for host in target_hosts:
        results.append(get_switch_info(host, args.user, args.password))

    if args.json:
        print(json.dumps(results, indent=4))
    else:
        # Adjusted header for memory columns
        header = f"{'HOSTNAME':<22} | {'MODEL':<10} | {'VERSION':<10} | {'MEM FREE %':<10} | {'MAC ADDRESS'}"
        print(f"\n{header}")
        print("-" * len(header))
        for info in results:
            if info["status"] == "failed":
                print(f"{info['host']:<22} | ERROR: {info['error']}")
            else:
                print(f"{info['host']:<22} | {info['model']:<10} | {info['version']:<10} | {info['memFreePct']:<10}% | {info['mac']}")
        print("-" * len(header) + "\n")

if __name__ == "__main__":
    main()