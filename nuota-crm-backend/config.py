# 诺控·塔塔 CRM 全局配置
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置，读取 .env 文件。"""

    # 数据库（psycopg v3 方言）
    DATABASE_URL: str = "postgresql+psycopg://jiuyi@localhost:5432/nuota_crm"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "dev-only-change-me"
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
    ALLOWED_ORIGINS: str = ""

    # 管理后台默认账号
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change-me-admin-password"

    # 上传目录
    STATIC_DIR: str = "/www/nuota-crm/static"
    UPLOAD_DIR: str = "/www/nuota-crm/static/uploads"
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024

    # 微信支付
    WXPAY_SUB_MCH_ID: str = ""
    WXPAY_SUB_APPID: str = ""
    WXPAY_APIV3_KEY: str = ""
    WXPAY_CERT_SERIAL: str = ""
    WXPAY_CERT_DIR: str = "/www/nuota-crm/certs"
    WXPAY_NOTIFY_URL: str = ""
    WXPAY_SP_MCH_ID: str = ""
    WXPAY_SP_APPID: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() in {"prod", "production"}

    @property
    def allowed_origins_list(self) -> list[str]:
        origins = [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        if origins:
            return origins
        if self.is_production:
            return []
        return ["*"]

    def validate_runtime_safety(self) -> None:
        """阻止生产环境带着开发默认值启动。"""
        if not self.is_production:
            return
        insecure = []
        if self.JWT_SECRET == "dev-only-change-me":
            insecure.append("JWT_SECRET")
        if self.ADMIN_PASSWORD == "change-me-admin-password":
            insecure.append("ADMIN_PASSWORD")
        if not self.ALLOWED_ORIGINS:
            insecure.append("ALLOWED_ORIGINS")
        if insecure:
            names = ", ".join(insecure)
            raise RuntimeError(f"生产环境必须配置安全参数: {names}")


settings = Settings()
settings.validate_runtime_safety()
