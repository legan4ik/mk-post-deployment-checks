import pytest
import cvp_checks.utils as utils


@pytest.fixture
def local_salt_client():
    return utils.init_salt_client()
