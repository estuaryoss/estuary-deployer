import json

import yaml


class DeploymentReader:

    @classmethod
    def load(cls, data):
        return yaml.safe_load(data)

    @classmethod
    def get_metadata_for_deployment(cls, data):
        metadata = cls.load(data).get("x-metadata")
        if metadata is not None:
            return metadata
        return {}
