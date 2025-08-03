# cli.py
import typer
import json
import shutil
from pathlib import Path

from backend.core.plugin_manager import PluginManager

app = typer.Typer(name="hevno", help="Hevno Engine Command-Line Interface")
plugin_app = typer.Typer(name="plugins", help="Manage Hevno plugins.")
app.add_typer(plugin_app)

HEVNO_JSON_PATH = Path("hevno.json")
PLUGINS_DIR = Path("plugins")

@plugin_app.command("sync")
def sync_plugins():
    """
    Synchronizes the 'plugins' directory with the 'hevno.json' manifest.
    This will fetch, update, or remove plugins to match the manifest.
    """
    typer.echo("🔌 Starting plugin synchronization...")
    if not HEVNO_JSON_PATH.exists():
        typer.secho(f"Error: '{HEVNO_JSON_PATH}' not found. Nothing to sync.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    with open(HEVNO_JSON_PATH, "r") as f:
        manifest = json.load(f)

    manager = PluginManager(plugins_dir=PLUGINS_DIR, manifest=manifest.get("plugins", {}))
    
    try:
        manager.sync()
        typer.secho("✅ Plugin synchronization complete.", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"🔥 Error during synchronization: {e}", fg=typer.colors.RED)
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


@plugin_app.command("add")
def add_plugin(
    url: str = typer.Argument(..., help="Git repository URL (e.g., https://github.com/user/repo)."),
    name: str = typer.Option(None, "--name", "-n", help="A specific name for the plugin directory. Defaults to repo name."),
    ref: str = typer.Option("main", "--ref", "-r", help="Git branch, tag, or commit hash."),
    subdir: str = typer.Option(None, "--subdir", "-d", help="Path to the plugin within the repository.")
):
    """
    Adds a new plugin from Git to hevno.json and syncs.
    """
    if not HEVNO_JSON_PATH.exists():
        # 如果文件不存在，创建一个基础结构
        manifest_data = {"plugins": {}}
        typer.echo(f"'{HEVNO_JSON_PATH}' not found, creating a new one.")
    else:
        with open(HEVNO_JSON_PATH, "r") as f:
            manifest_data = json.load(f)
    
    plugin_name = name or Path(url.split('/')[-1]).stem
    
    plugin_config = {"source": "git", "url": url, "ref": ref}
    if subdir:
        plugin_config["subdirectory"] = subdir

    manifest_data["plugins"][plugin_name] = plugin_config

    with open(HEVNO_JSON_PATH, "w") as f:
        json.dump(manifest_data, f, indent=2)

    typer.secho(f"Added plugin '{plugin_name}' to '{HEVNO_JSON_PATH}'.", fg=typer.colors.BLUE)
    # 调用 sync 来完成安装
    sync_plugins()


@plugin_app.command("remove")
def remove_plugin(name: str = typer.Argument(..., help="The name of the plugin to remove.")):
    """
    Removes a plugin from hevno.json and syncs.
    """
    if not HEVNO_JSON_PATH.exists():
        typer.secho(f"Error: '{HEVNO_JSON_PATH}' not found.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    with open(HEVNO_JSON_PATH, "r") as f:
        manifest_data = json.load(f)

    if name not in manifest_data.get("plugins", {}):
        typer.secho(f"Warning: Plugin '{name}' not found in manifest. Nothing to do.", fg=typer.colors.YELLOW)
        return

    del manifest_data["plugins"][name]
    
    with open(HEVNO_JSON_PATH, "w") as f:
        json.dump(manifest_data, f, indent=2)

    typer.secho(f"Removed plugin '{name}' from '{HEVNO_JSON_PATH}'.", fg=typer.colors.BLUE)
    
    # 物理删除目录
    plugin_path = PLUGINS_DIR / name
    if plugin_path.exists():
        shutil.rmtree(plugin_path)
        typer.echo(f"Removed directory: {plugin_path}")
    
    sync_plugins()


if __name__ == "__main__":
    app()