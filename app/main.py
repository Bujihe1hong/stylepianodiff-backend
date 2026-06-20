"""FastAPI 主入口：注册路由、CORS、异常处理"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import api_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="StylePianoDiff Web 平台后端 API",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://stylepianodiff-web.vercel.app/",  # 生产环境
        "http://localhost:5173",  # 本地开发
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(api_router, prefix="/api")


# 全局异常处理：统一返回 JSON 格式
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": f"服务器内部错误: {str(exc)}", "data": None},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=404,
        content={"code": 404, "message": "请求的资源不存在", "data": None},
    )


# 健康检查接口（公开）
@app.get("/api/health", response_model=dict)
def health_check() -> dict:
    """系统健康状态检查"""
    return {"code": 200, "message": "服务运行正常", "data": {"status": "ok", "version": settings.APP_VERSION}}


# Railway 默认健康检查路径
@app.get("/health", response_model=dict)
def railway_health_check() -> dict:
    """Railway 平台健康检查"""
    return {"status": "ok", "timestamp": "2024-06-19"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
