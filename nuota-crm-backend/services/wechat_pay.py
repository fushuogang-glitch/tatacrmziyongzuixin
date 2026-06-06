"""微信支付 - 服务商模式 JSAPI"""
import json, time, logging, hashlib, hmac, base64, secrets
from datetime import datetime
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.hashes import SHA256
import requests as http_req

from config import settings

logger = logging.getLogger('wechat_pay')

# ---- 子商户配置 ----
SUB_MCH_ID   = settings.WXPAY_SUB_MCH_ID
SUB_APPID     = settings.WXPAY_SUB_APPID
APIV3_KEY     = settings.WXPAY_APIV3_KEY
CERT_SERIAL   = settings.WXPAY_CERT_SERIAL
CERT_DIR      = settings.WXPAY_CERT_DIR
NOTIFY_URL    = settings.WXPAY_NOTIFY_URL

# 服务商信息
SP_MCH_ID     = settings.WXPAY_SP_MCH_ID
SP_APPID      = settings.WXPAY_SP_APPID  # 服务商appid，如果没有用空串

_private_key = None

def _require_config(*names: str) -> None:
    missing = [name for name in names if not globals().get(name)]
    if missing:
        raise RuntimeError(f"微信支付配置缺失: {', '.join(missing)}")

def _get_private_key():
    _require_config('CERT_DIR')
    global _private_key
    if _private_key is None:
        with open(f'{CERT_DIR}/apiclient_key.pem', 'rb') as f:
            _private_key = load_pem_private_key(f.read(), password=None)
    return _private_key


def _sign(message: str) -> str:
    """RSA-SHA256签名"""
    key = _get_private_key()
    signature = key.sign(message.encode('utf-8'), PKCS1v15(), SHA256())
    return base64.b64encode(signature).decode('utf-8')


def _build_auth_header(method: str, url_path: str, body: str = '') -> str:
    """构建Authorization头"""
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    message = f'{method}\n{url_path}\n{timestamp}\n{nonce}\n{body}\n'
    signature = _sign(message)
    return (
        f'WECHATPAY2-SHA256-RSA2048 '
        f'mchid="{SUB_MCH_ID}",'
        f'nonce_str="{nonce}",'
        f'signature="{signature}",'
        f'timestamp="{timestamp}",'
        f'serial_no="{CERT_SERIAL}"'
    )


def create_jsapi_order(openid: str, out_trade_no: str, total_fee: int, description: str) -> dict:
    """
    JSAPI下单（子商户自己下单模式）
    文档：https://pay.weixin.qq.com/doc/v3/merchant/4012791858
    """
    _require_config('SUB_MCH_ID', 'SUB_APPID', 'CERT_SERIAL', 'CERT_DIR', 'NOTIFY_URL')
    url_path = '/v3/pay/transactions/jsapi'
    url = f'https://api.mch.weixin.qq.com{url_path}'

    body_dict = {
        'appid': SUB_APPID,
        'mchid': SUB_MCH_ID,
        'description': description,
        'out_trade_no': out_trade_no,
        'notify_url': NOTIFY_URL,
        'amount': {'total': total_fee, 'currency': 'CNY'},
        'payer': {'openid': openid},
    }
    body_str = json.dumps(body_dict, ensure_ascii=False)

    auth = _build_auth_header('POST', url_path, body_str)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': auth,
    }

    resp = http_req.post(url, data=body_str.encode('utf-8'), headers=headers, timeout=10)
    logger.info(f'create order {out_trade_no}: status={resp.status_code}, body={resp.text[:300]}')

    if resp.status_code == 200:
        result = resp.json()
        prepay_id = result.get('prepay_id', '')
        # 构造前端调起支付的参数
        ts = str(int(time.time()))
        nonce = secrets.token_hex(16)
        package = f'prepay_id={prepay_id}'
        sign_msg = f'{SUB_APPID}\n{ts}\n{nonce}\n{package}\n'
        pay_sign = _sign(sign_msg)
        return {
            'timeStamp': ts,
            'nonceStr': nonce,
            'package': package,
            'signType': 'RSA',
            'paySign': pay_sign,
        }
    else:
        raise Exception(f'微信支付下单失败: code={resp.status_code}, msg={resp.text[:500]}')


def decrypt_notify(headers: dict, body: str) -> dict:
    """解密支付回调通知（APIv3 AEAD_AES_256_GCM）"""
    _require_config('APIV3_KEY')
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    data = json.loads(body)
    resource = data.get('resource', {})
    ciphertext = base64.b64decode(resource['ciphertext'])
    nonce = resource['nonce'].encode('utf-8')
    aad = resource.get('associated_data', '').encode('utf-8')
    key = APIV3_KEY.encode('utf-8')
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
    return json.loads(plaintext.decode('utf-8'))
