# Select ubuntu as the base image
FROM ubuntu:20.04

# Download all necessary packages and afterwards delete all temporary files to reduce
# image size
RUN apt update && apt install iptables openssh-server openssh-client iperf3 tcpdump isc-dhcp-client dhcpcd5 iproute2 nano dnsutils iputils-ping -y && \apt clean && apt autoclean && rm -rf /var/lib/apt/lists/*

# CMD indicates the command that is executed at the start of the container, when this 
# command finished the container will exit, this i why we use the bash command because it 
# will keep running
CMD ["/bin/bash"]
