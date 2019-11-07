class ActiveDeployments:

    # docker
    @staticmethod
    def docker_deployment(id, containers):
        return {
            "id": id,
            "containers": containers,
        }

    # k8s
    @staticmethod
    def k8s_deployment(namespace, name, deployment):
        return {
            "namespace": namespace,
            "name": name,
            "deployment": deployment,
        }
