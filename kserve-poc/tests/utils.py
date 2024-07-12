from ocp_resources.pod import Pod
from conftest import client

class FlanPodNotFoundError(Exception):
    pass

def get_flan_pod(client, namespace, is_name):
    for pod in Pod.get(dyn_client=client, namespace=namespace):
        if is_name+"-predictor" in pod.name:
            return pod

    raise FlanPodNotFoundError(f"No flan predictor pod found in namespace {namespace.name}")
