"""通用文件上传路由"""
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from config import settings
from utils.helpers import ok
from utils.auth import get_admin_or_agent

router = APIRouter(prefix="/admin/upload", tags=["upload"])

UPLOAD_DIR = settings.UPLOAD_DIR
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/image")
async def upload_image(file: UploadFile = File(...), _=Depends(get_admin_or_agent)):
    """上传图片，返回URL"""
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, "仅支持 jpg/png/webp/gif 图片")
    original_ext = os.path.splitext(file.filename or "")[1].lower()
    ext = ALLOWED_IMAGE_TYPES[content_type]
    if original_ext and original_ext not in set(ALLOWED_IMAGE_TYPES.values()) | {".jpeg"}:
        raise HTTPException(400, "文件扩展名不支持")
    fname = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}{ext}"
    path = os.path.join(UPLOAD_DIR, fname)
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(413, "文件超过大小限制")
    with open(path, 'wb') as f:
        f.write(content)
    url = f"/static/uploads/{fname}"
    return ok({"url": url, "filename": fname})
