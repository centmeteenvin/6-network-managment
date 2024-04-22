from __future__ import annotations
from abc import ABC, abstractmethod
from logged import logger
import shlex
import subprocess
import threading
import logging


class Command(ABC, threading.Thread):
    """
    To execute a command, create a Command object and it will run from creation.
    A Thread object will be associated with the process.
    It will log to DEBUG by default.
    The output is accessible from output property.
    This class holds a list of all commands that were executed, using the revert static method we can undo all changes.
    """
    executedCommands: list[Command] = []
 
 
    def __init__(self, command: str, undoCommands : list[str] = None) -> None:
        ABC.__init__(self)
        threading.Thread.__init__(self)
        args = shlex.split(command)
        logger.info(f'Executing {args}')
        self.process = subprocess.Popen(
            args, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.output = []
        self.undoCommands = undoCommands
        self._loggingLevel = 'INFO'
        Command.executedCommands.append(self)
        self.start()
        self._post_init()

    def readOutput(self) -> None:
        for line in self.process.stdout.readlines():
            processedLine = line.decode().strip()
            logger.debug(processedLine)
            self.output.append(processedLine)
    
    @abstractmethod
    def _post_init(self) -> None:
        """Code to execute after the process has starter in the main thread"""
        pass
    
    @abstractmethod
    def _run(self) -> None:
        """Overwrite to execute additional behavior every loop"""
        pass
    
    def run(self) -> None:
        while True:
            self.readOutput()
            
            if self.process.poll() is not None:
                return # The process has finished so should this thread.
    
    def undo(self) -> None:
        """This command is run when the script needs to undo all of it's work."""
        if self.process.poll() is not None:
            self.process.kill() # Ensure the process itself is terminated
        for command in self.undoCommands:
            UndoCommand(command)
            
    @staticmethod
    def revert() -> None:
        while len(Command.executedCommands) > 0:
            command = Command.executedCommands[-1] # fetch last executed command
            if not isinstance(command, UndoCommand):
                command.undo()
            Command.executedCommands.pop()
                              
            
class BlockingCommand(Command):
    """By its very nature all commands should be blocking, consider using this only for processes where the session can't be closed"""
    def _post_init(self) -> None:
        print("Blocking")
        self.process.wait()
    
    def _run(self) -> None:
        pass

class UndoCommand(BlockingCommand):
    """These commands are the undo's of other commands and cannot be undone themselves"""
    def undo(self) -> None:
        #Does nothing and should not be called.
        pass
    
class BackgroundCommand(Command):
    def __init__(self, command: str, undoCommands: list[str] = None, loggingLevel = 'DEBUG') -> None:
        super().__init__(command, undoCommands)
        self._loggingLevel = loggingLevel
    
    def _post_init(self) -> None:
        pass
    
    def _run(self) -> None:
        pass
    
class StaticRouteCommand(BlockingCommand):
    def __init__(self, destinationIp: str, gatewayIp: str) -> None:
        command = f"sudo ip route add {destinationIp}/24 via {gatewayIp}"
        undoCommand = f"sudo ip route del {destinationIp}/24"
        super().__init__(command, [undoCommand])