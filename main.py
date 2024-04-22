import argparse
import os
import subprocess
import logging
import threading
import shlex

from .logging import logger

def log_subprocess_output(pipe):
    for line in iter(pipe.readline, b''):
        # Log each line from the subprocess
        logger.debug('Subprocess output: %r', line.decode().strip())


def executeBash(command_line, block: bool = True):
    command_line_args = shlex.split(command_line)
    logger.info('Running subprocess: %s', command_line)

    try:
        process = subprocess.Popen(command_line_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        thread = threading.Thread(target=log_subprocess_output, args=(process.stdout,))
        thread.start()
        if block:
            process.wait()

    except Exception as e:
        logger.error('Exception occurred: %s', str(e))
        return False

    return True


logger.info("Setting up wireless")

argParser = argparse.ArgumentParser()
argParser.add_argument("--ap", action="store_true", help="If node should act like an acces point")
argParser.add_argument("-n", type=int, help="Give number of node", required=True)
argParser.add_argument("--level", help="Set logging level", default="INFO")
args = argParser.parse_args()

isAP = args.ap
nodeNr = args.n
logger.setLevel(args.level)

ip = "192.168.1." + str(nodeNr)

if isAP:
    executeBash("hostapd ./hostapd.conf", block=False)
else:
    executeBash("sudo wpa_passphrase demoNN passwordNN > ./wpa_supplicant.conf")
    executeBash("sudo iwconfig wlp1s0 mode managed")
    executeBash("sudo wpa_supplicant -i wlp1s0 -c ./wpa_supplicant.conf", block=False)
executeBash(f"sudo ifconfig wlp1s0 {ip}/24")

logger.info("Finished setting up wireless")

logger.info("Installing packages")
executeBash("sudo apt update")
executeBash("sudo apt install -y docker.io")
executeBash("sudo apt install -y openvswitch-switch apparmor")
executeBash("sudo curl https://raw.githubusercontent.com/openvswitch/ovs/master/utilities/ovs-docker -o /usr/bin/ovs-docker")
executeBash("sudo chmod +x /usr/bin/ovs-docker")
logger.info("Finished installing packages")

ip = f"192.168.{nodeNr}.1"

logger.info("Setting up OpenVSwitch")
executeBash("sudo ovs-vsctl add-br ovs-br0")
executeBash(f"sudo ip a a {ip}/24 dev ovs-br0")
executeBash("sudo ip l s ovs-br0 up")
executeBash("sudo sysctl -w net.ipv4.ip_forward=1")
logger.info("Finished setting up OpenVSwitch")

logger.info("Creating dhcp container")
os.chdir("./DockerAP")

with open("./dnsmasq.conf.template", "r") as f:
    content = f.read()
    content = content.replace("$", str(nodeNr))

with open("./dnsmasq.conf", "w") as f:
    f.write(content)

executeBash("sudo docker build –t dhcpimage .")
executeBash("sudo docker run –itd -v ./dnsmasq.conf:/etc/dnsmasq.d/dnsmasq.conf --privileged --name dhcp_container dhcpimage")
os.chdir("../")
logger.info("Finished creating dhcp container")

logger.info("Creating client containers")
os.chdir("./DockerClient")
for i in range(2):
    executeBash("sudo docker build –t clientimage .")
    executeBash(f"sudo docker run –itd --privileged --name client_container{i} clientimage")
logger.info("Finished creating client containers")

logger.info("Connecting containers to bridge")
executeBash(f"sudo /usr/bin/ovs-docker add-port ovs-br0 eth0 dhcp_container --ipaddress=192.168.{nodeNr}.2/24 --gateway=192.168.{nodeNr}.1")

for i in range(2):
    executeBash(f"sudo /usr/bin/ovs-docker add-port ovs-br0 eth{i + 1} client_container{i}")
logger.info("Finished connecting containers to bridge")

while (True):
   pass