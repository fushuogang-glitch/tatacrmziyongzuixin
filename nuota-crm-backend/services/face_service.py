# 腾讯云人脸识别（iai）完整接入
# 接口文档：https://cloud.tencent.com/document/product/867
import hashlib
import json
import logging
from typing import Optional, Dict, Any

from config import settings

logger = logging.getLogger(__name__)


class FaceService:
    """腾讯云人脸识别服务封装

    使用接口：
    - CreateGroup      : 初始化人员库
    - CreatePerson     : 会员注册时录脸
    - SearchPersons    : 签到时 1:N 搜索（不需要知道是谁，拍脸返回 member_id）
    - DeletePerson     : 解绑人脸（管理员操作）
    """

    def __init__(self) -> None:
        self.secret_id  = settings.TENCENT_SECRET_ID
        self.secret_key = settings.TENCENT_SECRET_KEY
        self.group_id   = settings.TENCENT_FACE_GROUP   # nuota_tata_members
        self.region     = settings.TENCENT_REGION       # ap-guangzhou
        self._client    = None

    def is_mock(self) -> bool:
        """未配置真实密钥时走 mock 分支"""
        return (
            not self.secret_id
            or self.secret_id.startswith("CONFIG.")
            or self.secret_id == "YOUR_SECRET_ID"
        )

    def _get_client(self):
        """懒加载腾讯云 iai 客户端"""
        if self._client is None:
            from tencentcloud.common import credential
            from tencentcloud.common.profile.client_profile import ClientProfile
            from tencentcloud.common.profile.http_profile import HttpProfile
            from tencentcloud.iai.v20200303 import iai_client

            cred = credential.Credential(self.secret_id, self.secret_key)
            hp = HttpProfile()
            hp.endpoint = "iai.tencentcloudapi.com"
            cp = ClientProfile()
            cp.httpProfile = hp
            self._client = iai_client.IaiClient(cred, self.region, cp)
        return self._client

    # ─────────────────────────────────────────────────────────
    # 初始化人员库（首次部署时调用一次即可）
    # ─────────────────────────────────────────────────────────
    def ensure_group(self) -> Dict[str, Any]:
        """确保人员库存在，幂等操作"""
        if self.is_mock():
            return {"ok": True, "msg": "mock 模式，跳过人员库初始化"}
        try:
            from tencentcloud.iai.v20200303 import models as iai_models
            client = self._get_client()

            # 先查是否存在
            req_list = iai_models.GetGroupListRequest()
            req_list.Limit  = 100
            req_list.Offset = 0
            resp_list = client.GetGroupList(req_list)
            groups = resp_list.GroupInfos or []
            exists = any(g.GroupId == self.group_id for g in groups)

            if not exists:
                req_create = iai_models.CreateGroupRequest()
                req_create.GroupName = "诺控塔塔会员库"
                req_create.GroupId   = self.group_id
                req_create.GroupExDescriptions = ["nuota_tata_crm"]
                client.CreateGroup(req_create)
                logger.info(f"人员库已创建：{self.group_id}")
            return {"ok": True, "msg": "人员库就绪"}
        except Exception as e:
            logger.error(f"ensure_group 失败：{e}")
            return {"ok": False, "msg": str(e)}

    # ─────────────────────────────────────────────────────────
    # 会员注册：录入人脸
    # ─────────────────────────────────────────────────────────
    def bind(self, member_id: int, face_base64: str) -> Dict[str, Any]:
        """
        将会员人脸录入腾讯云人员库。
        PersonId 使用 member_{member_id}，方便搜索结果直接解析出 member_id。
        """
        if not face_base64:
            return {"ok": False, "msg": "人脸图片数据为空"}

        if self.is_mock():
            digest = hashlib.sha256(f"{member_id}:{face_base64[:64]}".encode()).hexdigest()
            return {
                "ok": True,
                "face_token": f"mock_{digest[:32]}",
                "msg": "【测试模式】人脸绑定成功（未连接腾讯云）",
            }

        try:
            from tencentcloud.iai.v20200303 import models as iai_models
            client = self._get_client()

            person_id = f"member_{member_id}"

            # 先尝试删除旧记录（重绑场景）
            try:
                req_del = iai_models.DeletePersonRequest()
                req_del.PersonId = person_id
                client.DeletePerson(req_del)
            except Exception:
                pass  # 不存在则忽略

            # 创建人员并上传人脸
            req = iai_models.CreatePersonRequest()
            req.GroupId    = self.group_id
            req.PersonName = f"会员{member_id}"
            req.PersonId   = person_id
            req.Image      = face_base64   # base64 字符串（不含 data: 头）
            req.UniquePersonControl = 1    # 同一人只能在库中出现一次

            resp = client.CreatePerson(req)
            face_id = resp.FaceId

            logger.info(f"人脸绑定成功：member_id={member_id}, face_id={face_id}")
            return {
                "ok": True,
                "face_token": face_id,
                "person_id": person_id,
                "msg": "人脸绑定成功",
            }

        except Exception as e:
            logger.error(f"人脸绑定失败：member_id={member_id}, error={e}")
            # 解析腾讯云错误码
            err_msg = _parse_tencent_error(e)
            return {"ok": False, "msg": err_msg}

    # ─────────────────────────────────────────────────────────
    # 签到搜索：1:N 人脸搜索 → 返回 member_id
    # ─────────────────────────────────────────────────────────
    def search(self, face_base64: str, threshold: float = 80.0) -> Dict[str, Any]:
        """
        签到时调用：上传一张人脸图片，在人员库中搜索。
        返回 { ok, member_id, score, msg }
        """
        if not face_base64:
            return {"ok": False, "member_id": None, "score": 0, "msg": "人脸图片为空"}

        if self.is_mock():
            # mock：base64 长度 > 100 视为成功，返回固定 member_id=1
            score = 93.5 if len(face_base64) > 100 else 55.0
            if score >= threshold:
                return {"ok": True, "member_id": 1, "score": score, "msg": "【测试模式】识别成功"}
            return {"ok": False, "member_id": None, "score": score, "msg": "【测试模式】未识别到人脸"}

        try:
            from tencentcloud.iai.v20200303 import models as iai_models
            client = self._get_client()

            req = iai_models.SearchPersonsRequest()
            req.GroupIds      = [self.group_id]
            req.Image         = face_base64
            req.MaxFaceNum    = 1          # 只搜索图片中最大的人脸
            req.MinFaceSize   = 40         # 最小人脸像素
            req.MaxPersonNum  = 1          # 只返回最相似的一个人

            resp = client.SearchPersons(req)

            results = resp.Results or []
            if not results or not results[0].Candidates:
                return {"ok": False, "member_id": None, "score": 0, "msg": "未识别到人脸"}

            best = results[0].Candidates[0]
            score     = best.Score
            person_id = best.PersonId  # 格式：member_{member_id}

            if score < threshold:
                return {
                    "ok": False,
                    "member_id": None,
                    "score": score,
                    "msg": f"人脸相似度不足（{score:.1f} < {threshold}）",
                }

            # 从 person_id 解析出 member_id
            member_id = int(person_id.replace("member_", ""))
            logger.info(f"人脸签到成功：member_id={member_id}, score={score:.1f}")
            return {
                "ok": True,
                "member_id": member_id,
                "person_id": person_id,
                "score": score,
                "msg": "识别成功",
            }

        except Exception as e:
            logger.error(f"人脸搜索失败：{e}")
            err_msg = _parse_tencent_error(e)
            return {"ok": False, "member_id": None, "score": 0, "msg": err_msg}

    # ─────────────────────────────────────────────────────────
    # 验证：1:1 比对（用于购买时二次确认身份）
    # ─────────────────────────────────────────────────────────
    def verify(self, member_id: int, face_base64: str, threshold: float = 80.0) -> Dict[str, Any]:
        """
        已知 member_id，验证当前人脸是否与库中一致。
        用于：购买课程/专案时的二次人脸确认。
        """
        if not face_base64:
            return {"ok": False, "score": 0, "msg": "人脸图片为空"}

        if self.is_mock():
            score = 92.5 if len(face_base64) > 100 else 60.0
            return {
                "ok": score >= threshold,
                "score": score,
                "msg": "【测试模式】验证通过" if score >= threshold else "【测试模式】验证失败",
            }

        try:
            from tencentcloud.iai.v20200303 import models as iai_models
            client = self._get_client()

            req = iai_models.VerifyPersonRequest()
            req.PersonId = f"member_{member_id}"
            req.Image    = face_base64

            resp = client.VerifyPerson(req)
            score = resp.Score
            passed = score >= threshold

            logger.info(f"人脸验证：member_id={member_id}, score={score:.1f}, passed={passed}")
            return {
                "ok": passed,
                "score": score,
                "msg": "验证通过" if passed else f"人脸不匹配（相似度 {score:.1f}）",
            }

        except Exception as e:
            logger.error(f"人脸验证失败：member_id={member_id}, error={e}")
            err_msg = _parse_tencent_error(e)
            return {"ok": False, "score": 0, "msg": err_msg}

    # ─────────────────────────────────────────────────────────
    # 解绑人脸（管理员）
    # ─────────────────────────────────────────────────────────
    def unbind(self, member_id: int) -> Dict[str, Any]:
        if self.is_mock():
            return {"ok": True, "msg": "【测试模式】人脸已解绑"}
        try:
            from tencentcloud.iai.v20200303 import models as iai_models
            client = self._get_client()
            req = iai_models.DeletePersonRequest()
            req.PersonId = f"member_{member_id}"
            client.DeletePerson(req)
            return {"ok": True, "msg": "人脸已解绑"}
        except Exception as e:
            return {"ok": False, "msg": _parse_tencent_error(e)}


