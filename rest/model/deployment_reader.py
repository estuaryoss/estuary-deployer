import yaml


class DeploymentReader:

    @classmethod
    def load(cls, data):
        return yaml.safe_load(data)

    @classmethod
    def get_metadata_for_deployment(cls, data):
        try:
            deployment = cls.load(data)
            if not isinstance(deployment, dict):
                return {}
        except:
            return {}

        return deployment.get("x-metadata") if deployment.get("x-metadata") is not None else {}
