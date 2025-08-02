# backend/core/loader.py

import json
import logging
import importlib
import importlib.resources
import traceback
from typing import List, Dict

from backend.core.contracts import Container, HookManager, PluginRegisterFunc

# 在模块级别获取 logger
logger = logging.getLogger(__name__)

class PluginLoader:
    def __init__(self, container: Container, hook_manager: HookManager):
        self._container = container
        self._hook_manager = hook_manager

    def load_plugins(self):
        """执行插件加载的全过程：发现、排序、注册。"""
        # 使用 print 是因为此时日志系统可能还未配置
        print("\n--- Hevno 插件系统：开始加载 ---")
        
        # 阶段一：发现
        all_plugins = self._discover_plugins()
        if not all_plugins:
            print("警告：未发现任何插件。")
            print("--- Hevno 插件系统：加载完成 ---\n")
            return

        # 阶段二：排序
        sorted_plugins = sorted(all_plugins, key=lambda p: (p['manifest'].get('priority', 100), p['name']))
        
        # 打印加载顺序，这是一个有用的元信息
        print("插件加载顺序已确定：")
        for i, p_info in enumerate(sorted_plugins):
            print(f"  {i+1}. {p_info['name']} (优先级: {p_info['manifest'].get('priority', 100)})")

        # 阶段三：注册
        self._register_plugins(sorted_plugins)
        
        # 使用配置好的 logger 记录最终信息
        logger.info("所有插件均已加载并注册完毕。")
        print("--- Hevno 插件系统：加载完成 ---\n")


    def _discover_plugins(self) -> List[Dict]:
        """扫描 'plugins' 包，读取所有子包中的 manifest.json 文件。"""
        discovered = []
        try:
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
                    import_path = f"plugins.{plugin_path.name}"
                    
                    plugin_info = { "name": manifest.get('name', plugin_path.name), "manifest": manifest, "import_path": import_path }
                    discovered.append(plugin_info)
                except Exception:
                    # 在发现阶段保持静默，只处理能成功解析的
                    pass
        
        except (ModuleNotFoundError, FileNotFoundError):
             # 同样保持静默，如果没有 plugins 目录就算了
            pass
            
        return discovered
    
    def _register_plugins(self, plugins: List[Dict]):
        """按顺序导入并调用每个插件的注册函数。"""
        for plugin_info in plugins:
            plugin_name = plugin_info['name']
            import_path = plugin_info['import_path']
            
            try:
                # --- 核心改动：这里不再打印日志 ---
                # 日志记录的责任已移交插件本身
                plugin_module = importlib.import_module(import_path)
                register_func: PluginRegisterFunc = getattr(plugin_module, "register_plugin")
                register_func(self._container, self._hook_manager)

            except Exception as e:
                # 只有在发生致命错误时，加载器才需要“发声”
                # 并且使用 print，因为它不依赖于可能出问题的日志系统
                print("\n" + "="*80)
                print(f"!!! 致命错误：加载插件 '{plugin_name}' ({import_path}) 失败 !!!")
                print("="*80)
                traceback.print_exc()
                print("="*80)
                # 遇到错误时，可以选择停止应用或继续加载其他插件
                # 这里我们选择停止，因为插件依赖可能被破坏
                raise RuntimeError(f"无法加载插件 {plugin_name}") from e