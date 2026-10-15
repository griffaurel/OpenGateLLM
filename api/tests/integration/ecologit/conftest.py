import pytest


@pytest.fixture(scope="session")
def test_redis_pool():
    yield


@pytest.fixture(scope="function", autouse=True)
def _reset_redis_between_tests():
    yield
