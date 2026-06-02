"""广告位管理路由 v2 - 支持轮播+四宫格"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from utils.auth import get_current_admin, get_admin_or_agent
from utils.helpers import ok

router = APIRouter(prefix="/admin/banners", tags=["banners"])


@router.get("")
def list_banners(position: str = None, display_type: str = None,
                 db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    sql = "SELECT * FROM banners WHERE 1=1"
    params = {}
    if position:
        sql += " AND position = :pos"
        params["pos"] = position
    if display_type:
        sql += " AND display_type = :dt"
        params["dt"] = display_type
    sql += " ORDER BY sort_order, id"
    rows = db.execute(text(sql), params).mappings().all()
    return ok([dict(r) for r in rows])


@router.post("")
def create_banner(body: dict, db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    db.execute(text("""
        INSERT INTO banners (title, position, image_url, link_url, sort_order, is_active,
                             display_type, icon, subtitle, group_key)
        VALUES (:title, :position, :image_url, :link_url, :sort_order, true,
                :display_type, :icon, :subtitle, :group_key)
    """), {
        "title": body.get("title", ""),
        "position": body.get("position", "service_page"),
        "image_url": body.get("image_url", ""),
        "link_url": body.get("link_url", ""),
        "sort_order": body.get("sort_order", 0),
        "display_type": body.get("display_type", "carousel"),
        "icon": body.get("icon", ""),
        "subtitle": body.get("subtitle", ""),
        "group_key": body.get("group_key", ""),
    })
    db.commit()
    return ok({"msg": "已创建"})


@router.put("/{bid}")
def update_banner(bid: int, body: dict, db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    fields = ['title', 'position', 'image_url', 'link_url', 'sort_order', 'is_active',
              'display_type', 'icon', 'subtitle', 'group_key']
    sets, params = [], {"id": bid}
    for f in fields:
        if f in body:
            sets.append(f"{f} = :{f}")
            params[f] = body[f]
    if not sets:
        raise HTTPException(400, "无更新字段")
    sets.append("updated_at = NOW()")
    db.execute(text(f"UPDATE banners SET {', '.join(sets)} WHERE id = :id"), params)
    db.commit()
    return ok({"msg": "已更新"})


@router.delete("/{bid}")
def delete_banner(bid: int, db: Session = Depends(get_db), _=Depends(get_admin_or_agent)):
    db.execute(text("DELETE FROM banners WHERE id = :id"), {"id": bid})
    db.commit()
    return ok({"msg": "已删除"})


# 小程序公开接口（不需要登录）
@router.get("/public")
def public_banners(position: str = "service_page", db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT id, title, image_url, link_url, position, display_type, icon, subtitle, group_key
        FROM banners
        WHERE is_active = true AND position = :pos
        ORDER BY sort_order, id
    """), {"pos": position}).mappings().all()
    # 按display_type分组返回
    carousel = []
    grids = {}
    for r in rows:
        d = dict(r)
        if d.get("display_type") == "grid":
            gk = d.get("group_key") or "default"
            grids.setdefault(gk, []).append(d)
        else:
            carousel.append(d)
    return ok({
        "carousel": carousel,
        "grids": grids,
        "all": [dict(r) for r in rows],
    })
