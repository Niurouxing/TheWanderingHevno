# plugins/core_persistence/tests/test_service.py
import pytest
import zipfile
import io
import json
from pydantic import BaseModel

from plugins.core_persistence.service import PersistenceService
from plugins.core_persistence.models import AssetType, PackageManifest, PackageType

# 一个简单的 Pydantic 模型用于测试 save/load
class MockAsset(BaseModel):
    name: str
    value: int

@pytest.fixture
def persistence_service(tmp_path) -> PersistenceService:
    """提供一个使用临时目录的 PersistenceService 实例。"""
    assets_dir = tmp_path / "assets"
    return PersistenceService(assets_base_dir=str(assets_dir))

# 保持你原有的初始化测试
def test_persistence_service_initialization(persistence_service: PersistenceService, tmp_path):
    assets_dir = tmp_path / "assets"
    assert assets_dir.exists()
    assert persistence_service.assets_base_dir == assets_dir

# --- 新增的单元测试 ---

def test_save_and_load_asset(persistence_service: PersistenceService):
    """测试资产的保存和加载往返流程。"""
    asset = MockAsset(name="test_asset", value=123)
    asset_type = AssetType.GRAPH # 使用任意一种类型来测试
    asset_name = "my_first_asset"

    # 保存
    path = persistence_service.save_asset(asset, asset_type, asset_name)
    assert path.exists()
    
    # 加载
    loaded_asset = persistence_service.load_asset(asset_type, asset_name, MockAsset)
    
    assert isinstance(loaded_asset, MockAsset)
    assert loaded_asset.name == "test_asset"
    assert loaded_asset.value == 123

def test_list_assets(persistence_service: PersistenceService):
    """测试列出指定类型的所有资产。"""
    # 初始应为空
    assert persistence_service.list_assets(AssetType.GRAPH) == []

    # 创建一些资产
    persistence_service.save_asset(MockAsset(name="a", value=1), AssetType.GRAPH, "graph_a")
    persistence_service.save_asset(MockAsset(name="b", value=2), AssetType.GRAPH, "graph_b")
    persistence_service.save_asset(MockAsset(name="c", value=3), AssetType.CODEX, "codex_c")

    # 验证列表
    graph_assets = persistence_service.list_assets(AssetType.GRAPH)
    assert sorted(graph_assets) == ["graph_a", "graph_b"]
    
    codex_assets = persistence_service.list_assets(AssetType.CODEX)
    assert codex_assets == ["codex_c"]

def test_export_package(persistence_service: PersistenceService):
    """测试包导出功能。"""
    manifest = PackageManifest(
        package_type=PackageType.GRAPH_COLLECTION,
        entry_point="data/main.graph.hevno.json"
    )
    data_files = {
        "main.graph.hevno.json": MockAsset(name="main_graph", value=1)
    }

    zip_bytes = persistence_service.export_package(manifest, data_files)
    
    # 验证 zip 内容
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
        assert "manifest.json" in zf.namelist()
        assert "data/main.graph.hevno.json" in zf.namelist()
        
        manifest_data = json.loads(zf.read("manifest.json"))
        assert manifest_data["package_type"] == "graph_collection"

def test_import_package(persistence_service: PersistenceService):
    """测试包导入功能。"""
    # 先创建一个 zip 包
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        zf.writestr("manifest.json", '{"package_type": "sandbox_archive", "entry_point": "sb.json"}')
        zf.writestr("data/sb.json", '{"name": "test"}')
        zf.writestr("data/snapshots/snap1.json", '{"id": "uuid"}')

    manifest, data_files = persistence_service.import_package(zip_buffer.getvalue())

    assert manifest.package_type == PackageType.SANDBOX_ARCHIVE
    assert "sb.json" in data_files
    assert "snapshots/snap1.json" in data_files
    assert data_files["sb.json"] == '{"name": "test"}'