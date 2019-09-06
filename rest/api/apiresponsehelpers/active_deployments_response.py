class ActiveDeployments:

    @staticmethod
    def active_deployment(id, containers):
        return {
            "id": id,
            "containers": containers,
        }
