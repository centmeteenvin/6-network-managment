from command import BlockingCommand, BackgroundCommand, OVSAddPortCommand
from template import replaceInTemplateFile
from logged import ch
import yaml
import logging
class DockerContainer:
    def __init__(self, name) -> None:
        self.name = name
        self.ovsPort : str | None = None
        self._DGW : str = "" 
        self.VLAN : int = 0
        self._ipWithSN : str = ""
        
    def exec(self, command: str, blocking = True, tty = False) -> None:
        """Execute the given command inside this docker container, if blocking is False the command will run in the background"""
        execCommand = f"sudo docker exec -i{'t' if tty else ''} {self.name} {command}"
        if blocking:
            BlockingCommand(execCommand)
        else:
            BackgroundCommand(execCommand)
            
    @property
    def DGW(self) -> str:
        return self._DGW
    
    @DGW.setter
    def DGW(self, ip: str) -> None:
        self.exec("ip route del default")
        self.exec(f"ip route add default via {ip}")
        self._DGW = ip
        
    @property
    def ip(self) -> str:
        """Returns the ip with SNM of the ovsPort"""
        return self._ipWithSN

    @ip.setter
    def ip(self, ipWithSN: str) -> None:
        """Set the ip address on the containers ovsPort"""
        self.exec(f"ip address add {ipWithSN} dev {self.ovsPort}")
        self._ipWithSN = ipWithSN
        
    def dhclient(self) -> None:
        """Run the dhclient command on the container for the ovs-port, will run even if the command is not available"""
        self.exec(f"dhclient {self.ovsPort}") # Execute the command twice because the first time it will fail.
        self.exec(f"dhclient {self.ovsPort}")
        
    def __repre__(self) -> str:
        return f"""
    {10*'='} Docker Container {10*'='}
    name: {self.name}
    ovsPort: {self.name}
    VLAN: {self.VLAN}
    DGW: {self.DGW}
    
    """
            
class DockerCompose:
    def __init__(self, replaceDict: dict = {}) -> None:
        self.containers : dict = {}
        self.replaceDict = replaceDict
        
    def up(self, args: str) -> dict:
        """
        Parses the docker compose template file, then  brings the composition up.
        Returns a dictionary where the keys are the names of the containers and the values are containers
        Preregisters undo command.
        """
        dockerComposeFile = replaceInTemplateFile('./docker-compose.yaml.template', self.replaceDict)
        upCommand = f"docker compose up {args}" 
        downCommand = f"docker compose down"
        BlockingCommand(upCommand, [downCommand])
        yamlDict = None
        with open(dockerComposeFile, 'r') as file:
            yamlDict = yaml.safe_load(file)
            
        for serviceDefinition in yamlDict['services'].values():
            name = serviceDefinition['container_name']
            self.containers[name] = DockerContainer(name)
        return self.containers
    
class OVSBridge():
    def __init__(self, name) -> None:
        """
        Creates an ovs bridge instance and creates it on the host system.
        The undo commands are scheduled by default
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel('DEBUG')
        self.name = name
        self._ip = ""
        self.portMapping = {}
        BlockingCommand(f"sudo ovs-vsctl add-br {name}", undoCommands=[f"sudo ovs-vsctl del-br {name}"])
        
    @property
    def ip(self) -> str:
        return self._ip
    
    @ip.setter
    def ip(self, ipAddressWithSN: str) -> None:
        self._ip =ipAddressWithSN
        BlockingCommand(f"sudo ip a a {self._ip} dev {self.name}")
        BlockingCommand(f"sudo ip l s {self.name} up")
        
    def addContainer(self, container: DockerContainer, port: str, staticIpWithSN: str | None = None, gateway: str | None = None) -> None:
        """
        Adds the container to the given port, if staticIp and gateway are given the container will receive these values.
        It will also set the container ovsPort value and add the container with the port to self.portMapping.
        """
        container.ovsPort = port
        self.portMapping[container.name] = container
        OVSAddPortCommand(
            bridge=self.name,
            port=port,
            container=container.name,
            staticIp=staticIpWithSN,
            gateway=gateway
        )
        
    def setVLAN(self, container: DockerContainer, tag: int) -> None:
        BlockingCommand(f"sudo ovs-docker set-vlan {self.name} {container.ovsPort} {container.name} {tag}")
        container.VLAN = tag
    
