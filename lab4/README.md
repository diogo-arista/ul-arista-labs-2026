# Lab 4: Network Automation with Arista AVD

## Introduction

In the previous labs you explored network fundamentals (OSPF, VXLAN), interacted with Arista devices via CLI, and used Python scripts with eAPI and gNMI to configure and collect data from switches.

In this lab you will move to the next level of automation: **Arista AVD (Arista Validated Designs)**. AVD is an open-source Ansible collection that brings a "network-as-code" workflow to Arista fabrics. Instead of writing individual configuration commands, you describe *what* you want the network to look like in YAML files, and AVD takes care of *how* to configure every device.

The AVD workflow has four stages:

```
  DESIGN       BUILD        DEPLOY       VALIDATE
  ------       -----        ------       --------
  YAML files → EOS configs → Push to  → Automated
  (intent)     (generated)   devices    tests (ANTA)
                    |
                    └─→ Documentation (auto-generated)
```

## Learning Objectives

By the end of this lab you will be able to:

1. Explain the AVD workflow and the role of each stage
2. Understand the AVD data model (group_vars hierarchy)
3. Generate EOS configurations from a YAML intent model
4. Deploy configurations to network devices using Ansible and eAPI
5. Run automated network validation with ANTA
6. Read and understand the auto-generated fabric documentation
7. Perform a Day 2 change (add a VLAN) using the same workflow

## Lab Topology

```
                        MANAGEMENT NETWORK
                          172.20.20.0/24
              .11              .12              .13
          ┌───────────────────────────────────────────┐
          │                                           │
      ┌───┴───┐                                       │
      │spine1 │  AS 65001                             │
      │       │  Lo0: 192.168.255.1/32                │
      └───┬───┘                                       │
         / \                                          │
        /   \                                         │
    Eth1     Eth2                                     │
      /         \                                     │
  Eth1           Eth1                                 │
┌───┴───┐     ┌───┴───┐                              │
│ leaf1 │     │ leaf2 │                              │
│AS65101│     │AS65102│                              │
│Lo0:.3 │     │Lo0:.4 │                              │
│Lo1:.1 │     │Lo1:.2 │                              │
└───────┘     └───────┘                              │
    .12             .13 ──────────────────────────────┘

Fabric IP Plan:
  Loopback0  (Router ID):  spine1=192.168.255.1  leaf1=192.168.255.3  leaf2=192.168.255.4
  Loopback1  (VTEP):                             leaf1=192.168.254.1  leaf2=192.168.254.2
  P2P Links:               spine1↔leaf1: 192.168.103.0/31
                           spine1↔leaf2: 192.168.103.2/31
  Anycast GW (SVI):        VLAN 10 → 10.10.10.1/24  (same IP on both leafs)
```

The fabric uses **eBGP** as both underlay (IPv4 unicast for loopback reachability) and overlay (EVPN for MAC/IP advertisement across VXLAN).

## Prerequisites

- Completed Labs 1–3 (basic EOS CLI, eAPI, VXLAN concepts)
- Containerlab and the cEOS image installed (same as previous labs)
- Python 3 and pip available

---

## Exercise 1: Install AVD

AVD has two components:
- **`pyavd`** — Python library (the engine that processes the data model)
- **`arista.avd`** — Ansible collection (roles for build, deploy, validate)

Install both from the `avd/` directory:

```bash
cd lab4/avd
pip install -r requirements.txt --break-system-packages
ansible-galaxy collection install -r requirements.yml
```

Ansible refuses to load `ansible.cfg` from a world-writable directory (a security restriction). In Codespaces the workspace is world-writable by default, so fix the permissions once:

```bash
chmod o-w /workspaces/ul-arista-labs-2026/lab4/avd
```

Verify the installation:

```bash
ansible-galaxy collection list | grep arista
python3 -c "import pyavd; print(pyavd.__version__)"
```

> **What is happening?** `pyavd` provides the Python functions that transform your YAML intent into structured data. The `arista.avd` Ansible collection wraps those functions into Ansible roles that you call from playbooks.

---

## Exercise 2: Deploy the Lab Topology

Deploy the containerlab topology from the `lab4/` directory:

```bash
cd ..   # back to lab4/
sudo containerlab deploy -t lab4.clab.yaml
```

Wait ~60 seconds for the cEOS devices to fully boot. cEOS responds to ping quickly, but the management API (nginx) takes an extra 30–40 seconds to start. Hitting the API too early returns an empty response. Then verify all nodes are running:

```bash
sudo containerlab inspect -t lab4.clab.yaml
```

Confirm eAPI is reachable on each device (the bootstrap config uses HTTP on port 80):

