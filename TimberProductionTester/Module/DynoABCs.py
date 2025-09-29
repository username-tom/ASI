from abc import ABC, abstractmethod

class DynoBrake(ABC):

    @abstractmethod
    def set_torque(self, target: float = 0.0):
        ...

    @abstractmethod
    def start(self):
        ...

    @abstractmethod
    def stop(self):
        ...


class DynoPoller(ABC):

    @property
    def log_params(self):
        ...

    @log_params.setter
    @abstractmethod
    def log_params(self, logParams):
        ...

    @property
    def poll_interval(self):
        ...

    @poll_interval.setter
    @abstractmethod
    def poll_interval(self, val):
        ...

    @property
    def poll_enabled(self):
        ...

    @poll_enabled.setter
    @abstractmethod
    def poll_enabled(self, val):
        ...

    @abstractmethod
    def start_polling(self, pollInterval):
        ...

    @abstractmethod
    def stop_polling(self):
        ...
