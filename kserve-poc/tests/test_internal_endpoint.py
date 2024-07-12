from kubernetes.dynamic.client import DynamicClient
from kubernetes.dynamic.resource import ResourceInstance
from ocp_resources.resource import NamespacedResource, Resource
from ocp_resources.pod import Pod
from utils import get_flan_pod
import logging
import time
import pytest
import requests
import ocp_resources

LOGGER = logging.getLogger(__name__)

class TestKserveInternalEndpoint:

    def test_internal_endpoint_present(self, test_namespace: Resource):
        assert 1

    def test_creating_new_namespace(self, client: DynamicClient, test_namespace: Resource, test_s3_secret: Resource, test_storage_config: Resource, test_sr: Resource, test_is: Resource):
        # LOGGER.info(test_namespace.Status.READY)
        # LOGGER.info(test_namespace.name)
        # LOGGER.info(test_s3_secret.Condition.AVAILABLE)
        # LOGGER.info(test_storage_config.Condition.AVAILABLE)
        # LOGGER.info(test_sr.name)
        # LOGGER.info(test_sr.namespace)
        # LOGGER.info(test_sr.Condition.AVAILABLE)
        # LOGGER.info(test_is.name)
        # LOGGER.info(test_is.namespace)
        # LOGGER.info(test_is.Condition.AVAILABLE)
        predictor_pod = get_flan_pod(client, test_namespace.name, test_is.name)
        predictor_pod.wait_for_status("Running")
        predictor_pod.wait_for_condition("Ready", "True")
        assert test_is.instance.status.modelStatus.states.activeModelState == "Loaded"
        assert test_is.instance.status.address.url == f"http://{test_is.name}.{test_namespace.name}.svc.cluster.local"

    def test_curl_in_istio(self, test_is: Resource, test_with_istio_pod: Pod):
        test_with_istio_pod.wait_for_status("Running")
        test_with_istio_pod.wait_for_condition("Ready", "True")
        # Fails here but works when running manually in the cluster
        curl_result = test_with_istio_pod.execute(
            command=f"curl {test_is.instance.status.address.url}/health"
        )
        assert curl_result == "OK"