import pytest
import subprocess
from ocp_resources.configmap import ConfigMap
from ocp_resources.namespace import Namespace
from ocp_resources.resource import get_client
from ocp_resources.serving_runtime import ServingRuntime
from ocp_resources.inference_service import InferenceService
from ocp_resources.secret import Secret
from ocp_resources.pod import Pod

@pytest.fixture(scope="session")
def client():
    yield get_client(config_file="Files/kubeconfig")

@pytest.fixture(scope="class")
def test_namespace(client):
    with Namespace(
        client=client,
        name="test-namespace",
        delete_timeout=600,
    ) as ns:
        ns.wait_for_status(status=Namespace.Status.ACTIVE, timeout=120)
        yield ns

@pytest.fixture(scope="class")
def test_sr(client, test_namespace):
    with ServingRuntime(
        client=client,
        namespace=test_namespace.name,
        yaml_file="Files/caikit_tgis_servingruntime.yaml"
    ) as sr:
        sr.wait()
        yield sr

@pytest.fixture(scope="class")
def test_is(client, test_namespace):
    with InferenceService(
        client=client,
        namespace=test_namespace.name,
        yaml_file="Files/caikit_tgis_inferenceservice.yaml"
    ) as isvc:
        isvc.wait_for_condition("Ready", "True")
        yield isvc

@pytest.fixture(scope="class")
def test_s3_secret(client, test_namespace):
    with Secret(
        client=client,
        namespace=test_namespace.name,
        yaml_file="Files/s3-secret.yaml"
    ) as s3:
        s3.wait()
        yield s3

@pytest.fixture(scope="class")
def test_storage_config(client, test_namespace):
    with Secret(
        client=client,
        namespace=test_namespace.name,
        yaml_file="Files/storage-config.yaml"
    ) as storage_config:
        storage_config.wait()
        yield storage_config

@pytest.fixture(scope="class")
def test_with_istio_pod(client, test_namespace):
    run_command = f'oc run test-with-istio -n {test_namespace.name} --image=registry.access.redhat.com/rhel7/rhel-tools --annotations=sidecar.istio.io/inject="true" -- sleep infinity'
    subprocess.run(run_command, shell=True)
    for pod in Pod.get(dyn_client=client, namespace=test_namespace.name):
        if pod.name == "test-with-istio":
            my_pod=pod
    yield my_pod
    my_pod.delete()