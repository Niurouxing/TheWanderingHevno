# plugins/core_codex/tests/conftest.py

import pytest

# 告诉 pytest 加载项目根目录下的共享 fixtures。
# 这会使 test_engine_setup, sandbox_factory, client, 和所有数据 fixtures
# (如 linear_collection, codex_basic_data) 对本目录下的所有测试可见。
pytest_plugins = [
    "tests.conftest",
    "tests.conftest_data"
]