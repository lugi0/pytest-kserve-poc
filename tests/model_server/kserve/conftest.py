import os

import pytest
from ocp_resources.inference_service import InferenceService
from ocp_resources.secret import Secret
from ocp_resources.serving_runtime import ServingRuntime
from ocp_utilities.infra import dict_base64_encode
from simple_logger.logger import get_logger

from tests.model_server.kserve.utils import create_sidecar_pod
from utilities.infra import create_ns


LOGGER = get_logger(__name__)


@pytest.fixture(scope="module")
def endpoint_namespace(admin_client):
    yield from create_ns(admin_client=admin_client, name="endpoint-namespace")


@pytest.fixture(scope="module")
def diff_namespace(admin_client):
    yield from create_ns(admin_client=admin_client, name="diff-namespace")


@pytest.fixture(scope="class")
def endpoint_sr(admin_client, endpoint_namespace):
    with ServingRuntime(
        client=admin_client,
        namespace=endpoint_namespace.name,
        yaml_file="../manifests/caikit_tgis_servingruntime.yaml",
        wait=True,
    ) as sr:
        yield sr


@pytest.fixture(scope="class")
def endpoint_s3_secret(admin_client, endpoint_namespace):
    data = {
        "AWS_ACCESS_KEY_ID": os.environ["AWS_ACCESS_KEY_ID"],
        "AWS_DEFAULT_REGION": os.environ["AWS_DEFAULT_REGION"],
        "AWS_S3_BUCKET": os.environ["AWS_S3_BUCKET"],
        "AWS_S3_ENDPOINT": os.environ["AWS_S3_ENDPOINT"],
        "AWS_SECRET_ACCESS_KEY": os.environ["AWS_SECRET_ACCESS_KEY"],
    }
    with Secret(
        client=admin_client,
        namespace=endpoint_namespace.name,
        name="endpoint-s3-secret",
        data_dict=dict_base64_encode(_dict=data),
        wait=True,
    ) as secret:
        yield secret


@pytest.fixture(scope="class")
def endpoint_isvc(admin_client, endpoint_sr, endpoint_s3_secret):
    predictor = {
        "maxReplicas": 1,
        "minReplicas": 1,
        "model": {
            "modelFormat": "caikit",
            "name": "test-model",
            "resources": {
                "limits": {"cpu": "2", "memory": "8Gi"},
                "requests": {"cpu": "1", "memory": "4Gi"},
            },
            "runtime": endpoint_sr.name,
            "storage": {
                "key": endpoint_s3_secret.instance.data.key,
                "path": endpoint_s3_secret.instance.data.path,
            },
        },
    }

    with InferenceService(
        client=admin_client, namespace=endpoint_sr.name, **predictor
    ) as isvc:
        isvc.wait_for_condition(condition="Ready", status="True")
        yield isvc


@pytest.fixture(scope="class")
def storage_config_secret(admin_client, endpoint_s3_secret):
    with Secret(
        client=admin_client,
        namespace=endpoint_s3_secret.name,
        data_dict={endpoint_s3_secret.name: endpoint_s3_secret.instance.data},
        wait=True,
    ) as storage_config:
        yield storage_config


@pytest.fixture(scope="class")
def service_mesh_member(admin_client, endpoint_namespace):
    with ServiceMeshMember(
        client=admin_client,
        namespace=endpoint_namespace.name,
        control_plane_ref={"name": "default", "namespace": "istio-system"},
        wait=True,
    ) as smm:
        yield smm


@pytest.fixture(scope="class")
def endpoint_pod_with_istio_sidecar(admin_client, endpoint_namespace):
    pod = create_sidecar_pod(
        admin_client=admin_client,
        namespace=endpoint_namespace,
        istio=True,
        pod_name="test-with-istio",
    )
    yield pod
    pod.clean_up()


@pytest.fixture(scope="class")
def endpoint_pod_without_istio_sidecar(admin_client, endpoint_namespace):
    pod = create_sidecar_pod(
        admin_client=admin_client,
        namespace=endpoint_namespace,
        istio=True,
        pod_name="test",
    )
    yield pod
    pod.clean_up()


@pytest.fixture(scope="class")
def diff_pod_with_istio_sidecar(admin_client, diff_namespace):
    pod = create_sidecar_pod(
        admin_client=admin_client,
        namespace=diff_namespace,
        istio=True,
        pod_name="test-with-istio",
    )
    yield pod
    pod.clean_up()


@pytest.fixture(scope="class")
def diff_pod_without_istio_sidecar(admin_client, diff_namespace):
    pod = create_sidecar_pod(
        admin_client=admin_client,
        namespace=diff_namespace,
        istio=True,
        pod_name="test",
    )
    yield pod
    pod.clean_up()
