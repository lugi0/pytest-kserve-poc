from kubernetes.dynamic.client import DynamicClient
from ocp_resources.resource import Resource, NamespacedResource
from ocp_resources.pod import Pod
from ocp_resources.namespace import Namespace
from ocp_resources.inference_service import InferenceService
from utils import get_flan_pod, curl_from_pod
import logging
import subprocess

LOGGER = logging.getLogger(__name__)

class TestKserveInternalEndpoint:

    def test_new_ns(self, create_namespace: Resource):
        ns = create_namespace(name="test-namespace")
        assert ns.name == "test-namespace"

    def test_deploy_model(self, client: DynamicClient, create_namespace: Resource, test_s3_secret: Resource, test_storage_config: Resource, test_sr: Resource, test_is: Resource):
        ns = create_namespace("test-namespace")
        predictor_pod = get_flan_pod(client, ns.name, test_is.name)
        predictor_pod.wait_for_status("Running")
        predictor_pod.wait_for_condition("Ready", "True")
        assert test_is.instance.status.modelStatus.states.activeModelState == "Loaded"
        assert test_is.instance.status.address.url == f"http://{test_is.name}.{ns.name}.svc.cluster.local"

    def test_curl_with_istio(self, test_is: InferenceService, create_namespace: Namespace, pod_with_istio_sidecar: Pod, test_smm: NamespacedResource):
        LOGGER.info("Testing curl from the same namespace with a pod part of the service mesh")
        ns = create_namespace("test-namespace")
        pod = pod_with_istio_sidecar(ns)
        pod.wait_for_status("Running")
        pod.wait_for_condition("Ready", "True")
        curl_stdout = curl_from_pod(ns, test_is, pod, "health", "http")
        assert curl_stdout == "OK"

        LOGGER.info("Testing curl from a different namespace with a pod part of the service mesh")
        ns = create_namespace("diff-namespace")
        pod = pod_with_istio_sidecar(ns)
        pod.wait_for_status("Running")
        pod.wait_for_condition("Ready", "True")
        curl_stdout = curl_from_pod(ns, test_is, pod, "health", "http")
        assert curl_stdout == "OK"

    def test_curl_outside_istio(self, test_is: InferenceService, create_namespace: Namespace, pod_without_istio_sidecar: Pod):
        LOGGER.info("Testing curl from the same namespace with a pod not part of the service mesh")
        ns = create_namespace("test-namespace")
        pod = pod_without_istio_sidecar(ns)
        pod.wait_for_status("Running")
        pod.wait_for_condition("Ready", "True")
        curl_stdout = curl_from_pod(ns, test_is, pod, "health", "https")
        assert curl_stdout == "OK"

        LOGGER.info("Testing curl from a different namespace with a pod not part of the service mesh")
        ns = create_namespace("diff-namespace")
        pod = pod_without_istio_sidecar(ns)
        pod.wait_for_status("Running")
        pod.wait_for_condition("Ready", "True")
        curl_stdout = curl_from_pod(ns, test_is, pod, "health", "https")
        assert curl_stdout == "OK"
