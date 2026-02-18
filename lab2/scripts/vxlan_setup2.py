import argparse
import os
import sys
import urllib3
from pygnmi.client import gNMIclient

# Disable SSL warnings for lab environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_args():
    parser = argparse.ArgumentParser(
        description="Arista EOS VXLAN Configurator via gNMI (Model-Driven)",
        epilog="Example: python vxlan_setup_gnmi.py --file inventory.txt -i Loopback0 -m 10:1010 -f 1.1.1.2"
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
    parser.add_argument("--user", default="admin", help="gRPC username")
    parser.add_argument("--password", default="arista", help="gRPC password")
    
    return parser.parse_args()

def configure_vxlan_gnmi(target_host, args):
    """Connects to a single host and pushes the VXLAN config using gNMI Set."""
    # Arista gNMI typically listens on port 6030
    target = (target_host, 6030)
    
    # Define the updates using Arista Native YANG paths
    # These paths target the specific configuration nodes in the EOS database
    updates = [
        ('/vxlan/config/source-interface', args.interface),
        ('/vxlan/config/udp-port', 4789),
        ('/vxlan/config/flood-vtep', args.floodlist)
    ]

    # Add VLAN to VNI mappings to the update list
    for mapping in args.mappings:
        try:
            vlan_id, vni_id = mapping.split(':')
            # gNMI is strictly typed; VNI must be an integer
            updates.append((f'/vxlan/vlan-vnis/vlan-vni[vlan={vlan_id}]/config/vni', int(vni_id)))
        except ValueError:
            print(f"[-] Error: Invalid mapping format '{mapping}'. Skipping.")

    try:
        # Note the lowercase 'c' in gNMIclient
        with gNMIclient(target=target, username=args.user, password=args.password, insecure=True) as gc:
            print(f"[+] Connecting to {target_host} via gNMI...")
            # Perform the atomic Set operation
            results = gc.set(update=updates)
            print(f"[+] gNMI Set Request Successful on {target_host}")
            
    except Exception as e:
        print(f"[-] gNMI Error on {target_host}: {e}")

def main():
    args = get_args()
    hosts = []

    # Identify target hosts from CLI or File
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: Inventory file {args.file} not found.")
            sys.exit(1)
        with open(args.file, "r") as f:
            hosts = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        hosts = [args.host]

    # Iterate through hosts and apply config
    for host in hosts:
        configure_vxlan_gnmi(host, args)
        print("-" * 50)

if __name__ == "__main__":
    main()