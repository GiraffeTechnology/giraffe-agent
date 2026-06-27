"""Shared test fixtures.

Routes all GLTG HTTP calls to an in-memory fake so unit tests exercise the real
HTTP client + mapping code without a live GLTG server. Disabled when
RUN_GLTG_INTEGRATION_TESTS=1 so the live integration test hits a real server.
"""

import os

import pytest

from src.integrations import gltg_client as _gltg_client
from tests.gltg_fake import mock_transport as _gltg_mock_transport


@pytest.fixture(autouse=True)
def _gltg_api_mock():
    if os.environ.get("RUN_GLTG_INTEGRATION_TESTS") == "1":
        yield
        return
    _gltg_client.set_default_transport(_gltg_mock_transport())
    try:
        yield
    finally:
        _gltg_client.set_default_transport(None)
