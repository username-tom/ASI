from abc import ABC, abstractmethod


class ComABC(ABC):

    @abstractmethod
    def read(self, name):
        ...

    @abstractmethod
    def write(self, name, value):
        ...

    @abstractmethod
    def controller_parameter(self, params):
        ...