```bash
curl -s -u admin:admin http://172.20.20.11/command-api \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"runCmds","params":{"version":1,"cmds":["show version"]},"id":1}' \
  | python3 -m json.tool | grep hostname
```

You should see `"hostname": "spine1"`. Repeat for `.12` (leaf1) and `.13` (leaf2).

> **Troubleshooting:** If the command returns nothing, run it without the pipe first to see the raw response:
> ```bash
> curl -s -u admin:admin http://172.20.20.11/command-api \
>   -H "Content-Type: application/json" \
>   -d '{"jsonrpc":"2.0","method":"runCmds","params":{"version":1,"cmds":["show version"]},"id":1}'
> ```
> If cEOS is still booting you may get a connection refused — wait 15 seconds and retry.

> **Question:** At this point, the devices only have the minimal bootstrap configuration (management IP, eAPI, admin user). Try running `show bgp evpn` on spine1. What do you see, and why?

```bash
ssh admin@172.20.20.11   # password: admin
spine1# show bgp evpn
```

---

## Exercise 3: Explore the AVD Project Structure

Move into the AVD project directory and examine the files:

```bash
cd avd/
ls -la
```

You will find:

```
avd/
├── ansible.cfg            ← Ansible settings (inventory location, connection options)
├── requirements.yml       ← Ansible Galaxy dependencies
├── requirements.txt       ← Python dependencies
├── inventory.yml          ← Ansible inventory (maps hostnames to IPs and groups)
├── build.yml              ← Playbook: generate configs from YAML
├── deploy.yml             ← Playbook: push configs to devices
├── validate.yml           ← Playbook: run automated tests
└── group_vars/            ← The AVD data model (your network intent)
    ├── all.yml            ← Ansible connection variables
    ├── FABRIC.yml         ← Fabric-wide design choices
    ├── SPINES.yml         ← Spine node definitions
    ├── LEAFS.yml          ← Leaf node definitions
    ├── NETWORK_SERVICES.yml    ← Tenant VLANs and VRFs
    └── CONNECTED_ENDPOINTS.yml ← Server/host wiring (empty in this lab)
```

Read through each `group_vars/` file and notice:
- `FABRIC.yml` sets design-wide choices (protocols, MTU, management settings)
- `SPINES.yml` and `LEAFS.yml` define *nodes* — each node needs only an ID, BGP AS, and management IP
- `NETWORK_SERVICES.yml` defines *what services* run on the fabric (VLANs, VRFs, SVIs)

> **Question:** In `LEAFS.yml`, find the `loopback_ipv4_offset` setting. Using the formula `pool_base + offset + id`, calculate what Loopback0 IP AVD will assign to leaf2.

---

## Exercise 4: Build — Generate Configurations

Run the build playbook. This is a **read-only, offline operation** — no devices are contacted:

```bash
ansible-playbook build.yml
```

You will see Ansible working through two roles: `eos_designs` then `eos_cli_config_gen`. When it finishes, examine the generated output:

```bash
ls intended/
ls intended/configs/
ls intended/structured_configs/
ls documentation/
```

Look at the generated EOS configuration for spine1:

```bash
cat intended/configs/spine1.cfg
```

And for leaf1:

```bash
cat intended/configs/leaf1.cfg
```

> **Questions to consider:**
> 1. Identify the BGP configuration section. How many BGP neighbors does spine1 have? What are their ASNs?
> 2. Find the VXLAN interface configuration on leaf1. What is the VTEP source interface and the VNI assigned to VLAN 10?
> 3. How many lines of configuration did AVD generate? Compare this to the ~10-line bootstrap config.

Now look at the structured intermediate format (the step between YAML intent and EOS config):

```bash
cat intended/structured_configs/leaf1.yml | head -80
```

> **Key insight:** AVD has a two-step process. `eos_designs` converts your *intent* (what you want) into a *structured config* (a device-centric YAML). `eos_cli_config_gen` then renders that into EOS CLI syntax. This separation lets you validate the data model before rendering and makes it easy to add new platform support.

---

## Exercise 5: Review the Generated Documentation

AVD automatically generates Markdown documentation describing the entire fabric:

```bash
ls documentation/
ls documentation/fabric/
ls documentation/devices/
```

Open the fabric documentation:

```bash
cat documentation/fabric/FABRIC-documentation.md
```

This document contains:
- A topology diagram (as Markdown)
- BGP peer groups and their configuration
- P2P link IP address assignments
- Loopback IP assignments

Open a device-specific document:

```bash
cat documentation/devices/leaf1.md
```

