import pytest
import subprocess
from kubernetes.dynamic.client import DynamicClient
from ocp_resources.namespace import Namespace
from ocp_resources.resource import get_client, NamespacedResource, Resource
from ocp_resources.serving_runtime import ServingRuntime
from ocp_resources.inference_service import InferenceService
from ocp_resources.secret import Secret
from ocp_resources.pod import Pod
import logging

LOGGER = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def client():
    yield get_client(config_file="Files/kubeconfig")

@pytest.fixture(scope="class")
def create_namespace(client: DynamicClient):
    """
    Factory to create and delete Namespaces needed in a test class
    """

    created_namespaces = {}

    def _create_namespace(name):
        if name in created_namespaces.keys():
            return created_namespaces[name]
        LOGGER.info("CREATING NEW NAMESPACE")
        ns = Namespace(client=client, name=name, delete_timeout=600)
        ns.create()
        LOGGER.info("WAITING FOR NS STATUS TO BECOME ACTIVE")
        ns.wait_for_status(status=Namespace.Status.ACTIVE, timeout=120)
        created_namespaces[name]=ns
        LOGGER.info(f"NS {name} IS ACTIVE, RETURNING")
        return ns
    
    yield _create_namespace

    for ns in created_namespaces.values():
        ns.delete()

@pytest.fixture(scope="class")
def test_sr(client, create_namespace):
    ns = create_namespace("test-namespace")
    with ServingRuntime(
        client=client,
        namespace=ns.name,
        yaml_file="Files/caikit_tgis_servingruntime.yaml"
    ) as sr:
        sr.wait()
        yield sr

@pytest.fixture(scope="class")
def test_is(client, create_namespace):
    ns = create_namespace("test-namespace")
    with InferenceService(
        client=client,
        namespace=ns.name,
        yaml_file="Files/caikit_tgis_inferenceservice.yaml"
    ) as isvc:
        isvc.wait_for_condition("Ready", "True")
        yield isvc

@pytest.fixture(scope="class")
def test_s3_secret(client, create_namespace):
    ns = create_namespace("test-namespace")
    with Secret(
        client=client,
        namespace=ns.name,
        yaml_file="Files/s3-secret.yaml"
    ) as s3:
        s3.wait()
        yield s3

@pytest.fixture(scope="class")
def test_storage_config(client, create_namespace):
    ns = create_namespace("test-namespace")
    with Secret(
        client=client,
        namespace=ns.name,
        yaml_file="Files/storage-config.yaml"
    ) as storage_config:
        storage_config.wait()
        yield storage_config

@pytest.fixture(scope="class")
def test_smm(client, create_namespace):
    ns = create_namespace("diff-namespace")
    # ugly hack, smm resource is not part of the library yet
    run_command = f'oc apply -n {ns.name} -f Files/service_mesh_member.yaml'
    out = subprocess.run(run_command, shell=True)
    yield out
    run_command = f'oc delete ServiceMeshMember default -n {ns.name}'
    subprocess.run(run_command, shell=True)

@pytest.fixture(scope="class")
def pod_with_istio_sidecar(client: DynamicClient):

    created_pods = []

    def _create_pod(namespace: Namespace):
        LOGGER.info(f"CREATING POD TEST-WITH-ISTIO IN NS {namespace.name}")
        run_command = f'oc run test-with-istio -n {namespace.name} --image=registry.access.redhat.com/rhel7/rhel-tools --annotations=sidecar.istio.io/inject="true" -- sleep infinity'
        subprocess.run(run_command, shell=True)
        for pod in Pod.get(dyn_client=client, namespace=namespace.name):
            if pod.name == "test-with-istio":
                my_pod=pod
        created_pods.append(pod)
        LOGGER.info(f"POD HAS BEEN CREATED IN {namespace.name}")
        return my_pod
    
    yield _create_pod

    for pod in created_pods:
        pod.delete()

@pytest.fixture(scope="class")
def pod_without_istio_sidecar(client: DynamicClient):

    created_pods = []

    def _create_pod(namespace: Namespace):
        LOGGER.info(f"CREATING POD TEST IN NS {namespace.name}")
        run_command = f'oc run test -n {namespace.name} --image=registry.access.redhat.com/rhel7/rhel-tools -- sleep infinity'
        subprocess.run(run_command, shell=True)
        for pod in Pod.get(dyn_client=client, namespace=namespace.name):
            if pod.name == "test":
                my_pod=pod
        created_pods.append(pod)
        LOGGER.info(f"POD HAS BEEN CREATED IN {namespace.name}")
        return my_pod
    
    yield _create_pod

    for pod in created_pods:
        pod.delete()
