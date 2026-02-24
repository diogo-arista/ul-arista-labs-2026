import pyeapi
import argparse
import urllib3
import json
import sys
import os

# Disable SSL warnings for lab environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_args():
    parser = argparse.ArgumentParser(
        description="Arista EOS VXLAN Configurator: Supports single host or inventory files.",
        epilog="Example: python vxlan_setup.py --file inventory.txt -i Loopback0 -m 10:1010 -f 1.1.1.2"
    )
    
    # Selection Group: Individual Host or Inventory File
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--host", help="Target switch hostname or IP")
    group.add_argument("--file", help="Path to text file containing hostnames")
    
    # VXLAN Parameters
    parser.add_argument("-i", "--interface", required=True, help="Source interface (e.g., Loopback0)")
    parser.add_argument("-m", "--mappings", nargs="+", required=True, help="Format vlan:vni (e.g., 10:1010)")
    parser.add_argument("-f", "--floodlist", nargs="+", required=True, help="Flood-list IPs (e.g., 1.1.1.2 1.1.1.3)")
    
    # Credentials
    parser.add_argument("--user", default="admin", help="eAPI username")
    parser.add_argument("--password", default="arista", help="eAPI password")
    
    return parser.parse_args()

def apply_config(target_host, args):
    """Connects to a single host and pushes the VXLAN config."""
    connection = pyeapi.client.connect(
        transport='https', host=target_host, 
        username=args.user, password=args.password, 
        port=443, verify=False
    )
    node = pyeapi.client.Node(connection)
    
    cmds = [
        "interface Vxlan1",
        f"vxlan source-interface {args.interface}",
        "vxlan udp-port 4789"
    ]
    
    for mapping in args.mappings:
        vlan_id, vni_id = mapping.split(':')
        cmds.append(f"vxlan vlan {vlan_id} vni {vni_id}")
            
    flood_ips = " ".join(args.floodlist)
    cmds.append(f"vxlan flood vtep {flood_ips}")

    try:
        print(f"[+] Configuring {target_host}...")
        node.config(cmds)
        print(f"[+] Success: Config pushed to {target_host}.")
    except Exception as e:
        print(f"[-] Failed to configure {target_host}: {e}")

def main():
    args = get_args()
    hosts = []

    # Identify targets
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: File {args.file} not found.")
            sys.exit(1)
        with open(args.file, "r") as f:
            hosts = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        hosts = [args.host]

    # Execute against all hosts
    for target in hosts:
        apply_config(target, args)
        print("-" * 40)

if __name__ == "__main__":
    main()