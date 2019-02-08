from abc import ABC, abstractmethod


class TVRemoteController(ABC):

    def __init__(self, value):
        self.value = value
        super().__init__()

    @abstractmethod
    def install_channel(self):
        pass

    @abstractmethod
    def uninstall_channel(self):
        pass

    @abstractmethod
    def get_active_channel(self):
        pass

    @abstractmethod
    def get_channel_list(self):
        pass