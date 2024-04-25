import argparse
from logged import logger
from template import replaceInTemplateFile
import os
import shlex
import subprocess
import threading
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
        BackgroundCommand("hostapd ./hostapd.conf", loggingLevel='INFO')
    else:
        BlockingCommand(
            "sudo wpa_passphrase demoNN passwordNN > ./wpa_supplicant.conf")
        BlockingCommand("sudo iwconfig wlp1s0 mode managed")
        BackgroundCommand(
            "sudo wpa_supplicant -i wlp1s0 -c ./wpa_supplicant.conf", loggingLevel='INFO')
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

    logger.info("Setting up OpenVSwitch")
    BlockingCommand("sudo ovs-vsctl add-br ovs-br0",
                    undoCommands=["sudo ovs-vsctl del-br ovs-br0"])
    BlockingCommand(f"sudo ip a a {ip}/24 dev ovs-br0")
    BlockingCommand("sudo ip l s ovs-br0 up")
    BlockingCommand("sudo sysctl -w net.ipv4.ip_forward=1")
    logger.info("Finished setting up OpenVSwitch")

    logger.info("Creating dhcp container")
    replaceInTemplateFile("./DockerAP/dnsmasq.conf.template", {"$": str(nodeNr)})
    replaceInTemplateFile("./docker-compose.yaml.template", {"$": str(nodeNr)})
    BlockingCommand("sudo docker compose up --build --detach", ["sudo docker compose down -v"])
    logger.info("Connecting containers to bridge")
    BlockingCommand(
        f"sudo /usr/bin/ovs-docker add-port ovs-br0 eth0 dhcp_container --ipaddress=192.168.{nodeNr}.2/24 --gateway=192.168.{nodeNr}.1")

    for i in range(2):
        BlockingCommand(
            f"sudo /usr/bin/ovs-docker add-port ovs-br0 eth{i + 1} client_container{i + 1}")
    logger.info("Finished connecting containers to bridge")

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