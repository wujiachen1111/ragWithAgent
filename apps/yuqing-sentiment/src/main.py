"""
YuQing舆情分析系统入口
"""

import os
import uvicorn


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))

    uvicorn.run("yuqing.main:app", host=host, port=port, reload=True)