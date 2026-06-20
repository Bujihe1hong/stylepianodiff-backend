"""Pydantic Settings 配置管理"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    # 数据库配置（支持 SQL Server 或 SQLite，部署时通过环境变量切换）
    DATABASE_URL: str = (
        "sqlite:///./stylepianodiff.db"
        # "mssql+pyodbc://sa:YourPassword123@localhost/StylePianoDB?"
        # "driver=ODBC+Driver+17+for+SQL+Server"
    )

    # SQLite 专用连接参数（SQL Server 时无需此参数）
    DATABASE_CONNECT_ARGS: dict = {"check_same_thread": False}


    # JWT 配置
    SECRET_KEY: str = "stylepianodiff-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1天

    # 文件上传配置
    UPLOAD_DIR: Path = Path(__file__).resolve().parent.parent.parent / "uploads"
    GENERATED_DIR: Path = Path(__file__).resolve().parent.parent.parent / "generated"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB

    # 模型路径配置（Linux 容器路径）
    MODEL_PROJECT_PATH: Path = Path("/app/models")
    CHECKPOINT_PATH: Path = Path("/app/models/stage3_best.pt")
    MODEL_CONFIG_PATH: Path = Path("/app/models/config.yaml")
    MODEL_CHECKPOINT_DIR: Path = Path(__file__).resolve().parent.parent.parent / "models"

    # 生成任务配置
    GENERATION_TIMEOUT: int = 120  # 模型推理超时时间（秒）
    DEFAULT_ALPHA: float = 1.0
    DEFAULT_TEMPERATURE: float = 1.0
    DEFAULT_TARGET_BARS: int = 8

    # FastAPI 服务配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"

    # 应用配置
    APP_NAME: str = "StylePianoDiff API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # 日志配置
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        arbitrary_types_allowed = True


settings = Settings()
