"""
StylePianoDiff Web 平台 - 后端配置兼容模块
实际配置定义在 app.core.config 中，本模块提供向后兼容的导入路径
"""

from app.core.config import Settings, settings

__all__ = ["Settings", "settings"]
