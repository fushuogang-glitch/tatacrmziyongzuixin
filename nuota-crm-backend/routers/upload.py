"""通用文件上传路由"""
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends
from utils.helpers import ok
from utils.auth import get_current_admin

router = APIRouter(prefix="/admin/upload", tags=["upload"])

UPLOAD_DIR = "/www/nuota-crm/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/image")
async def upload_image(file: UploadFile = File(...), _=Depends(get_current_admin)):
    """上传图片，返回URL"""
    ext = os.path.splitext(file.filename or 'img.png')[1] or '.png'
    fname = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}{ext}"
    path = os.path.join(UPLOAD_DIR, fname)
    content = await file.read()
    with open(path, 'wb') as f:
        f.write(content)
    url = f"/static/uploads/{fname}"
    return ok({"url": url, "filename": fname})
