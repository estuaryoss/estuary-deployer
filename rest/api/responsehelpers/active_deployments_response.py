class ActiveDeployment:

    # docker
    @staticmethod
    def docker_deployment(id, containers):
        return {
            "id": id,
            "containers": containers,
        }

    # k8s pod
    @staticmethod
    def k8s_pod(namespace, name, pod):
        return {
            "namespace": namespace,
            "name": name,
            "pod": pod,
        }

    # k8s deployment
    @staticmethod
    def k8s_deployment(namespace, name, pod):
        return {
            "namespace": namespace,
            "name": name,
            "deployment": pod,
        }
