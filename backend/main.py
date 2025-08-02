# backend/main.py 

import uvicorn
import os 
from backend.app import create_app

# 调用工厂函数来获取完全配置好的应用实例
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app", 
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True, # 在开发时启用重载
        reload_dirs=["backend"]
    )