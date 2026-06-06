# 内容管理路由 —— 企业文化/行业动态/品牌宣传/视频号
# 2026-05-15
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import Session

from database import get_db, Base
from services.audit_service import log_action
from utils.auth import get_current_admin

# ══════════════════ ORM ══════════════════
class Article(Base):
    __tablename__ = "articles"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    title = Column(String(300), nullable=False)
    category = Column(String(50), default="news")
    brand = Column(String(50), default="塔塔")
    summary = Column(Text)
    content = Column(Text)
    cover_image = Column(String(500))
    video_url = Column(String(500))
    video_channel_url = Column(String(500))
    author = Column(String(100))
    tags = Column(String(300))
    status = Column(String(20), default="draft")
    sort_order = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

# ══════════════════ Schemas ══════════════════
class ArticleCreate(BaseModel):
    title: str
    category: Optional[str] = "news"
    brand: Optional[str] = "塔塔"
    summary: Optional[str] = None
    content: Optional[str] = None
    cover_image: Optional[str] = None
    video_url: Optional[str] = None
    video_channel_url: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[str] = None
    status: Optional[str] = "draft"
    sort_order: Optional[int] = 0

# ══════════════════ 小程序端 API ══════════════════
router = APIRouter(prefix="/api/v1/articles", tags=["articles"])

@router.get("")
def list_articles(
    category: Optional[str] = None,
    brand: Optional[str] = None,
    limit: int = Query(20, le=50),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """小程序端：获取已发布的内容列表"""
    q = db.query(Article).filter(Article.status == "published")
    if category:
        # promo映射member_story(兼容CRM端分类名)
        cat_alias = {"promo": ["promo", "member_story"], "member_story": ["promo", "member_story"]}
        if category in cat_alias:
            q = q.filter(Article.category.in_(cat_alias[category]))
        else:
            q = q.filter(Article.category == category)
    if brand:
        q = q.filter(Article.brand == brand)
    total = q.count()
    items = q.order_by(Article.sort_order.desc(), Article.published_at.desc()).offset(offset).limit(limit).all()
    return {
        "code": 0,
        "data": [{
            "id": a.id, "title": a.title, "category": a.category,
            "brand": a.brand, "summary": a.summary,
            "cover_image": a.cover_image,
            "video_url": a.video_url,
            "video_channel_url": a.video_channel_url,
            "author": a.author, "tags": a.tags,
            "view_count": a.view_count,
            "published_at": a.published_at.isoformat() if a.published_at else None,
        } for a in items],
        "total": total
    }

@router.get("/{article_id}")
def get_article(article_id: int, db: Session = Depends(get_db)):
    """小程序端：获取内容详情（浏览量+1）"""
    a = db.query(Article).filter(Article.id == article_id, Article.status == "published").first()
    if not a:
        raise HTTPException(404, "内容不存在")
    a.view_count = (a.view_count or 0) + 1
    db.commit()
    return {
        "code": 0,
        "data": {
            "id": a.id, "title": a.title, "category": a.category,
            "brand": a.brand, "summary": a.summary, "content": a.content,
            "cover_image": a.cover_image,
            "video_url": a.video_url,
            "video_channel_url": a.video_channel_url,
            "author": a.author, "tags": a.tags,
            "view_count": a.view_count,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
    }

# ══════════════════ 管理端 API ══════════════════
admin_router = APIRouter(prefix="/admin/articles", tags=["articles-admin"], dependencies=[Depends(get_current_admin)])

CATEGORY_MAP = {
    "culture": "企业文化",
    "news": "行业动态",
    "promo": "品牌宣传",
    "video": "视频号",
    "course_review": "课程回顾",
}

@admin_router.get("")
def admin_list_articles(
    category: Optional[str] = None,
    status: Optional[str] = None,
    brand: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    query = db.query(Article)
    if category:
        query = query.filter(Article.category == category)
    if status:
        query = query.filter(Article.status == status)
    if brand:
        query = query.filter(Article.brand == brand)
    if q:
        query = query.filter(Article.title.ilike(f"%{q}%"))
    total = query.count()
    items = query.order_by(Article.sort_order.desc(), Article.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "code": 0,
        "data": [{
            "id": a.id, "title": a.title, "category": a.category,
            "category_label": CATEGORY_MAP.get(a.category, a.category),
            "brand": a.brand, "summary": a.summary,
            "cover_image": a.cover_image,
            "video_url": a.video_url,
            "video_channel_url": a.video_channel_url,
            "author": a.author, "tags": a.tags,
            "status": a.status, "sort_order": a.sort_order,
            "view_count": a.view_count,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        } for a in items],
        "total": total
    }

@admin_router.post("")
def admin_create_article(body: ArticleCreate, db: Session = Depends(get_db)):
    a = Article(**body.dict())
    if body.status == "published":
        a.published_at = datetime.now()
    db.add(a)
    db.commit()
    db.refresh(a)
    return {"code": 0, "msg": "内容创建成功", "data": {"id": a.id}}

@admin_router.put("/{article_id}")
def admin_update_article(article_id: int, body: ArticleCreate, db: Session = Depends(get_db)):
    a = db.query(Article).filter(Article.id == article_id).first()
    if not a:
        raise HTTPException(404, "内容不存在")
    for k, v in body.dict(exclude_unset=True).items():
        setattr(a, k, v)
    a.updated_at = datetime.now()
    db.commit()
    return {"code": 0, "msg": "内容已更新"}

@admin_router.put("/{article_id}/publish")
def admin_publish_article(article_id: int, db: Session = Depends(get_db)):
    a = db.query(Article).filter(Article.id == article_id).first()
    if not a:
        raise HTTPException(404, "内容不存在")
    a.status = "published"
    a.published_at = datetime.now()
    a.updated_at = datetime.now()
    db.commit()
    return {"code": 0, "msg": "内容已发布"}

@admin_router.put("/{article_id}/unpublish")
def admin_unpublish_article(article_id: int, db: Session = Depends(get_db)):
    a = db.query(Article).filter(Article.id == article_id).first()
    if not a:
        raise HTTPException(404, "内容不存在")
    a.status = "draft"
    a.updated_at = datetime.now()
    db.commit()
    return {"code": 0, "msg": "内容已下架"}

@admin_router.delete("/{article_id}")
def admin_delete_article(article_id: int, db: Session = Depends(get_db)):
    a = db.query(Article).filter(Article.id == article_id).first()
    if not a:
        raise HTTPException(404, "内容不存在")
    db.delete(a)
    db.commit()
    return {"code": 0, "msg": "内容已删除"}
