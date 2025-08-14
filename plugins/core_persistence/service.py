# plugins/core_persistence/service.py

import os
import io
import json
import logging
import shutil
import asyncio
import base64
import zipfile
from pathlib import Path
from typing import Type, TypeVar, Tuple, Dict, Any, List, Optional
from uuid import UUID

import aiofiles
from pydantic import BaseModel, ValidationError
from PIL import Image, PngImagePlugin

# 导入位于后端内核的自定义序列化工具
from backend.core.serialization import custom_json_decoder_object_hook

from .contracts import PersistenceServiceInterface, PackageManifest
from plugins.core_engine.contracts import Sandbox, StateSnapshot # 仍然需要它们来做类型检查和序列化
from .models import AssetType, FILE_EXTENSIONS

T = TypeVar('T', bound=BaseModel)
logger = logging.getLogger(__name__)

class PersistenceService(PersistenceServiceInterface):
    def __init__(self, assets_base_dir: str):
        self.assets_base_dir = Path(assets_base_dir)
        self._sandboxes_root_dir = self.assets_base_dir / "sandboxes"
        self._sandboxes_root_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"PersistenceService initialized. Sandboxes directory: {self._sandboxes_root_dir.resolve()}")

    @property
    def sandboxes_root_dir(self) -> Path:
        return self._sandboxes_root_dir

    def _get_sandbox_dir(self, sandbox_id: UUID) -> Path:
        return self._sandboxes_root_dir / str(sandbox_id)

    async def save_sandbox(self, sandbox_id: UUID, data: Dict[str, Any]) -> None:
        sandbox_dir = self._get_sandbox_dir(sandbox_id)
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        file_path = sandbox_dir / "sandbox.json"
        
        # 不再需要 `default` 参数，因为传入的 `data` 已经是完全 JSON 兼容的了
        json_string = json.dumps(data, indent=2)

        async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
            await f.write(json_string)
        logger.debug(f"Persisted sandbox '{sandbox_id}' to {file_path}")

    async def load_sandbox(self, sandbox_id: UUID) -> Optional[Dict[str, Any]]:
        file_path = self._get_sandbox_dir(sandbox_id) / "sandbox.json"
        if not file_path.is_file(): return None
        async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
            content = await f.read()
        return json.loads(content, object_hook=custom_json_decoder_object_hook)

    async def delete_sandbox(self, sandbox_id: UUID) -> None:
        sandbox_dir = self._get_sandbox_dir(sandbox_id)
        if sandbox_dir.exists():
            await asyncio.to_thread(shutil.rmtree, sandbox_dir)
            logger.info(f"Deleted sandbox directory: {sandbox_dir}")

    async def list_sandbox_ids(self) -> List[str]:
        if not self._sandboxes_root_dir.is_dir():
            return []
        def _sync_list_dirs():
            return [p.name for p in self._sandboxes_root_dir.iterdir() if p.is_dir()]
        return await asyncio.to_thread(_sync_list_dirs)

    async def save_snapshot(self, sandbox_id: UUID, snapshot_id: UUID, data: Dict[str, Any]) -> None:
        snapshot_dir = self._get_sandbox_dir(sandbox_id) / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        file_path = snapshot_dir / f"{snapshot_id}.json"
        
        json_string = json.dumps(data, indent=2)
        
        async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
            await f.write(json_string)
        logger.debug(f"Persisted snapshot '{snapshot_id}' for sandbox '{sandbox_id}'")

    async def load_snapshot(self, sandbox_id: UUID, snapshot_id: UUID) -> Optional[Dict[str, Any]]:
        file_path = self._get_sandbox_dir(sandbox_id) / "snapshots" / f"{snapshot_id}.json"
        if not file_path.is_file(): return None
        async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f: content = await f.read()
        return json.loads(content, object_hook=custom_json_decoder_object_hook)

    async def load_all_snapshots_for_sandbox(self, sandbox_id: UUID) -> List[Dict[str, Any]]:
        snapshot_dir = self._get_sandbox_dir(sandbox_id) / "snapshots"
        if not snapshot_dir.is_dir():
            return []

        def _sync_read_files() -> List[Dict[str, Any]]:
            snapshots_data = []
            for file_path in snapshot_dir.glob("*.json"):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    snapshots_data.append(json.loads(content, object_hook=custom_json_decoder_object_hook))
                except (json.JSONDecodeError) as e:
                    logger.error(f"Skipping corrupt snapshot file {file_path}: {e}")
            return snapshots_data
            
        return await asyncio.to_thread(_sync_read_files)
        
    async def delete_all_for_sandbox(self, sandbox_id: UUID) -> None:
        """异步删除属于特定沙盒的所有快照文件。"""
        snapshot_dir = self._get_sandbox_dir(sandbox_id) / "snapshots"
        if snapshot_dir.is_dir():
            await asyncio.to_thread(shutil.rmtree, snapshot_dir)
            logger.debug(f"Deleted snapshot directory: {snapshot_dir}")

    async def delete_snapshot(self, sandbox_id: UUID, snapshot_id: UUID) -> None:
        """异步删除一个指定的快照文件。"""
        file_path = self._get_sandbox_dir(sandbox_id) / "snapshots" / f"{snapshot_id}.json"
        if file_path.is_file():
            try:
                # 使用 os.remove 比 shutil.rmtree 更适合删除文件
                await asyncio.to_thread(os.remove, file_path)
                logger.debug(f"Deleted snapshot file: {file_path}")
            except FileNotFoundError:
                # 如果在检查和删除之间文件消失了，这不是一个错误
                pass
            except Exception as e:
                logger.error(f"Error deleting snapshot file {file_path}: {e}")
                # 重新抛出，让上层知道操作失败
                raise
        
    async def list_assets(self, asset_type: AssetType) -> List[str]:
        """Lists all assets of a given type by scanning the assets directory."""
        if asset_type == AssetType.SANDBOX:
             # Sandboxes are directories, not files with extensions
            return await self.list_sandbox_ids()

        ext = FILE_EXTENSIONS.get(asset_type)
        if not ext:
            raise ValueError(f"Unknown asset type '{asset_type}' with no defined file extension.")

        # For other asset types, we'd define their storage location.
        # As of now, only sandboxes are fully implemented, so we return empty for others.
        # For example: search_dir = self.assets_base_dir / asset_type.value
        # This implementation assumes other assets aren't stored yet.
        return []

    async def _embed_zip_in_png(self, zip_bytes: bytes, base_image_bytes: Optional[bytes] = None) -> bytes:
        def _sync_embed():
            encoded_data = base64.b64encode(zip_bytes).decode('ascii')
            if base_image_bytes: image = Image.open(io.BytesIO(base_image_bytes))
            else: image = Image.new('RGBA', (1, 1), (0, 0, 0, 255))
            png_info_obj = PngImagePlugin.PngInfo()
            png_info_obj.add_text("hevno:data", encoded_data, zip=True)
            buffer = io.BytesIO()
            image.save(buffer, "PNG", pnginfo=png_info_obj)
            return buffer.getvalue()
        return await asyncio.to_thread(_sync_embed)

    async def _extract_zip_from_png(self, png_bytes: bytes) -> Tuple[bytes, bytes]:
        def _sync_extract():
            try:
                image = Image.open(io.BytesIO(png_bytes))
                image.load()
                encoded_data = image.text.get("hevno:data")
                if encoded_data is None: raise ValueError("Invalid Hevno package: 'hevno:data' chunk not found.")
                zip_data = base64.b64decode(encoded_data)
                return zip_data, png_bytes
            except Exception as e:
                logger.error(f"[EXTRACT] Exception while processing PNG: {e}", exc_info=True)
                raise ValueError(f"Failed to process PNG file: {e}") from e
        return await asyncio.to_thread(_sync_extract)

    async def save_sandbox_icon(self, sandbox_id: str, icon_bytes: bytes) -> Path:
        icon_path = self.assets_base_dir / "sandbox_icons" / f"{sandbox_id}.png"
        icon_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(icon_path, 'wb') as f:
            await f.write(icon_bytes)
        logger.info(f"Saved icon for sandbox {sandbox_id} to {icon_path}")
        return icon_path

    async def export_package(self, manifest: PackageManifest, data_files: Dict[str, Any], base_image_bytes: Optional[bytes] = None) -> bytes:
        def _sync_zip():
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('manifest.json', manifest.model_dump_json(indent=2))
                for filename, model_instance in data_files.items():
                    if isinstance(model_instance, BaseModel): file_content = model_instance.model_dump_json(indent=2)
                    else: file_content = json.dumps(model_instance, indent=2)
                    zf.writestr(f'data/{filename}', file_content)
            return zip_buffer.getvalue()
        zip_bytes = await asyncio.to_thread(_sync_zip)
        return await self._embed_zip_in_png(zip_bytes, base_image_bytes)

    async def import_package(self, package_bytes: bytes) -> Tuple[PackageManifest, Dict[str, str], bytes]:
        zip_bytes, png_bytes = await self._extract_zip_from_png(package_bytes)
        def _sync_unzip():
            data_files: Dict[str, str] = {}
            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
                try:
                    manifest_content = zf.read('manifest.json').decode('utf-8')
                    manifest = PackageManifest.model_validate_json(manifest_content)
                except KeyError: raise ValueError("Package is missing 'manifest.json'.")
                except (ValidationError, json.JSONDecodeError) as e: raise ValueError(f"Invalid 'manifest.json': {e}") from e
                for item in zf.infolist():
                    if item.filename.startswith('data/') and not item.is_dir():
                        relative_path = item.filename.split('data/', 1)[1]
                        data_files[relative_path] = zf.read(item).decode('utf-8')
            return manifest, data_files
        manifest, data_files = await asyncio.to_thread(_sync_unzip)
        return manifest, data_files, png_bytes
        
    def get_sandbox_icon_path(self, sandbox_id: str) -> Optional[Path]:
        icon_path = self.assets_base_dir / "sandbox_icons" / f"{sandbox_id}.png"
        return icon_path if icon_path.is_file() else None

    def get_default_icon_path(self) -> Path:
        return self.assets_base_dir / "default_sandbox_icon.png"