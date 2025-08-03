# backend/core/plugin_manager.py
import httpx
import zipfile
import io
import shutil
from pathlib import Path
from typing import Dict, Any

class PluginManager:
    def __init__(self, plugins_dir: Path, manifest: Dict[str, Any]):
        self.plugins_dir = plugins_dir
        self.manifest = manifest
        self.plugins_dir.mkdir(exist_ok=True)

    def sync(self):
        """
        Main sync method. Ensures the plugins directory matches the manifest.
        """
        print("--- Plugin Sync ---")
        # 1. 移除不再需要的插件
        self._clean_removed_plugins()
        # 2. 安装或更新声明的 Git 插件
        for name, config in self.manifest.items():
            if config.get("source") == "git":
                self._install_git_plugin(name, config)
            elif config.get("source") == "local":
                # 确认本地插件存在，如果不存在则警告
                if not (self.plugins_dir / name).exists():
                     print(f"  - ⚠️ Warning: Local plugin '{name}' declared in manifest but not found in filesystem.")
                else:
                    print(f"  - ✅ Keeping local plugin: {name}")

        print("-------------------")

    def _clean_removed_plugins(self):
        """
        Removes any directories in 'plugins/' that are not declared in the manifest.
        This correctly handles plugins that were removed from hevno.json.
        """
        print("🧹 Checking for stale plugins to remove...")
        if not self.plugins_dir.exists():
            return

        declared_plugins = set(self.manifest.keys())

        for item in self.plugins_dir.iterdir():
            # 我们只关心目录，并且忽略像 __pycache__ 这样的特殊目录
            if item.is_dir() and not item.name.startswith(('__', '.')):
                if item.name not in declared_plugins:
                    print(f"  - Removing stale plugin: {item.name}")
                    shutil.rmtree(item)

    def _install_git_plugin(self, name: str, config: Dict[str, Any]):
        """
        Fetches a plugin from a Git repository zip archive and installs it.
        Behavior depends on the 'strategy' config.
        """
        url = config["url"]
        ref = config["ref"]
        subdir = config.get("subdirectory") 
        strategy = config.get("strategy", "pin") # 默认是 "pin"
        target_dir = self.plugins_dir / name

        # 核心逻辑变更：
        # 1. 如果是 'latest' 策略，并且目录存在，则强制删除以进行更新。
        if strategy == "latest" and target_dir.exists():
            print(f"  - 🔄 Updating '{name}' to latest from branch '{ref}'. Removing old version.")
            shutil.rmtree(target_dir)
        # 2. 如果是 'pin' 策略，并且目录已存在，则跳过（保持现有行为）。
        elif strategy == "pin" and target_dir.exists():
            print(f"  - ✅ Plugin '{name}' is pinned and already exists. Skipping.")
            return

        # 如果目录不存在（或已被删除），则执行安装流程
        print(f"  - 📥 Installing '{name}' from {url} @ {ref}")
        
        repo_path = url.replace("https://github.com/", "")
        zip_url = f"https://github.com/{repo_path}/archive/{ref}.zip"

        try:
            with httpx.Client() as client:
                response = client.get(zip_url, follow_redirects=True, timeout=60)
                response.raise_for_status()
            
            zip_bytes = io.BytesIO(response.content)

            with zipfile.ZipFile(zip_bytes) as zf:
                root_folder_name = zf.namelist()[0]
                source_path_in_zip = Path(root_folder_name) / (subdir or "")

                for member in zf.infolist():
                    try:
                        member_path = Path(member.filename)
                        # 检查成员是否在我们的目标子目录内
                        relative_path = member_path.relative_to(source_path_in_zip)
                    except ValueError:
                        continue # 不是我们关心的文件，跳过

                    # 目标路径现在是 `plugins/{plugin_name}/{relative_path}`
                    final_target_path = target_dir / relative_path

                    if member.is_dir():
                        final_target_path.mkdir(parents=True, exist_ok=True)
                    else:
                        final_target_path.parent.mkdir(parents=True, exist_ok=True)
                        with final_target_path.open("wb") as f_out:
                            f_out.write(zf.read(member.filename))

        except httpx.HTTPStatusError as e:
            raise IOError(f"Failed to download plugin '{name}' from {zip_url}. Status: {e.response.status_code}") from e
        except Exception as e:
            if target_dir.exists():
                shutil.rmtree(target_dir)
            raise IOError(f"An error occurred while installing plugin '{name}': {e}") from e