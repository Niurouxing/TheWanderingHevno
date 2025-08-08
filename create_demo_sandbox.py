# create_demo_sandbox.py

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
from uuid import UUID

# 将项目根目录添加到Python路径中，以便可以导入 backend 和 plugins
# 这确保脚本在任何地方都能正确找到模块
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# --- 核心框架组件 ---
from backend.container import Container
from backend.core.hooks import HookManager
from backend.core.loader import PluginLoader
from backend.core.tasks import BackgroundTaskManager

# --- 核心服务接口和数据模型 ---
from plugins.core_engine.contracts import (
    Sandbox, 
    StateSnapshot, 
    SnapshotStoreInterface,
    GenericNode, 
    RuntimeInstruction, 
    GraphDefinition
)
from plugins.core_persistence.contracts import (
    PersistenceServiceInterface, 
    PackageManifest, 
    PackageType
)
from pydantic import BaseModel

# --- 变量配置 ---
BASE_IMAGE_PATH = Path("base_image.png")
OUTPUT_FILENAME_TEMPLATE = "demo_sandbox_{sandbox_id}.png"


async def main():
    """主执行函数"""

    # --------------------------------------------------------------------------
    # 步骤 1: 模拟 FastAPI 应用启动过程 (Lifespan)
    # --------------------------------------------------------------------------
    # 这是最关键的一步。我们必须重现 app.py 中 lifespan 的逻辑，
    # 以确保所有插件都被加载，所有服务都被注册，所有钩子都被初始化。
    print("🔧 [1/5] 模拟应用启动以配置依赖注入容器...")

    container = Container()
    hook_manager = HookManager(container)

    # 1a. 注册平台核心服务
    container.register("container", lambda: container)
    container.register("hook_manager", lambda: hook_manager)
    task_manager = BackgroundTaskManager(container)
    container.register("task_manager", lambda: task_manager, singleton=True)
    hook_manager.add_shared_context("task_manager", task_manager)

    # 1b. 加载所有插件 (同步注册)
    loader = PluginLoader(container, hook_manager)
    loader.load_plugins()

    # 1c. 触发异步服务初始化钩子
    # 这一步至关重要，因为它会填充 RuntimeRegistry, LLM Service 等
    await hook_manager.trigger('services_post_register')
    print("✅ 启动模拟完成。容器已就绪。")


    # --------------------------------------------------------------------------
    # 步骤 2: 从容器中解析我们需要的核心服务
    # --------------------------------------------------------------------------
    # 现在容器已经完全配置好了，我们可以像在API端点中一样获取服务。
    print("\n🔍 [2/5] 从容器中解析核心服务...")
    try:
        sandbox_store: Dict[UUID, Sandbox] = container.resolve("sandbox_store")
        snapshot_store: SnapshotStoreInterface = container.resolve("snapshot_store")
        persistence_service: PersistenceServiceInterface = container.resolve("persistence_service")
        print("✅ 服务解析成功。")
    except ValueError as e:
        print(f"❌ 错误: 无法解析服务: {e}")
        print("   请确保所有核心插件 (core_engine, core_persistence) 都在 'plugins' 目录下且 manifest.json 正确。")
        return


    # --------------------------------------------------------------------------
    # 步骤 3: 定义我们的演示流图
    # --------------------------------------------------------------------------
    # 我们将创建一个简单的图：
    # - 节点1: 输出一个固定的欢迎字符串。
    # - 节点2: 记录一条日志，内容引用节点1的输出。
    print("\n📝 [3/5] 定义演示用流图...")
    
    DEMO_GRAPH_DATA = {
        "main": GraphDefinition(
            nodes=[
                GenericNode(
                    id="welcome_message",
                    run=[RuntimeInstruction(
                        runtime="system.io.input",
                        config={"value": "Hello from the Hevno Engine demo!"}
                    )]
                ),
                GenericNode(
                    id="log_message",
                    depends_on=["welcome_message"], # 虽然宏会自动推断，但明确写出更清晰
                    run=[RuntimeInstruction(
                        runtime="system.io.log",
                        config={"message": "Log Runtime says: {{ nodes.welcome_message.output }}"}
                    )]
                )
            ]
        )
    }
    
    # 将 Pydantic 模型转换为字典以便存储
    demo_graph_dict = {"main": DEMO_GRAPH_DATA["main"].model_dump()}
    print("✅ 流图定义完成。")


    # --------------------------------------------------------------------------
    # 步骤 4: 创建一个 Sandbox 实例
    # --------------------------------------------------------------------------
    # 我们将遵循 core_engine/api.py 中 `create_sandbox` 端点的逻辑。
    print("\n🛠️  [4/5] 创建并初始化 Sandbox 实例...")

    # 4a. 定义沙盒的初始蓝图 (definition)
    sandbox_definition = {
        "initial_lore": {
            "description": "A demo sandbox created by script.",
            "graphs": demo_graph_dict  # 将图定义放在初始知识中
        },
        "initial_moment": {
            "status": "Ready",
            "turn": 0
        }
    }
    
    # 4b. 创建 Sandbox 对象
    sandbox = Sandbox(
        name="演示沙盒 (Demo Sandbox)",
        definition=sandbox_definition,
        lore=sandbox_definition["initial_lore"]  # lore 从 initial_lore 初始化
    )

    # 4c. 创建创世快照 (Genesis Snapshot)
    genesis_snapshot = StateSnapshot(
        sandbox_id=sandbox.id,
        moment=sandbox_definition["initial_moment"] # moment 从 initial_moment 初始化
    )
    
    # 4d. 保存状态
    snapshot_store.save(genesis_snapshot)
    sandbox.head_snapshot_id = genesis_snapshot.id
    sandbox_store[sandbox.id] = sandbox

    print(f"✅ 沙盒 '{sandbox.name}' 创建成功 (ID: {sandbox.id})。")


    # --------------------------------------------------------------------------
    # 步骤 5: 导出 Sandbox 为 PNG
    # --------------------------------------------------------------------------
    # 我们将遵循 core_engine/api.py 中 `export_sandbox` 端点的逻辑。
    print("\n📦 [5/5] 导出沙盒为 PNG 文件...")

    # 5a. 检查基础图片是否存在
    if not BASE_IMAGE_PATH.is_file():
        print(f"❌ 错误: 找不到基础图片 '{BASE_IMAGE_PATH}'。请将你的PNG图片放在项目根目录并命名为 'base_image.png'。")
        return
    base_image_bytes = BASE_IMAGE_PATH.read_bytes()
    print(f"   - 使用基础图片: {BASE_IMAGE_PATH}")

    # 5b. 准备导出数据
    snapshots = snapshot_store.find_by_sandbox(sandbox.id)

    manifest = PackageManifest(
        package_type=PackageType.SANDBOX_ARCHIVE,
        entry_point="sandbox.json",
        metadata={"sandbox_name": sandbox.name, "source": "create_demo_script"}
    )

    # 准备要打包的文件，键是包内路径，值是Pydantic模型实例
    data_files: Dict[str, BaseModel] = {"sandbox.json": sandbox}
    for snap in snapshots:
        data_files[f"snapshots/{snap.id}.json"] = snap

    # 5c. 调用持久化服务执行导出
    try:
        print("   - 调用 persistence_service.export_package...")
        png_bytes = persistence_service.export_package(manifest, data_files, base_image_bytes)
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 5d. 保存最终的PNG文件
    output_filename = OUTPUT_FILENAME_TEMPLATE.format(sandbox_id=sandbox.id)
    with open(output_filename, "wb") as f:
        f.write(png_bytes)

    print("\n" + "="*50)
    print("🎉 成功!")
    print(f"✅ 沙盒已成功导出为: {output_filename}")
    print(f"   现在你可以将这个PNG文件拖拽到前端（未来实现时）进行导入。")
    print("="*50)


if __name__ == "__main__":
    # 使用 asyncio.run 来执行我们的异步 main 函数
    asyncio.run(main())