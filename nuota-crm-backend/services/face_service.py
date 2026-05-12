# 腾讯云人脸核身封装（占位实现）
# 生产环境替换为腾讯云 FaceID / iai SDK 调用
import hashlib
from typing import Optional, Dict, Any

from config import settings


class FaceService:
    """人脸服务：封装腾讯云 FaceID / iai 接口。

    当前为 mock 实现（用手机号/base64 长度推算 face_token，方便联调），
    生产上替换 bind/verify 两个方法内部即可。
    """

    def __init__(self) -> None:
        self.secret_id = settings.TENCENT_SECRET_ID
        self.secret_key = settings.TENCENT_SECRET_KEY
        self.group = settings.TENCENT_FACE_GROUP
        self.region = settings.TENCENT_REGION

    def is_mock(self) -> bool:
        return self.secret_id.startswith("CONFIG.")

    def bind(self, member_id: int, face_base64: str) -> Dict[str, Any]:
        """绑定人脸。返回 {face_token, msg}。"""
        if not face_base64:
            return {"ok": False, "msg": "人脸数据为空"}
        if self.is_mock():
            digest = hashlib.sha256(f"{member_id}:{face_base64[:64]}".encode()).hexdigest()
            return {"ok": True, "face_token": f"mock_{digest[:32]}", "msg": "mock 绑定成功"}
        # TODO: 调用腾讯云 iai.CreatePerson / CreateFace
        raise NotImplementedError("请接入腾讯云 iai CreatePerson/CreateFace")

    def verify(self, face_token: Optional[str], face_base64: str, threshold: float = 80.0) -> Dict[str, Any]:
        """人脸比对。返回 {ok, score, msg}。"""
        if not face_base64:
            return {"ok": False, "score": 0, "msg": "人脸数据为空"}
        if not face_token:
            return {"ok": False, "score": 0, "msg": "未绑定人脸"}
        if self.is_mock():
            # 简单 mock：长度 > 100 视作通过，用于联调
            score = 92.5 if len(face_base64) > 100 else 60.0
            return {
                "ok": score >= threshold,
                "score": score,
                "msg": "mock 识别成功" if score >= threshold else "人脸相似度不足",
            }
        # TODO: 调用腾讯云 iai.VerifyFace / CompareFace
        raise NotImplementedError("请接入腾讯云 iai VerifyFace/SearchPersons")


face_service = FaceService()
