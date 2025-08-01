# backend/core/loader.py
import os
import pkgutil
import importlib
from typing import List

def load_modules(directories: List[str]):
    """
    动态地扫描并导入指定目录下的所有 Python 模块。

    :param directories: 一个包含要扫描的包目录路径的列表 (e.g., ["backend.runtimes", "backend.llm.providers"])
    """
    print("\n--- Starting Dynamic Module Loading ---")
    for package_name in directories:
        try:
            package = importlib.import_module(package_name)
            
            # 使用 pkgutil.walk_packages 来安全地、递归地查找所有子模块
            for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):
                try:
                    importlib.import_module(module_name)
                except Exception as e:
                    print(f"  - Failed to load module '{module_name}': {e}")
        except ImportError as e:
            print(f"Warning: Could not import package '{package_name}'. Skipping. Error: {e}")
    print("--- Finished Dynamic Module Loading ---\n")