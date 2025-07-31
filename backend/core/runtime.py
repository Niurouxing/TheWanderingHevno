# 这个文件现在只是为了向后兼容导入路径。
# 所有新的定义都在 core.interfaces 中。
# 理想情况下，可以删除这个文件，并更新所有导入。

from backend.core.interfaces import RuntimeInterface, SubGraphRunner

# 让 linter 知道这些名字是被有意导入和导出的
__all__ = ["RuntimeInterface", "SubGraphRunner"]