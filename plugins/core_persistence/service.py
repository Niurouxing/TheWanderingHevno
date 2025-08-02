# plugins/core_persistence/service.py

import io
import json
import zipfile
import logging
from pathlib import Path
from typing import Type, TypeVar, Tuple, Dict, Any, List
from pydantic import BaseModel, ValidationError

from .models import PackageManifest, AssetType, FILE_EXTENSIONS

T = TypeVar('T', bound=BaseModel)
logger = logging.getLogger(__name__)

class PersistenceService:
    """
    处理所有文件系统和包导入/导出操作的核心服务。
    """
    def __init__(self, assets_base_dir: str):
        self.assets_base_dir = Path(assets_base_dir)
        self.assets_base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"PersistenceService initialized. Assets directory: {self.assets_base_dir.resolve()}")

    def _get_asset_path(self, asset_type: AssetType, asset_name: str) -> Path:
        """根据资产类型和名称构造标准化的文件路径。"""
        extension = FILE_EXTENSIONS[asset_type]
        # 简单的安全措施，防止路径遍历
        safe_name = Path(asset_name).name 
        return self.assets_base_dir / asset_type.value / f"{safe_name}{extension}"

    def save_asset(self, asset_model: T, asset_type: AssetType, asset_name: str) -> Path:
        """将 Pydantic 模型保存为格式化的 JSON 文件。"""
        file_path = self._get_asset_path(asset_type, asset_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        json_content = asset_model.model_dump_json(indent=2)
        file_path.write_text(json_content, encoding='utf-8')
        return file_path

    def load_asset(self, asset_type: AssetType, asset_name: str, model_class: Type[T]) -> T:
        """从文件加载并验证 Pydantic 模型。"""
        file_path = self._get_asset_path(asset_type, asset_name)
        if not file_path.exists():
            raise FileNotFoundError(f"Asset '{asset_name}' of type '{asset_type.value}' not found.")
        
        json_content = file_path.read_text(encoding='utf-8')
        try:
            return model_class.model_validate_json(json_content)
        except ValidationError as e:
            raise ValueError(f"Failed to validate asset '{asset_name}': {e}") from e

    def list_assets(self, asset_type: AssetType) -> List[str]:
        """列出指定类型的所有资产名称。"""
        asset_dir = self.assets_base_dir / asset_type.value
        if not asset_dir.exists():
            return []
        
        extension = FILE_EXTENSIONS[asset_type]
        
        asset_names = [
            p.name.removesuffix(extension) 
            for p in asset_dir.glob(f"*{extension}")
        ]
        return sorted(asset_names)

    def export_package(self, manifest: PackageManifest, data_files: Dict[str, BaseModel]) -> bytes:
        """在内存中创建一个 .hevno.zip 包并返回其字节流。"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('manifest.json', manifest.model_dump_json(indent=2))
            for filename, model_instance in data_files.items():
                file_content = model_instance.model_dump_json(indent=2)
                zf.writestr(f'data/{filename}', file_content)
        
        return zip_buffer.getvalue()

    def import_package(self, zip_bytes: bytes) -> Tuple[PackageManifest, Dict[str, str]]:
        """解压包，读取清单和所有数据文件（作为原始字符串）。"""
        zip_buffer = io.BytesIO(zip_bytes)
        data_files: Dict[str, str] = {}
        
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            try:
                manifest_content = zf.read('manifest.json').decode('utf-8')
                manifest = PackageManifest.model_validate_json(manifest_content)
            except KeyError:
                raise ValueError("Package is missing 'manifest.json'.")
            except (ValidationError, json.JSONDecodeError) as e:
                raise ValueError(f"Invalid 'manifest.json': {e}") from e

            for item in zf.infolist():
                if item.filename.startswith('data/') and not item.is_dir():
                    relative_path = item.filename.split('data/', 1)[1]
                    data_files[relative_path] = zf.read(item).decode('utf-8')
        
        return manifest, data_files