
## **需求文档：前端插件资源动态服务**

**版本**: 1.0
**提出者**: 前端团队
**目标**: 实现一个优雅、可扩展的机制，让后端能够动态服务所有前端插件的静态资源（JS, CSS, 图像等）。

### 1. 核心问题 (The Problem)

我们的前端是一个“微型操作系统”，其功能和UI完全由动态加载的**插件**构成。每个插件都是一个独立的包，包含自己的前端代码（如 `dist/index.js`）。

目前，前端内核通过 `/api/plugins/manifest` 端点获取插件列表及其入口文件路径（如 `/plugins/core_layout/dist/index.js`）。然而，当浏览器尝试请求这个URL时，后端无法识别并返回404错误，因为没有一个机制能将 `/plugins/...` 这样的URL路径映射到服务器上实际的插件文件位置。

### 2. 目标与需求 (The Goal)

我们需要一个后端API端点，它能像一个**智能的、统一的资源网关**一样，处理所有前端插件的资源请求。

#### **具体需求:**

1.  **统一的URL结构**: 所有插件的资源都应通过一个统一的、可预测的URL前缀进行访问。我们建议使用 `/plugins`。
    *   例如，要访问 `core_layout` 插件的 `dist/bundle.css` 文件，前端将请求 `GET /plugins/core_layout/dist/bundle.css`。

2.  **动态路径解析**: 后端必须能够将上述URL动态地解析到服务器文件系统上的正确路径。
    *   `GET /plugins/core_layout/dist/bundle.css` -> 应返回 `[项目根目录]/plugins/core_layout/dist/bundle.css` 文件的内容。
    *   `GET /plugins/world-viewer/assets/icon.svg` -> 应返回 `[项目根目录]/plugins/world-viewer/assets/icon.svg` 文件的内容。

3.  **极简实现**: 该功能应作为后端核心能力的一部分，避免复杂的配置。理想情况下，它应该能自动发现并服务所有位于 `plugins/` 目录下的插件资源。

### 3. 实现建议 (Proposed Solution)

我们建议创建一个**单一的、动态的API路由**来处理所有这类请求，而不是为每个插件或每个子目录单独挂载静态文件服务。

#### **API端点规格:**

*   **HTTP方法**: `GET`
*   **路径**: `/plugins/{plugin_id}/{resource_path:path}`
    *   `plugin_id` (string): 插件的唯一ID，即它在 `plugins/` 目录下的文件夹名称。
    *   `resource_path` (path): 插件内部的任意文件路径。

#### **工作流 (Workflow):**

1.  前端浏览器向后端发送请求，例如 `GET /plugins/core_layout/frontend/dist/index.js`。
2.  FastAPI的路由系统匹配到 `/plugins/{plugin_id}/{resource_path:path}`。
3.  路由处理函数接收到参数:
    *   `plugin_id = "core_layout"`
    *   `resource_path = "frontend/dist/index.js"`
4.  在函数内部，后端执行以下逻辑：
    a.  **构建物理文件路径**: 将插件ID和资源路径拼接成服务器上的绝对文件路径。
        ```
        # 伪代码
        base_plugins_dir = "path/to/project/plugins"
        target_file_path = Path(base_plugins_dir) / plugin_id / resource_path
        ```
    b.  **安全检查 (可选，但推荐)**: 验证 `target_file_path` 是否确实位于 `base_plugins_dir` 内部，防止路径遍历攻击（如 `../../secrets.txt`）。
    c.  **文件存在性检查**: 检查文件是否存在。如果不存在，返回 `404 Not Found`。
    d.  **返回文件**: 如果文件存在，使用 `FileResponse` (FastAPI) 或类似机制，将文件内容作为响应体返回。系统应能自动推断正确的 `Content-Type` (如 `application/javascript`, `text/css`)。

#### **FastAPI 实现伪代码:**

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

# 假设这个路由器会被包含在主应用中
plugins_router = APIRouter()

# 项目根目录下的 'plugins' 文件夹
BASE_PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"

@plugins_router.get("/plugins/{plugin_id}/{resource_path:path}")
async def serve_plugin_resource(plugin_id: str, resource_path: str):
    """
    动态服务任何插件的任何静态资源。
    """
    try:
        # 1. 构建目标文件的路径
        target_file = (BASE_PLUGINS_DIR / plugin_id / resource_path).resolve()

        # 2. 安全性：确保请求的文件在合法的插件目录内
        if not str(target_file).startswith(str(BASE_PLUGINS_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Forbidden: Access denied.")

        # 3. 检查文件是否存在
        if not target_file.is_file():
            raise HTTPException(status_code=404, detail="Resource not found.")

        # 4. 返回文件响应，FastAPI会自动处理Content-Type
        return FileResponse(target_file)
        
    except Exception as e:
        # 捕获其他潜在错误，例如路径构建失败
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

```

### 4. 收益 (Benefits)

*   **优雅与简洁**: 只有一个API端点，就解决了所有插件的资源服务问题，无需为每个插件写一行配置。
*   **可扩展性**: 当添加新插件时，**后端无需任何代码改动或重启**。只要文件存在于 `plugins/` 目录下，它们就立即可通过URL访问。
*   **解耦**: 前端不需要知道后端的具体文件系统结构，只需要遵循 ` /plugins/{id}/{path}` 的URL约定即可。