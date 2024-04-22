import argparse
import os
import subprocess
import logging
import threading
import shlex

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
logger.setLevel(args.level)
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
    BlockingCommand("sudo apt install -y docker.io")
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
    os.chdir("./DockerAP")

    with open("./dnsmasq.conf.template", "r") as f:
        content = f.read()
        content = content.replace("$", str(nodeNr))

    with open("./dnsmasq.conf", "w") as f:
        f.write(content)

    BlockingCommand("sudo docker build –t dhcpimage .")
    BlockingCommand(
        "sudo docker run –itd -v ./dnsmasq.conf:/etc/dnsmasq.d/dnsmasq.conf --privileged --name dhcp_container dhcpimage",
        undoCommands=["sudo docker stop dhcp_container", "sudo docker container rm dhcp_container"]
        )
    os.chdir("../")
    logger.info("Finished creating dhcp container")

    logger.info("Creating client containers")
    os.chdir("./DockerClient")
    for i in range(2):
        BlockingCommand("sudo docker build –t clientimage .")
        BlockingCommand(
            f"sudo docker run –itd --privileged --name client_container{i} clientimage",
            undoCommands=[f"sudo docker stop client_container{i}", f"sudo docker container rm client_container{i}"]
            )
    logger.info("Finished creating client containers")

    logger.info("Connecting containers to bridge")
    BlockingCommand(
        f"sudo /usr/bin/ovs-docker add-port ovs-br0 eth0 dhcp_container --ipaddress=192.168.{nodeNr}.2/24 --gateway=192.168.{nodeNr}.1")

    for i in range(2):
        BlockingCommand(
            f"sudo /usr/bin/ovs-docker add-port ovs-br0 eth{i + 1} client_container{i}")
    logger.info("Finished connecting containers to bridge")

    logger.info("Adding static routes")
    for otherNode in others:
        # For each node access the 192.168.nodenr.0/24 network through the 192.168.1.nodenr gateway
        gatewayIp = f"192.168.1.{otherNode}"
        StaticRouteCommand(f"192.168.{otherNode}.0/24", gatewayIp)

    shouldQuit = input("Type [exit] to exit: ") == "exit"
    while not shouldQuit:
        shouldQuit = input("Type [exit] to exit: ") == "exit"

except Exception as e:
    logger.fatal(f"Got exception {e}, reverting all commands, {e.with_traceback()}")
    Command.revert()