def _parse_tencent_error(e: Exception) -> str:
    """解析腾讯云 SDK 错误为可读中文"""
    msg = str(e)
    error_map = {
        "INVALIDPARAMETERVALUE_NOFACEDETECTED": "未检测到人脸，请正对摄像头重试",
        "INVALIDPARAMETERVALUE_NOFACEINGROUPS": "人脸库为空，请先录入学员人脸",
        "INVALIDPARAMETERVALUE_FACENOTEXIST":   "该会员尚未绑定人脸",
        "RESOURCEUNAVAILABLE_INARREARS":        "腾讯云账户欠费，请充值",
        "REQUESTLIMITEXCEEDED":                 "请求频率超限，请稍后重试",
        "INVALIDPARAMETERVALUE_INVALIDIMAGE":   "图片格式错误，请重新拍摄",
        "FAILEDOPERATION_IMAGEDECODEFAILED":    "图片解码失败，请检查图片质量",
        "FAILEDOPERATION_CONFLICTOPERATION":    "人员已存在，请先解绑再重新绑定",
        "AUTHFAILURE":                          "腾讯云密钥错误，请检查配置",
    }
    for code, zh in error_map.items():
        if code in msg:
            return zh
    return f"识别服务异常：{msg[:80]}"


# 单例
face_service = FaceService()
