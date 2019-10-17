from abc import abstractmethod, ABC


class EnvCreation(ABC):

    @abstractmethod
    def up(self):
        raise NotImplementedError("You must implement this method")
