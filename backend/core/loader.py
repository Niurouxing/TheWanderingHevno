# backend/core/loader.py

import json
import logging
import importlib
import importlib.resources
import traceback
from typing import List, Dict

# 导入类型提示，而不是实现
from backend.core.contracts import Container, HookManager, PluginRegisterFunc

logger = logging.getLogger(__name__)

class PluginLoader:
    def __init__(self, container: Container, hook_manager: HookManager):
        self._container = container
        self._hook_manager = hook_manager

    def load_plugins(self):
        """执行插件加载的全过程：发现、排序、注册。"""
        # 在日志系统配置前使用 print
        print("\n--- Hevno 插件系统：开始加载 ---")
        
        # 阶段一：发现
        all_plugins = self._discover_plugins()
        if not all_plugins:
            print("警告：在 'plugins' 目录中未发现任何插件。")
            print("--- Hevno 插件系统：加载完成 ---\n")
            return

        # 阶段二：排序 (根据 manifest 中的 priority)
        sorted_plugins = sorted(all_plugins, key=lambda p: (p['manifest'].get('priority', 100), p['name']))
        
        print("插件加载顺序已确定：")
        for i, p_info in enumerate(sorted_plugins):
            print(f"  {i+1}. {p_info['name']} (优先级: {p_info['manifest'].get('priority', 100)})")

        # 阶段三：注册
        self._register_plugins(sorted_plugins)
        
        logger.info("所有已发现的插件均已加载并注册完毕。")
        print("--- Hevno 插件系统：加载完成 ---\n")

    def _discover_plugins(self) -> List[Dict]:
        """扫描 'plugins' 包，读取所有子包中的 manifest.json 文件。"""
        discovered = []
        try:
            # 使用现代的 importlib.resources 来安全地访问包数据
            plugins_package_path = importlib.resources.files('plugins')
            
            for plugin_path in plugins_package_path.iterdir():
                if not plugin_path.is_dir() or plugin_path.name.startswith(('__', '.')):
                    continue

                manifest_path = plugin_path / "manifest.json"
                if not manifest_path.is_file():
                    continue
                
                try:
                    manifest_content = manifest_path.read_text(encoding='utf-8')
                    manifest = json.loads(manifest_content)
                    # 构造 Python 导入路径
                    import_path = f"plugins.{plugin_path.name}"
                    
                    plugin_info = {
                        "name": manifest.get('name', plugin_path.name),
                        "manifest": manifest,
                        "import_path": import_path
                    }
                    discovered.append(plugin_info)
                except Exception as e:
                    print(f"警告：无法解析插件 '{plugin_path.name}' 的 manifest.json: {e}")
                    pass
        
        except (ModuleNotFoundError, FileNotFoundError):
            print("信息：'plugins' 目录不存在或为空，跳过插件加载。")
            pass
            
        return discovered
    
    def _register_plugins(self, plugins: List[Dict]):
        """按顺序导入并调用每个插件的注册函数。"""
        for plugin_info in plugins:
            plugin_name = plugin_info['name']
            import_path = plugin_info['import_path']
            
            try:
                plugin_module = importlib.import_module(import_path)
                
                if not hasattr(plugin_module, "register_plugin"):
                    print(f"警告：插件 '{plugin_name}' 未定义 'register_plugin' 函数，已跳过。")
                    continue
                
                register_func: PluginRegisterFunc = getattr(plugin_module, "register_plugin")
                # 将核心服务注入到插件的注册函数中
                register_func(self._container, self._hook_manager)

            except Exception as e:
                print("\n" + "="*80)
                print(f"!!! 致命错误：加载插件 '{plugin_name}' ({import_path}) 失败 !!!")
                print("="*80)
                traceback.print_exc()
                print("="*80)
                raise RuntimeError(f"无法加载插件 {plugin_name}，应用启动中止。") from e