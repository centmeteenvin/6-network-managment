import argparse
from logged import logger
from object import DockerContainer, DockerCompose, OVSBridge
import subprocess
import traceback

from command import *

logger.info("Setting up wireless")

argParser = argparse.ArgumentParser()
argParser.add_argument("--ap", action="store_true",
                       help="If node should act like an acces point")
argParser.add_argument(
    "-n", type=int, help="Give number of node", required=True)
argParser.add_argument("--level", help="Set logging level", default="INFO")
argParser.add_argument("--others", type=str, help="The other nodes numbers in the network", default="21,23,24,28")
args = argParser.parse_args()

isAP = args.ap
nodeNr = args.n
level = args.level
logger.setLevel(level)
others : list[int] = [int(nr) for nr in args.others.split(',')]
try:
    others.remove(nodeNr) # ensure our node number is not present
except:
    pass

ip = "192.168.1." + str(nodeNr)
try:
    if isAP:
        BackgroundCommand("sudo hostapd ./hostapd.conf", loggingLevel='DEBUG')
    else:
        BlockingCommand(
            "sudo wpa_passphrase demoNN passwordNN > ./wpa_supplicant.conf", shell=True, split=False)
        BlockingCommand("sudo iwconfig wlp1s0 mode managed")
        BackgroundCommand(
            "sudo wpa_supplicant -i wlp1s0 -c wpa_supplicant.conf", loggingLevel='DEBUG')
    BlockingCommand(f"sudo ifconfig wlp1s0 {ip}/24")

    logger.info("Finished setting up wireless")

    logger.info("Installing packages")
    BlockingCommand("sudo apt update")
# Add Docker's official GPG key:
    BlockingCommand("sudo apt-get -y install ca-certificates curl")
    BlockingCommand("sudo install -m 0755 -d /etc/apt/keyrings")
    BlockingCommand("sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc")
    BlockingCommand("sudo chmod a+r /etc/apt/keyrings/docker.asc")

# Add the repository to Apt sources:
    subprocess.run('echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null', shell=True)
    BlockingCommand("sudo apt-get update")

    BlockingCommand(" sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin")
    BlockingCommand("sudo apt install -y openvswitch-switch apparmor")
    BlockingCommand(
        "sudo curl https://raw.githubusercontent.com/openvswitch/ovs/master/utilities/ovs-docker -o /usr/bin/ovs-docker")
    BlockingCommand("sudo chmod +x /usr/bin/ovs-docker")
    
    logger.info("Finished installing packages")

    ip = f"192.168.{nodeNr}.1"
    bridge = 'ovs-br0'
    logger.info("Setting up OpenVSwitch")
    bridge = OVSBridge('ovs-br0')
    bridge.ip = f"192.168.{nodeNr}.1/24"

    BlockingCommand("sudo sysctl -w net.ipv4.ip_forward=1")
    logger.info("Finished setting up OpenVSwitch")

    logger.info("Creating dhcp container")
    dockerComposition = DockerCompose()
    containers = dockerComposition.up("--build --detach")
    dhcpContainer : DockerContainer = containers['dhcp_container']
    client1 : DockerContainer = containers['client_container1']
    client2 : DockerContainer = containers['client_container2']
    client3 : DockerContainer = containers['client_container3']
    clients : tuple[DockerContainer]= (client1, client2, client3)
    logger.info("Connecting containers to bridge")
    bridge.addContainer(dhcpContainer, 'eth1', staticIpWithSN=f'192.168.{nodeNr}.2/24', gateway=f'192.168.{nodeNr}.1')
    
    for i, client in enumerate(clients):
        bridge.addContainer(client, f'eth1')

    logger.info("Finished connecting containers to bridge")

    logger.info("Starting dhcp server")
    dhcpContainer.exec("dnsmasq -d -C /etc/dnsmasq.d/dnsmasq.conf")

    logger.info("Fetching ip addresses for clients")
    # for client in clients:
    #     client.exec("")
    logger.info("Adding static routes")
    for otherNode in others:
        # For each node access the 192.168.nodenr.0/24 network through the 192.168.1.nodenr gateway
        gatewayIp = f"192.168.1.{otherNode}"
        StaticRouteCommand(f"192.168.{otherNode}.0/24", gatewayIp)

    shouldQuit = input("Type [exit] to exit: ") == "exit"
    while not shouldQuit:
        shouldQuit = input("Type [exit] to exit: ") == "exit"
        if shouldQuit:
            break
except Exception as e:
    traceback.print_exc()
    logger.fatal(f"Got exception {e}")
logger.info(f"Shutting down, reverting all commands")
Command.revert()