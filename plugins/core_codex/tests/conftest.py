# plugins/core_codex/tests/conftest.py

import pytest

# 加载项目根的共享 fixtures 和 core_engine 的共享 fixtures
# 这将使 client, sandbox_factory, mutate_resource_api, query_resource_api 等全部可用
pytest_plugins = [
    "tests.conftest",
    "tests.conftest_data",
    "plugins.core_engine.tests.conftest"
]
