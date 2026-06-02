"""微信支付 - 服务商模式 JSAPI"""
import json, time, logging, hashlib, hmac, base64, secrets
from datetime import datetime
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
from cryptography.hazmat.primitives.hashes import SHA256
import requests as http_req

logger = logging.getLogger('wechat_pay')

# ---- 子商户配置 ----
SUB_MCH_ID   = '1718951748'
SUB_APPID     = 'wxf6a6e4ce11b11dd8'
APIV3_KEY     = 'TaTa2026WxPaySecretKeyAB12345678'
CERT_SERIAL   = '5A94F342ADA2DDB0E3C5BBFC6F905756A85C7B47'
CERT_DIR      = '/www/nuota-crm/certs'
NOTIFY_URL    = 'https://crm.tata-cn.com/api/v1/pay/notify'

# 服务商信息
SP_MCH_ID     = '1800009908'
SP_APPID      = ''  # 服务商appid，如果没有用空串

_private_key = None

def _get_private_key():
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
