# 诺控·塔塔 CRM —— FastAPI 入口
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import text

from config import settings
from database import engine, Base, SessionLocal
import models  # noqa: F401 —— 触发模型注册
from models import AdminUser

from routers.auth import router as auth_router, admin_router as auth_admin_router
from routers.members import router as members_router
from routers.face import router as face_router
from routers.checkin import router as checkin_router, admin_router as checkin_admin_router
from routers.sessions import router as sessions_router, admin_router as sessions_admin_router
from routers.referrals import router as referrals_router, admin_router as referrals_admin_router
from routers.rewards import router as rewards_router, admin_router as rewards_admin_router
from routers.bookings import (
    router as bookings_router,
    admin_router as bookings_admin_router,
    quota_router,
)
from routers.handbooks import router as handbooks_router, admin_router as handbooks_admin_router
from routers.admin import router as admin_router
from utils.auth import hash_password


def _ensure_admin():
    """首次启动：默认管理员账号自动创建。"""
    db = SessionLocal()
    try:
        exist = db.query(AdminUser).filter(AdminUser.username == settings.ADMIN_USERNAME).first()
        if not exist:
            db.add(AdminUser(
                username=settings.ADMIN_USERNAME,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                real_name="超级管理员",
                role="admin",
                status="active",
            ))
            db.commit()
            logger.info(f"已创建默认管理员：{settings.ADMIN_USERNAME} / {settings.ADMIN_PASSWORD}")
    finally:
        db.close()


def _ensure_schema():
    """对齐 ORM 新增字段（openid / admin_users 表）。使用 IF NOT EXISTS 幂等执行。"""
    stmts = [
        "ALTER TABLE members ADD COLUMN IF NOT EXISTS openid VARCHAR(64)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_members_openid ON members(openid) WHERE openid IS NOT NULL",
        """
        CREATE TABLE IF NOT EXISTS admin_users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            real_name VARCHAR(50),
            phone VARCHAR(20),
            role VARCHAR(20) DEFAULT 'admin',
            status VARCHAR(20) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
    ]
    with engine.begin() as conn:
        for s in stmts:
            conn.execute(text(s))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建表（与 sql/schema.sql 互补）+ 默认管理员
    try:
        Base.metadata.create_all(bind=engine)
        _ensure_schema()
        _ensure_admin()
    except Exception as e:
        logger.warning(f"启动初始化告警：{e}")
    yield


app = FastAPI(
    title="诺控·塔塔 CRM API",
    version="1.0.0",
    description="学员全生命周期管理（小程序 + 管理后台）",
    lifespan=lifespan,
)

# CORS：允许管理后台 / 小程序（小程序自身不受 CORS 限制）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"code": 422, "msg": "参数校验失败", "data": exc.errors()},
    )


@app.get("/health", tags=["system"])
def health():
    return {"code": 0, "msg": "ok", "data": {"app": settings.APP_NAME, "env": settings.APP_ENV}}


# ---- 学员端路由 ----
app.include_router(auth_router)
app.include_router(members_router)
app.include_router(face_router)
app.include_router(checkin_router)
app.include_router(sessions_router)
app.include_router(referrals_router)
app.include_router(rewards_router)
app.include_router(bookings_router)
app.include_router(handbooks_router)

# ---- 管理端路由 ----
app.include_router(auth_admin_router)
app.include_router(checkin_admin_router)
app.include_router(sessions_admin_router)
app.include_router(referrals_admin_router)
app.include_router(rewards_admin_router)
app.include_router(bookings_admin_router)
app.include_router(quota_router)
app.include_router(handbooks_admin_router)
app.include_router(admin_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
