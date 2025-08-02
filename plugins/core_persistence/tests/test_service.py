# plugins/core_persistence/tests/test_service.py
import pytest
from plugins.core_persistence.service import PersistenceService

# 使用 pytest.mark.asyncio 来标记异步测试函数
@pytest.mark.asyncio
async def test_persistence_service_initialization(tmp_path):
    """
    测试 PersistenceService 能否在临时目录中正确初始化。
    `tmp_path` 是 pytest 内置的一个 fixture，提供一个临时的目录路径。
    """
    assets_dir = tmp_path / "assets"
    service = PersistenceService(assets_base_dir=str(assets_dir))
    
    assert assets_dir.exists()
    assert service.assets_base_dir == assets_dir

# 可以在这里添加更多关于 save_asset, load_asset, import/export 的单元测试