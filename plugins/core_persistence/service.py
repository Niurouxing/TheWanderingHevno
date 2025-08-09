# plugins/core_persistence/service.py

import io
import json
import zipfile
import logging
import shutil
import asyncio
import base64
from pathlib import Path
from typing import Type, TypeVar, Tuple, Dict, Any, List, Optional
from uuid import UUID

import aiofiles
from pydantic import BaseModel, ValidationError
from PIL import Image, PngImagePlugin

from .contracts import PersistenceServiceInterface, PackageManifest
from plugins.core_engine.contracts import Sandbox, StateSnapshot
from .models import AssetType, FILE_EXTENSIONS

T = TypeVar('T', bound=BaseModel)
logger = logging.getLogger(__name__)

class PersistenceService(PersistenceServiceInterface):
    """
    【已重构为异步】
    处理所有文件系统和包导入/导出操作的核心服务。
    所有耗时的I/O操作现在都是非阻塞的。
    """
    def __init__(self, assets_base_dir: str):
        self.assets_base_dir = Path(assets_base_dir)
        self.sandboxes_root_dir = self.assets_base_dir / "sandboxes"
        self.sandboxes_root_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"PersistenceService initialized. Sandboxes directory: {self.sandboxes_root_dir.resolve()}")

    # --- 辅助方法 (同步，因为只处理路径) ---
    def _get_sandbox_dir(self, sandbox_id: UUID) -> Path:
        return self.sandboxes_root_dir / str(sandbox_id)

    # --- 沙盒持久化方法 (异步) ---
    async def save_sandbox(self, sandbox: Sandbox) -> None:
        sandbox_dir = self._get_sandbox_dir(sandbox.id)
        # mkdir is fast and can remain synchronous
        sandbox_dir.mkdir(exist_ok=True)
        file_path = sandbox_dir / "sandbox.json"
        async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
            await f.write(sandbox.model_dump_json(indent=2))
        logger.debug(f"Persisted sandbox '{sandbox.id}' to {file_path}")

    async def load_sandbox(self, sandbox_id: UUID) -> Optional[Sandbox]:
        file_path = self._get_sandbox_dir(sandbox_id) / "sandbox.json"
        if not file_path.is_file():
            return None
        async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
            content = await f.read()
        return Sandbox.model_validate_json(content)

    async def delete_sandbox(self, sandbox_id: UUID) -> None:
        sandbox_dir = self._get_sandbox_dir(sandbox_id)
        if sandbox_dir.exists():
            # shutil.rmtree is a blocking I/O operation
            await asyncio.to_thread(shutil.rmtree, sandbox_dir)
            logger.info(f"Deleted sandbox directory: {sandbox_dir}")

    async def list_sandbox_ids(self) -> List[str]:
        if not self.sandboxes_root_dir.is_dir():
            return []
        # Directory iteration can be a blocking I/O operation
        def _sync_list_dirs():
            return [p.name for p in self.sandboxes_root_dir.iterdir() if p.is_dir()]
        return await asyncio.to_thread(_sync_list_dirs)

    # --- 快照持久化方法 (异步) ---
    async def save_snapshot(self, snapshot: StateSnapshot) -> None:
        snapshot_dir = self._get_sandbox_dir(snapshot.sandbox_id) / "snapshots"
        snapshot_dir.mkdir(exist_ok=True)
        file_path = snapshot_dir / f"{snapshot.id}.json"
        async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
            await f.write(snapshot.model_dump_json(indent=2))
        logger.debug(f"Persisted snapshot '{snapshot.id}' for sandbox '{snapshot.sandbox_id}'")

    async def load_snapshot(self, sandbox_id: UUID, snapshot_id: UUID) -> Optional[StateSnapshot]:
        file_path = self._get_sandbox_dir(sandbox_id) / "snapshots" / f"{snapshot_id}.json"
        if not file_path.is_file():
            return None
        async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
            content = await f.read()
        return StateSnapshot.model_validate_json(content)

    async def load_all_snapshots_for_sandbox(self, sandbox_id: UUID) -> List[StateSnapshot]:
        snapshot_dir = self._get_sandbox_dir(sandbox_id) / "snapshots"
        if not snapshot_dir.is_dir():
            return []

        # Reading directory content is I/O-bound
        def _sync_read_files():
            snapshots = []
            for file_path in snapshot_dir.glob("*.json"):
                try:
                    snapshots.append(StateSnapshot.model_validate_json(file_path.read_text(encoding='utf-8')))
                except (ValidationError, json.JSONDecodeError) as e:
                    logger.error(f"Skipping corrupt snapshot file {file_path}: {e}")
            return snapshots
        
        return await asyncio.to_thread(_sync_read_files)
        
    # --- 包/图标 处理方法 (主要是CPU密集型或I/O密集型，设为异步) ---

    async def _embed_zip_in_png(self, zip_bytes: bytes, base_image_bytes: Optional[bytes] = None) -> bytes:
        """(Worker Thread) 将ZIP数据作为zTXt块嵌入到PNG图片中。"""
        def _sync_embed():
            encoded_data = base64.b64encode(zip_bytes).decode('ascii')
            if base_image_bytes:
                image = Image.open(io.BytesIO(base_image_bytes))
            else:
                image = Image.new('RGBA', (1, 1), (0, 0, 0, 255))
            
            png_info_obj = PngImagePlugin.PngInfo()
            png_info_obj.add_text("hevno:data", encoded_data, zip=True)

            buffer = io.BytesIO()
            image.save(buffer, "PNG", pnginfo=png_info_obj)
            return buffer.getvalue()
        
        return await asyncio.to_thread(_sync_embed)

    async def _extract_zip_from_png(self, png_bytes: bytes) -> Tuple[bytes, bytes]:
        """(Worker Thread) 从PNG图片的zTXt块中提取ZIP数据。"""
        def _sync_extract():
            try:
                image = Image.open(io.BytesIO(png_bytes))
                image.load()
                
                # 【核心 Bug 修复】使用正确的键 "hevno:data"
                encoded_data = image.text.get("hevno:data")
                
                if encoded_data is None:
                    raise ValueError("Invalid Hevno package: 'hevno:data' chunk not found.")
                
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

    async def export_package(self, manifest: PackageManifest, data_files: Dict[str, BaseModel], base_image_bytes: Optional[bytes] = None) -> bytes:
        def _sync_zip():
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('manifest.json', manifest.model_dump_json(indent=2))
                for filename, model_instance in data_files.items():
                    file_content = model_instance.model_dump_json(indent=2)
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
                except KeyError:
                    raise ValueError("Package is missing 'manifest.json'.")
                except (ValidationError, json.JSONDecodeError) as e:
                    raise ValueError(f"Invalid 'manifest.json': {e}") from e

                for item in zf.infolist():
                    if item.filename.startswith('data/') and not item.is_dir():
                        relative_path = item.filename.split('data/', 1)[1]
                        data_files[relative_path] = zf.read(item).decode('utf-8')
            return manifest, data_files

        manifest, data_files = await asyncio.to_thread(_sync_unzip)
        return manifest, data_files, png_bytes
        
    # --- 同步方法 (因为它们不执行耗时I/O) ---
    def get_sandbox_icon_path(self, sandbox_id: str) -> Optional[Path]:
        icon_path = self.assets_base_dir / "sandbox_icons" / f"{sandbox_id}.png"
        return icon_path if icon_path.is_file() else None

    def get_default_icon_path(self) -> Path:
        return self.assets_base_dir / "default_sandbox_icon.png"

    # --- 旧的 Asset 方法 (也转换为异步以保持一致性) ---
    def _get_asset_path(self, asset_type: AssetType, asset_name: str) -> Path:
        extension = FILE_EXTENSIONS[asset_type]
        safe_name = Path(asset_name).name 
        return self.assets_base_dir / asset_type.value / f"{safe_name}{extension}"

    async def save_asset(self, asset_model: T, asset_type: AssetType, asset_name: str) -> Path:
        file_path = self._get_asset_path(asset_type, asset_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        json_content = asset_model.model_dump_json(indent=2)
        async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
            await f.write(json_content)
        return file_path

    async def load_asset(self, asset_type: AssetType, asset_name: str, model_class: Type[T]) -> T:
        file_path = self._get_asset_path(asset_type, asset_name)
        if not file_path.exists():
            raise FileNotFoundError(f"Asset '{asset_name}' of type '{asset_type.value}' not found.")
        
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            json_content = await f.read()

        try:
            return model_class.model_validate_json(json_content)
        except ValidationError as e:
            raise ValueError(f"Failed to validate asset '{asset_name}': {e}") from e

    async def list_assets(self, asset_type: AssetType) -> List[str]:
        asset_dir = self.assets_base_dir / asset_type.value
        if not asset_dir.exists():
            return []
        
        extension = FILE_EXTENSIONS[asset_type]
        
        def _sync_list():
            return sorted([p.name.removesuffix(extension) for p in asset_dir.glob(f"*{extension}")])

        return await asyncio.to_thread(_sync_list)