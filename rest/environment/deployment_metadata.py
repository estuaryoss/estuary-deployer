class DeploymentMetadataSingleton:
    __instance = None
    METADATA_SPACE_MAX_SIZE = 100
    metadata = {}

    @staticmethod
    def get_instance():
        if DeploymentMetadataSingleton.__instance is None:
            DeploymentMetadataSingleton()
        return DeploymentMetadataSingleton.__instance

    def __init__(self):
        """
        The constructor. This class keeps system env vars plus the virtual env vars set by the user.
        These env vars are then passed to the subprocess call.
        """

        if DeploymentMetadataSingleton.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            DeploymentMetadataSingleton.__instance = self

    def set_metadata_for_deployment(self, deployment, metadata):
        """labels is dict"""
        if not isinstance(metadata, dict):
            return False
        if len(self.metadata) < self.METADATA_SPACE_MAX_SIZE and deployment != "":
            self.metadata[deployment] = metadata
            return True

        return False

    def get_metadata_for_deployments(self):
        return self.metadata

    def delete_metadata_for_deployment(self, deployment_id):
        """ {deployment_id: metadata_dict} """
        if self.metadata.get(deployment_id) is not None:
            self.metadata.pop(deployment_id)

    def get_metadata_for_deployment(self, deployment):
        if self.metadata.get(deployment) is not None:
            return self.metadata.get(deployment)
        return {}

    def delete_metadata_for_inactive_deployments(self, active_deployments):
        deployments_metadata = list(self.metadata.keys())
        for depl_id_metadata in deployments_metadata:
            found = False
            for deployment in active_deployments:
                depl_id = deployment.get('id')
                if depl_id_metadata == depl_id:
                    found = True
            if not found:
                self.delete_metadata_for_deployment(deployment_id=depl_id_metadata)
