from abc import abstractmethod, ABC


class Routes(ABC):

    @abstractmethod
    def index(self):
        raise NotImplementedError("You must implement this method")

    @abstractmethod
    def ping(self):
        raise NotImplementedError("You must implement this method")

    @abstractmethod
    def deploystart(self):
        raise NotImplementedError("You must implement this method")

    @abstractmethod
    def deploystartenv(self):
        raise NotImplementedError("You must implement this method")

    @abstractmethod
    def deploystart_from_server(self):
        raise NotImplementedError("You must implement this method")
