# 诺控·塔塔 CRM —— FastAPI 入口
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy import text

from config import settings
from database import engine, Base, SessionLocal, get_db
from sqlalchemy.orm import Session
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
from routers.customers import router as customers_router
from routers.services import router as services_router, admin_router as services_admin_router
from routers.agreements import router as agreements_router
from routers.calendar import router as calendar_router, public_router as calendar_public_router
from routers.consultant_auth import router as consultant_auth_router, admin_router as consultant_auth_admin_router
from routers.notifications import router as notifications_router
from routers.followup import router as followup_router
from routers.enterprise import router as enterprise_router
from routers.articles import router as articles_router, admin_router as articles_admin_router
from routers.courses import router as courses_router, admin_router as courses_admin_router
from routers.course_sessions import (
    admin_router as cs_admin_router,
    router as cs_router,
    webhook_router as cs_webhook_router,
)
from routers.agents import router as agents_router
from routers.webhook_events import router as webhook_events_router, admin_router as webhook_admin_router
from routers.agent_api import router as agent_api_router
from routers.saas_bridge import router as saas_bridge_router
from utils.auth import hash_password, get_current_admin


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
            logger.info(f"已创建默认管理员：{settings.ADMIN_USERNAME}")
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


import asyncio
from datetime import datetime as _dt, time as _time


async def _daily_debt_reminder_loop():
    """每天 09:00 执行一次追款提醒。"""
    while True:
        now = _dt.now()
        # 计算距下一个 09:00 的秒数
        target = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if now >= target:
            from datetime import timedelta
            target = target + timedelta(days=1)
        wait_sec = (target - now).total_seconds()
        await asyncio.sleep(wait_sec)
        try:
            from tasks.debt_reminder import run as debt_run
            debt_run()
            logger.info("[debt_reminder] 每日追款提醒执行完毕")
        except Exception as e:
            logger.error(f"[debt_reminder] 定时任务异常: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建表（与 sql/schema.sql 互补）+ 默认管理员
    try:
        Base.metadata.create_all(bind=engine)
        _ensure_schema()
        _ensure_admin()
    except Exception as e:
        logger.warning(f"启动初始化告警：{e}")
    # 启动每日追款提醒后台任务
    task = asyncio.create_task(_daily_debt_reminder_loop())
    yield
    task.cancel()


app = FastAPI(
    title="诺控·塔塔 CRM API",
    version="1.0.0",
    description="学员全生命周期管理（小程序 + 管理后台）",
    lifespan=lifespan,
)

# CORS：允许管理后台 / 小程序（小程序自身不受 CORS 限制）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
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


@app.post("/admin/migrate-consultant-v2", tags=["system"])
def migrate_consultant_v2(db: Session = Depends(get_db), _=Depends(get_current_admin)):
    """一次性迁移：加顾问字段+新建两张表"""
    from sqlalchemy import text
    results = []
    try:
        db.execute(text("ALTER TABLE consultants ADD COLUMN IF NOT EXISTS service_modules TEXT"))
        results.append("OK: service_modules")
    except Exception as e:
        results.append(f"SKIP service_modules: {e}")
    try:
        db.execute(text("ALTER TABLE consultants ADD COLUMN IF NOT EXISTS password_hash VARCHAR(128)"))
        results.append("OK: password_hash")
    except Exception as e:
        results.append(f"SKIP password_hash: {e}")
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS consultant_applications (
            id SERIAL PRIMARY KEY, name VARCHAR(50) NOT NULL,
            phone VARCHAR(20) NOT NULL UNIQUE, specialty VARCHAR(100), company VARCHAR(100),
            service_modules TEXT, password_hash VARCHAR(128) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending', reviewed_by INTEGER,
            review_note TEXT, reviewed_at TIMESTAMP, created_at TIMESTAMP DEFAULT NOW()
        )
    """))
    results.append("OK: consultant_applications")
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS consultant_invite_codes (
            id SERIAL PRIMARY KEY, consultant_id INTEGER, code VARCHAR(32) UNIQUE NOT NULL,
            used_count INTEGER DEFAULT 0, max_uses INTEGER DEFAULT 100,
            is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMP DEFAULT NOW()
        )
    """))
    results.append("OK: consultant_invite_codes")
    db.commit()
    return {"code": 0, "results": results}


# ---- 学员端路由 ----

# 公开分公司列表（注册页用，不需要token）
from fastapi import APIRouter as _AR
_public_router = _AR(tags=["public"])

@_public_router.get("/admin/branches/public")
def public_branches(db = Depends(get_db)):
    from models.branch import Branch
    items = db.query(Branch).filter(Branch.status == "active").order_by(Branch.id).all()
    return {"code": 0, "msg": "ok", "data": [{"id": b.id, "name": b.name, "short_name": b.short_name, "city": b.city} for b in items]}

app.include_router(_public_router)

app.include_router(auth_router)
app.include_router(members_router)
app.include_router(face_router)
app.include_router(checkin_router)
app.include_router(sessions_router)
app.include_router(referrals_router)
app.include_router(rewards_router)
app.include_router(bookings_router)
app.include_router(handbooks_router)
app.include_router(services_router)
app.include_router(agreements_router)

# ---- 管理端路由 ----
app.include_router(auth_admin_router)
app.include_router(checkin_admin_router)
app.include_router(sessions_admin_router)
app.include_router(referrals_admin_router)
app.include_router(rewards_admin_router)
app.include_router(bookings_admin_router)
app.include_router(quota_router)
app.include_router(handbooks_admin_router)
app.include_router(services_admin_router)
app.include_router(admin_router)
app.include_router(customers_router)
app.include_router(calendar_router)
app.include_router(calendar_public_router)
app.include_router(consultant_auth_router)
app.include_router(consultant_auth_admin_router)
app.include_router(notifications_router)
app.include_router(followup_router)
app.include_router(enterprise_router)
app.include_router(articles_router)
app.include_router(articles_admin_router)
app.include_router(courses_router)
app.include_router(courses_admin_router)
app.include_router(cs_admin_router)
app.include_router(cs_router)
app.include_router(cs_webhook_router)
app.include_router(agents_router)
app.include_router(webhook_events_router)
app.include_router(webhook_admin_router)
app.include_router(agent_api_router)
app.include_router(saas_bridge_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)

# ── 文件上传 ──
from routers.upload import router as upload_router
app.include_router(upload_router)

# ── 静态文件 ──
from starlette.staticfiles import StaticFiles
import os
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount('/static', StaticFiles(directory=settings.STATIC_DIR), name='static')

# ── 微信支付 ──
from routers.payment import router as payment_router
app.include_router(payment_router)

# 推荐码验证API
from routers.referral_api import router as referral_verify_router
app.include_router(referral_verify_router)

# 会员通知接口（小程序端）
from routers.member_notifications import router as member_notif_router
from routers.salary import router as salary_router
app.include_router(member_notif_router)
app.include_router(salary_router)
from routers.promotion import router as promotion_router
app.include_router(promotion_router)
from routers.banners import router as banners_router
app.include_router(banners_router)
# 采购+储值管理（2026-06-02）
from routers.purchase_recharge import router as pr_router
app.include_router(pr_router)

# 会员深度分析 + 老师人才模型分析（2026-06-02·塔才）
from routers.deep_analysis import router as da_router
app.include_router(da_router)