> **Question:** Find the BGP peer group section in the fabric documentation. Does it correctly list both leaf1 and leaf2 as peers of spine1?

> **Why does this matter?** In production networks, keeping documentation up to date is a constant struggle. With AVD, documentation is generated automatically every time you run `build.yml` — it is *always* in sync with the actual deployed configuration.

---

## Exercise 6: Deploy — Push Configurations to Devices

Now push the generated configurations to the live devices:

```bash
ansible-playbook deploy.yml
```

Watch the output carefully. AVD:
1. Reads the generated config from `intended/configs/`
2. Connects to each device via eAPI
3. Computes the diff (what needs to change)
4. Applies the configuration

When the playbook finishes, verify the configuration on spine1:

```bash
ssh admin@172.20.20.11
spine1# show bgp summary
spine1# show bgp evpn summary
spine1# show ip route
```

On leaf1, verify the VXLAN interface and BGP sessions:

```bash
ssh admin@172.20.20.12
leaf1# show interfaces Vxlan1
leaf1# show bgp evpn
leaf1# show vxlan vtep
```

> **Questions:**
> 1. How many BGP sessions does spine1 have? Are they all Established?
> 2. What EVPN routes does leaf1 have in its BGP table?
> 3. Can leaf1 ping leaf2's VTEP IP? Run `ping 192.168.254.2 source Loopback0` from leaf1.

---

## Exercise 7: Validate — Automated Network Testing

Run the automated validation suite:

```bash
ansible-playbook validate.yml
```

AVD uses **ANTA (Arista Network Test Automation)** to run a comprehensive set of tests derived directly from your data model. The tests are generated automatically — you do not need to write them manually.

Review the test results:

```bash
cat reports/FABRIC-state.md
```

The report shows each test, the device it ran on, and whether it passed or failed. Common tests include:
- `VerifyBGPSpecificPeers` — Are all expected BGP sessions established?
- `VerifyInterfacesStatus` — Are all fabric interfaces up/up?
- `VerifyReachability` — Can all VTEPs reach each other?

> **Questions:**
> 1. How many tests were run in total? How many passed?
> 2. Find a test that verifies the EVPN overlay. What is the test checking?
> 3. Why is automated validation valuable compared to manually running `show` commands?

---

## Exercise 8 (Challenge): Day 2 — Add a New VLAN

A core benefit of AVD is that Day 2 operations follow the exact same workflow as Day 1. You change the YAML, rebuild, and redeploy.

**Task:** Add a new management VLAN (VLAN 20, subnet 10.10.20.0/24) to the fabric.

1. Open `group_vars/NETWORK_SERVICES.yml`
2. Find the commented-out VLAN 20 example at the bottom of the file
3. Uncomment it and add the new SVI entry under the `svis:` list
4. Re-run the full workflow:

```bash
ansible-playbook build.yml
ansible-playbook deploy.yml
ansible-playbook validate.yml
```

After deployment, verify the new VLAN on a leaf switch:

```bash
ssh admin@172.20.20.12
leaf1# show vlan
leaf1# show interfaces Vlan20
leaf1# show bgp evpn route-type imet
```

> **Questions:**
> 1. What changed in `intended/configs/leaf1.cfg` after adding VLAN 20?
> 2. What new BGP EVPN routes appeared after the deployment?
> 3. How many lines of YAML did you write to add the new VLAN? How many lines of EOS config did AVD generate?
> 4. In a production network with 50 leaf switches, what would the traditional (manual) approach require? What does AVD require?

---

## Summary

In this lab you experienced the complete AVD workflow:

| Stage | Tool | What happened |
|-------|------|---------------|
| Design | YAML group_vars | Described network intent in a human-readable data model |
| Build | `eos_designs` + `eos_cli_config_gen` | Generated EOS configs and Markdown documentation automatically |
| Deploy | `eos_config_deploy_eapi` | Pushed configs to live devices via eAPI |
| Validate | ANTA (`eos_validate_state`) | Ran automated tests derived from the data model |

The key insight is that with AVD you define the **intent** of the network once, and the tool handles consistency, documentation, and validation across all devices — whether you have 3 switches or 300.

---

## Cleanup

When you are finished, destroy the lab topology:

```bash
cd ..   # back to lab4/
sudo containerlab destroy -t lab4.clab.yaml --cleanup
```

---

## Further Reading

- [Arista AVD Documentation](https://avd.arista.com)
- [ANTA Documentation](https://anta.arista.com)
- [AVD GitHub Repository](https://github.com/aristanetworks/avd)
- [Arista Validated Designs Getting Started Guide](https://avd.arista.com/stable/docs/getting-started/)
