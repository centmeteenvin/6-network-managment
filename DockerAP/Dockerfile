# Select ubuntu as the base image
FROM ubuntu:20.04

# Download all necessary packages and afterwards delete all temporary files to reduce
# image size
RUN apt update && apt install dnsmasq iproute2 nano dnsutils tcpdump iputils-ping -y && \apt clean && apt autoclean && rm -rf /var/lib/apt/lists/*

# Create 2 directories, -p indicates parent directories are created if necessary
RUN mkdir -p /var/lib/dnsmasq /etc/dnsmasq.d

# Copy the config file from the host into the image
# /etc/dnsmasq.d/dnsmasq.conf

# CMD indicates the command that is executed at the start of the container, when this
# command finished the container will exit, We start the container using dnsmasq command
# in debug mode
CMD ["/bin/bash"]
