import argparse
import os
import sys
import urllib3
from pygnmi.client import gNMIclient

# Disable warnings for lab SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_args():
    parser = argparse.ArgumentParser(description="Arista EOS VXLAN Configurator via gNMI")
    parser.add_argument("--host", required=True, help="Target switch IP/Hostname")
    parser.add_argument("-i", "--interface", required=True, help="Source interface (e.g., Loopback0)")
    parser.add_argument("-m", "--mappings", nargs="+", required=True, help="Format vlan:vni (e.g., 10:1010)")
    parser.add_argument("-f", "--floodlist", nargs="+", required=True, help="Flood-list IPs")
    parser.add_argument("--user", default="admin", help="gRPC username")
    parser.add_argument("--password", default="arista", help="gRPC password")
    return parser.parse_args()

def configure_vxlan_gnmi(args):
    # gNMI target details (Arista uses port 6030 by default)
    target = (args.host, 6030)
    
    # Define the YANG paths and the updates
    # Note: Arista uses native Arista-vlan-config models for specific VXLAN mappings
    updates = [
        # Set Source Interface
        (f'/interfaces/interface[name=Vxlan1]/vxlan/source-interface', args.interface),
        # Set UDP Port
        (f'/interfaces/interface[name=Vxlan1]/vxlan/udp-port', 4789)
    ]

    # Add VLAN to VNI mappings
    for mapping in args.mappings:
        vlan_id, vni_id = mapping.split(':')
        updates.append((f'/interfaces/interface[name=Vxlan1]/vxlan/vlan-vni-map[vlan={vlan_id}]/vni', int(vni_id)))

    # Add Flood List
    # gNMI allows lists to be passed directly as a value or defined per leaf
    updates.append((f'/interfaces/interface[name=Vxlan1]/vxlan/flood-vtep', args.floodlist))

    try:
        with gNMIClient(target=target, username=args.user, password=args.password, insecure=True) as gc:
            print(f"[+] Connecting to {args.host} via gNMI port 6030...")
            # Perform a gNMI 'Set' operation
            results = gc.set(update=updates)
            print(f"[+] gNMI Set Request Successful on {args.host}")
            
    except Exception as e:
        print(f"[-] gNMI Error: {e}")

if __name__ == "__main__":
    main()