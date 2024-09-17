from ocp_resources.resource import NamespacedResource
from ocp_resources.pod import Pod
from ocp_resources.namespace import Namespace
from ocp_resources.inference_service import InferenceService
from simple_logger.logger import get_logger
from utils import get_flan_pod, curl_from_pod


LOGGER = get_logger(__name__)


class TestKserveInternalEndpoint:
    def test_deploy_model(self, admin_client, endpoint_namespace, endpoint_isvc):
        assert (
            endpoint_isvc.instance.status.modelStatus.states.activeModelState
            == "Loaded"
        )
        assert (
            endpoint_isvc.instance.status.address.url
            == f"http://{endpoint_isvc.name}.{endpoint_namespace.name}.svc.cluster.local"
        )

        #  should be in fixture - test setup
        predictor_pod = get_flan_pod(
            namespace=endpoint_namespace, client=endpoint_namespace.name, name=endpoint_isvc.name
        )
        predictor_pod.wait_for_status("Running")
        predictor_pod.wait_for_condition("Ready", "True")

    def test_curl_with_istio(
        self,
        endpoint_isvc: InferenceService,
        endpoint_namespace,
        diff_namespace,
        endpoint_pod_with_istio_sidecar: Pod,
        diff_pod_with_istio_sidecar,
        test_smm: NamespacedResource,
    ):
        LOGGER.info(
            "Testing curl from the same namespace with a pod part of the service mesh"
        )

        curl_stdout = curl_from_pod(
            isvc=endpoint_isvc,
            pod=endpoint_pod_with_istio_sidecar,
            endpoint="health",
        )
        assert curl_stdout == "OK"

        LOGGER.info(
            "Testing curl from a different namespace with a pod part of the service mesh"
        )

        curl_stdout = curl_from_pod(
            isvc=endpoint_isvc, pod=diff_pod_with_istio_sidecar, endpoint="health"
        )
        assert curl_stdout == "OK"

    def test_curl_outside_istio(
        self,
        endpoint_isvc: InferenceService,
        endpoint_namespace: Namespace,
        diff_namespace,
        endpoint_pod_without_istio_sidecar: Pod,
        diff_pod_without_istio_sidecar,
    ):
        LOGGER.info(
            "Testing curl from the same namespace with a pod not part of the service mesh"
        )

        curl_stdout = curl_from_pod(
            isvc=endpoint_isvc,
            pod=endpoint_pod_without_istio_sidecar,
            endpoint="health",
            protocol="https",
        )
        assert curl_stdout == "OK"

        LOGGER.info(
            "Testing curl from a different namespace with a pod not part of the service mesh"
        )

        curl_stdout = curl_from_pod(
            isvc=endpoint_isvc, pod=diff_pod_without_istio_sidecar, endpoint="health", protocol="https"
        )
        assert curl_stdout == "OK"
