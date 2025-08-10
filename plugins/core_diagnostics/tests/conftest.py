# plugins/core_api/tests/conftest.py

import pytest

# Make project-level fixtures available to tests in this directory.
# This imports test_engine_setup, sandbox_factory, client, and all data fixtures.
pytest_plugins = [
    "tests.conftest",
    "tests.conftest_data"
]