import pytest
from ocp_resources.resource import get_client


@pytest.fixture(scope="session")
def admin_client():
    """
    Get DynamicClient
    """
    return get_client()
