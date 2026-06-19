"""
StylePianoDiff Web 平台 - API 路由聚合模块
将所有子路由注册到 api_router，统一在 main.py 中引入
"""

from fastapi import APIRouter

from app.api import composers, generate, history, midi, users

api_router = APIRouter()

# 注册各模块路由，统一添加 /api 前缀
api_router.include_router(composers.router, prefix="/composers", tags=["作曲家风格"])
api_router.include_router(generate.router, prefix="/generate", tags=["生成任务"])
api_router.include_router(history.router, prefix="/history", tags=["生成历史"])
api_router.include_router(midi.router, prefix="/midi", tags=["MIDI文件"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])

__all__ = ["api_router"]
