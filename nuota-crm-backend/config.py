# 诺控·塔塔 CRM 全局配置
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置，读取 .env 文件。"""

    # 数据库
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/nuota_crm"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "nuota-tata-crm-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7

    # 微信小程序
    WX_APPID: str = "CONFIG.WX_APPID"
    WX_SECRET: str = "CONFIG.WX_SECRET"

    # 腾讯云人脸核身
    TENCENT_SECRET_ID: str = "CONFIG.TENCENT_SECRET_ID"
    TENCENT_SECRET_KEY: str = "CONFIG.TENCENT_SECRET_KEY"
    TENCENT_FACE_GROUP: str = "nuota_tata_members"
    TENCENT_REGION: str = "ap-guangzhou"

    # 企微通知
    WECOM_WEBHOOK: str = "CONFIG.WECOM_WEBHOOK"

    # 应用
    APP_NAME: str = "nuota-crm-backend"
    APP_ENV: str = "dev"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # 管理后台默认账号
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
