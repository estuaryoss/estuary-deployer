from rest.environment.deployment_metadata import DeploymentMetadataSingleton


class ActiveDeployment:

    # docker
    @staticmethod
    def docker_deployment(id, containers):
        return {
            "id": id,
            "metadata": DeploymentMetadataSingleton.get_instance().get_metadata_for_deployment(id),
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
