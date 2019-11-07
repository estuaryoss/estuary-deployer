from abc import abstractmethod, ABC


class Routes(ABC):

    @abstractmethod
    def index(self):
        raise NotImplementedError("You must implement this method")

    @abstractmethod
    def ping(self):
        raise NotImplementedError("You must implement this method")

    @abstractmethod
    def about(self):
        raise NotImplementedError("You must implement this method")

    @abstractmethod
    def get_env_vars(self):
        raise NotImplementedError("You must implement this method")

    @abstractmethod
    def get_env_var(self):
        raise NotImplementedError("You must implement this method")

    @abstractmethod
    def deploy_start(self):
        raise NotImplementedError("You must implement this method")

    @abstractmethod
    def deploy_start_env(self):
        raise NotImplementedError("You must implement this method")

    @abstractmethod
    def deploy_start_from_server(self):
        raise NotImplementedError("You must implement this method")

    @abstractmethod
    def deploy_stop(self):
        raise NotImplementedError("You must implement this method")

    @abstractmethod
    def execute_command(self):
        raise NotImplementedError("You must implement this method")
