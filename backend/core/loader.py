# backend/core/loader.py
import os
import pkgutil
import importlib
from typing import List
from pathlib import Path

# 从新模块导入 HookManager 类型提示
from backend.core.hooks import HookManager

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

def load_plugins(hook_manager: HookManager):
    """
    动态扫描 `plugins/` 目录，发现并注册所有插件。

    :param hook_manager: 一个 HookManager 实例，插件将向其注册钩子。
    """
    print("\n--- Starting Plugin Loading ---")
    
    # 假设项目根目录是 backend 目录的父目录
    project_root = Path(__file__).parent.parent.parent 
    plugins_dir = project_root / "plugins"

    if not plugins_dir.is_dir():
        print(f"Plugin directory not found at '{plugins_dir}'. Skipping.")
        print("--- Finished Plugin Loading ---")
        return

    # 将插件目录添加到 Python 路径中，以便能够导入它们
    import sys
    if str(plugins_dir) not in sys.path:
        sys.path.insert(0, str(plugins_dir))

    # 遍历 `plugins/` 下的每个子目录（每个子目录是一个插件）
    for plugin_path in plugins_dir.iterdir():
        if plugin_path.is_dir():
            plugin_name = plugin_path.name
            try:
                # 动态导入插件的入口模块 (e.g., import example_logger)
                plugin_module = importlib.import_module(plugin_name)
                
                # 检查插件是否定义了 `register_plugin` 函数
                if hasattr(plugin_module, "register_plugin"):
                    register_func = getattr(plugin_module, "register_plugin")
                    # 调用注册函数，并将 hook_manager 实例传递进去
                    register_func(hook_manager)
                    print(f"  - Successfully loaded and registered plugin: '{plugin_name}'")
                else:
                    print(f"  - Warning: Plugin '{plugin_name}' found, but it has no 'register_plugin' function.")

            except Exception as e:
                print(f"  - Failed to load plugin '{plugin_name}': {e}")
                import traceback
                traceback.print_exc()

    print("--- Finished Plugin Loading ---\n")