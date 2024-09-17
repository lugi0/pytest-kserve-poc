from ocp_resources.pod import Pod
from kubernetes.dynamic.client import DynamicClient
from ocp_resources.inference_service import InferenceService
from ocp_resources.namespace import Namespace
from simple_logger.logger import get_logger

from conftest import client
import subprocess

LOGGER = get_logger(__name__)


class FlanPodNotFoundError(Exception):
    pass


class CurlFailedInPod(Exception):

    def __init__(self, result: subprocess.CompletedProcess):
        self.result= result
        self.message = f'curl failed with RC {result.returncode} - stderr: {result.stderr}'
        super().__init__(self.message)


class ProtocolNotSupported(Exception):
    
    def __init__(self, protocol: str):
        self.protocol = protocol
        self.message = f'Protocol {protocol} is not supported'
        super().__init__(self.message)


def get_flan_pod(client: DynamicClient, namespace: str, is_name: str) -> Pod:
    for pod in Pod.get(dyn_client=client, namespace=namespace):
        if is_name+"-predictor" in pod.name:
            return pod

    raise FlanPodNotFoundError(f"No flan predictor pod found in namespace {namespace}")


def curl_from_pod(namespace: Namespace, isvc: InferenceService, pod: Pod, endpoint: str, protocol: str = "http") -> str:
    if protocol == "http":
        host = isvc.instance.status.address.url
    elif protocol== "https":
        tmp = isvc.instance.status.address.url
        host = "https://"+tmp.split("://")[1]
    else:
        raise ProtocolNotSupported(protocol)
    # Fails here but works when running manually in the cluster
    # curl_result = pod.execute(
    #    command=f"curl {host}/{endpoint}"
    # )
    run_command = f'oc exec {pod.name} -n {namespace.name} -- curl -k {host}/{endpoint}'
    curl_result = subprocess.run(run_command, shell=True, capture_output=True, text=True)
    LOGGER.info(curl_result)
    if curl_result.returncode == 0:
        return curl_result.stdout
    else:
        raise CurlFailedInPod(curl_result)
