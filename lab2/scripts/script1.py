import pyeapi
import json
from pprint import pprint

# 1. Define connection details
# Replace with your lab credentials and IP/Hostname
connection = pyeapi.client.connect(
    transport="https",
    host="clab-lab2-ceos1",
    username="admin",
    password="pass",
    port=443,
    verify=False  # Skip SSL certificate check for lab use
)

# 2. Create a node object to interact with the switch
node = pyeapi.client.Node(connection)

try:
    # 3. Execute 'show version' and capture the JSON response
    response = node.enable("show version")
    
    # The response is a list containing a dictionary for each command run
    # Since we ran one command, we look at index [0]
    version_data = response[0]['result']

    # 4. "Do something" with the data: extract specific fields
    model = version_data.get('modelName')
    version = version_data.get('version')
    mac = version_data.get('systemMacAddress')
    uptime = version_data.get('uptime')

    # 5. Show it in a "pretty" way
    print("-" * 30)
    print(f"Device: {model}")
    print(f"Software: {version}")
    print(f"MAC Address: {mac}")
    print(f"Uptime: {uptime} seconds")
    print("-" * 30)

except Exception as e:
    print(f"An error occurred: {e}")