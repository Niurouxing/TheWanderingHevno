# plugins/core_persistence/service.py

import io
import json
import zipfile
import logging
from pathlib import Path
from typing import Type, TypeVar, Tuple, Dict, Any, List, Optional
from pydantic import BaseModel, ValidationError
import base64
from PIL import Image, PngImagePlugin

from .contracts import PersistenceServiceInterface, PackageManifest
from .models import AssetType, FILE_EXTENSIONS

T = TypeVar('T', bound=BaseModel)
logger = logging.getLogger(__name__)

class PersistenceService(PersistenceServiceInterface):
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
    
    def _embed_zip_in_png(self, zip_bytes: bytes, base_image_bytes: Optional[bytes] = None) -> bytes:
        """将ZIP数据作为标准的zTXt块嵌入到PNG图片中。"""
        logger.debug(f"[EMBED] Received zip_bytes with size: {len(zip_bytes)}")
        
        encoded_data = base64.b64encode(zip_bytes).decode('ascii')
        logger.debug(f"[EMBED] Base64 encoded data size: {len(encoded_data)}")

        if base_image_bytes:
            image = Image.open(io.BytesIO(base_image_bytes))
            logger.debug(f"[EMBED] Using provided base image with size: {len(base_image_bytes)}")
        else:
            image = Image.new('RGBA', (1, 1), (0, 0, 0, 255))
            logger.debug("[EMBED] No base image provided, creating a new 1x1 PNG.")
        
        # --- 【核心修正】创建一个只包含我们自定义数据的 PngInfo 对象 ---
        png_info_obj = PngImagePlugin.PngInfo()
        png_info_obj.add_text("hevno:data", encoded_data, zip=True)
        logger.debug("[EMBED] Created a new PngInfo object containing only our 'hevno:data' ztxt chunk.")

        buffer = io.BytesIO()
        # --- 【核心修正】让 Pillow 的 save 方法自动处理和保留原始元数据 ---
        # save 方法会自动保留原始图像的必要块（如 PLTE, tRNS），
        # 然后再附加我们通过 pnginfo 参数提供的新块。
        image.save(buffer, "PNG", pnginfo=png_info_obj)
        
        output_bytes = buffer.getvalue()
        logger.debug(f"[EMBED] Final PNG size: {len(output_bytes)}")
        
        # --- 添加验证步骤 ---
        try:
            with Image.open(io.BytesIO(output_bytes)) as verification_image:
                verification_image.verify() # 检查文件结构的完整性
            logger.debug("[EMBED] Self-verification successful: The generated PNG is valid.")
        except Exception as e:
            logger.error(f"[EMBED] Self-verification FAILED: The generated PNG is corrupted. Error: {e}")
            # 如果我们生成了损坏的文件，最好抛出异常而不是返回它
            raise IOError("Failed to generate a valid PNG file after embedding data.") from e

        return output_bytes

    def _extract_zip_from_png(self, png_bytes: bytes) -> Tuple[bytes, bytes]:
        """从PNG图片的zTXt块中提取ZIP数据。"""
        logger.debug(f"[EXTRACT] Received png_bytes with size: {len(png_bytes)}")
        try:
            image = Image.open(io.BytesIO(png_bytes))
            image.load()
            logger.debug(f"[EXTRACT] Image text chunks from loaded PNG: {image.text}")

            # --- 【核心修正】从 image.text 字典中查找我们的数据 ---
            encoded_data = image.text.get("hevno:data")
            
            if encoded_data is None:
                logger.error("[EXTRACT] 'hevno:data' zTXt chunk NOT FOUND in image text chunks.")
                raise ValueError("Invalid Hevno package: 'hevno:data' chunk not found.")
            
            # --- 【核心修正】解码 ---
            zip_data = base64.b64decode(encoded_data)
            logger.debug(f"[EXTRACT] Found and decoded 'hevno:data' chunk. Original zip size: {len(zip_data)}")
            return zip_data, png_bytes
        except Exception as e:
            logger.error(f"[EXTRACT] Exception while processing PNG: {e}", exc_info=True)
            raise ValueError(f"Failed to process PNG file: {e}") from e

    def save_sandbox_icon(self, sandbox_id: str, icon_bytes: bytes) -> Path:
        """保存沙盒图标文件。"""
        icon_path = self.assets_base_dir / "sandbox_icons" / f"{sandbox_id}.png"
        icon_path.parent.mkdir(parents=True, exist_ok=True)
        icon_path.write_bytes(icon_bytes)
        logger.info(f"Saved icon for sandbox {sandbox_id} to {icon_path}")
        return icon_path

    def get_sandbox_icon_path(self, sandbox_id: str) -> Optional[Path]:
        """获取沙盒图标的文件路径，如果不存在则返回None。"""
        icon_path = self.assets_base_dir / "sandbox_icons" / f"{sandbox_id}.png"
        return icon_path if icon_path.is_file() else None

    def get_default_icon_path(self) -> Path:
        """获取默认图标的路径。"""
        return self.assets_base_dir / "default_sandbox_icon.png"

    def export_package(self, manifest: PackageManifest, data_files: Dict[str, BaseModel], base_image_bytes: Optional[bytes] = None) -> bytes:
        """在内存中创建一个 .hevno.zip 包，嵌入PNG，并返回其字节流。"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('manifest.json', manifest.model_dump_json(indent=2))
            for filename, model_instance in data_files.items():
                file_content = model_instance.model_dump_json(indent=2)
                zf.writestr(f'data/{filename}', file_content)
        
        zip_bytes = zip_buffer.getvalue()
        return self._embed_zip_in_png(zip_bytes, base_image_bytes)

    def import_package(self, package_bytes: bytes) -> Tuple[PackageManifest, Dict[str, str], bytes]:
        """从PNG中解压包，返回清单、数据文件和原始PNG图像字节。"""
        zip_bytes, png_bytes = self._extract_zip_from_png(package_bytes)
        
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
        
        return manifest, data_files, png_bytes