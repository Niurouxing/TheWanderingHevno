# plugins/core_persistence/contracts.py

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Tuple, TypeVar
from pydantic import BaseModel
from .models import PackageManifest

T = TypeVar('T', bound=BaseModel)

class PersistenceServiceInterface(ABC):
    """
    定义了持久化服务必须提供的核心能力的抽象接口。
    其他插件应该依赖于这个接口，而不是具体的 PersistenceService 类。
    """

    @abstractmethod
    def export_package(self, manifest: PackageManifest, data_files: Dict[str, BaseModel]) -> bytes:
        """
        在内存中创建一个 .hevno.zip 包并返回其字节流。
        """
        raise NotImplementedError

    @abstractmethod
    def import_package(self, zip_bytes: bytes) -> Tuple[PackageManifest, Dict[str, str]]:
        """
        解压包，读取清单和所有数据文件（作为原始字符串）。
        """
        raise NotImplementedError

    # 注意：我们可以选择性地将其他方法（如 save_asset, load_asset）也加入接口，
    # 取决于是否有其他插件需要这些功能。目前 sandbox_router 只用了上面两个。