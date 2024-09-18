import shlex

import pytest
from ocp_resources.pod import Pod
from kubernetes.dynamic.client import DynamicClient
from ocp_resources.inference_service import InferenceService
from pyhelper_utils.shell import run_command
from simple_logger.logger import get_logger


LOGGER = get_logger(name=__name__)


class FlanPodNotFoundError(Exception):
    pass


class ProtocolNotSupported(Exception):
    def __init__(self, protocol: str):
        self.protocol = protocol
        self.message = f"Protocol {protocol} is not supported"
        super().__init__(self.message)


def get_flan_pod(client: DynamicClient, namespace: str, name_prefix: str) -> Pod:
    for pod in Pod.get(dyn_client=client, namespace=namespace):
        if name_prefix + "-predictor" in pod.name:
            return pod

    raise FlanPodNotFoundError(f"No flan predictor pod found in namespace {namespace}")


def curl_from_pod(
    isvc: InferenceService,
    pod: Pod,
    endpoint: str,
    protocol: str = "http",
) -> str:
    if protocol == "http":
        host = isvc.instance.status.address.url

    elif protocol == "https":
        tmp = isvc.instance.status.address.url
        host = "https://" + tmp.split("://")[1]

    else:
        raise ProtocolNotSupported(protocol)

    return pod.execute(command=shlex.split(f"curl -k {host}/{endpoint}"))


def create_sidecar_pod(admin_client, namespace, istio, pod_name):
    cmd = f"oc run test-with-istio -n {namespace.name} --image=registry.access.redhat.com/rhel7/rhel-tools"
    if istio:
        cmd = f'{cmd} --annotations=sidecar.istio.io/inject="true"'

    cmd += " -- sleep infinity"

    _, _, err = run_command(command=shlex.split(cmd), check=False)
    if err:
        pytest.fail(f"Failed on {err}")

    pod = Pod(name=pod_name, Namespace=namespace.name, client=admin_client)
    pod.wait_for_status(status="Running")
    pod.wait_for_condition(condition="Ready", status="True")
    return pod
