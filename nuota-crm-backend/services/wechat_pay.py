"""微信支付 JSAPI 服务模块"""
import json, time, logging
from wechatpayv3 import WeChatPay, WeChatPayType

logger = logging.getLogger('wechat_pay')

# ---- 配置 ----
MCH_ID = '1718951748'
APPID  = 'wxf6a6e4ce11b11dd8'
APIV3_KEY = 'TaTa2026WxPaySecretKeyAB12345678'
CERT_SERIAL = '5A94F342ADA2DDB0E3C5BBFC6F905756A85C7B47'
CERT_DIR = '/www/nuota-crm/certs'
NOTIFY_URL = 'https://tata-cn.com/api/v1/pay/notify'

_pay = None

def get_pay() -> WeChatPay:
    global _pay
    if _pay is None:
        with open(f'{CERT_DIR}/apiclient_key.pem') as f:
            private_key = f.read()
        with open(f'{CERT_DIR}/apiclient_cert.pem') as f:
            cert = f.read()
        _pay = WeChatPay(
            wechatpay_type=WeChatPayType.JSAPI,
            mchid=MCH_ID,
            private_key=private_key,
            cert_serial_no=CERT_SERIAL,
            appid=APPID,
            apiv3_key=APIV3_KEY,
            cert_dir=CERT_DIR,
            notify_url=NOTIFY_URL,
        )
    return _pay


def create_jsapi_order(openid: str, out_trade_no: str, total_fee: int, description: str) -> dict:
    """
    创建JSAPI预付单
    :param openid: 用户的微信openid
    :param out_trade_no: 商户订单号
    :param total_fee: 金额（分）
    :param description: 商品描述
    :return: prepay_id 等信息给前端调 wx.requestPayment
    """
    pay = get_pay()
    code, message = pay.pay(
        description=description,
        out_trade_no=out_trade_no,
        notify_url=NOTIFY_URL,
        amount={'total': total_fee, 'currency': 'CNY'},
        payer={'openid': openid},
    )
    logger.info(f'create order {out_trade_no}: code={code}, msg={message}')
    if code == 200:
        result = json.loads(message)
        prepay_id = result.get('prepay_id', '')
        # 生成前端调起支付的参数
        pay_params = pay.sign([APPID, str(int(time.time())), prepay_id])
        return {
            'prepay_id': prepay_id,
            'timeStamp': str(int(time.time())),
            'nonceStr': pay_params.get('nonceStr', ''),
            'package': f'prepay_id={prepay_id}',
            'signType': 'RSA',
            'paySign': pay_params.get('paySign', ''),
        }
    else:
        raise Exception(f'微信支付下单失败: code={code}, msg={message}')


def decrypt_notify(headers: dict, body: str) -> dict:
    """解密微信支付回调通知"""
    pay = get_pay()
    result = pay.callback(headers, body)
    if result:
        return json.loads(result)
    raise Exception('回调验签失败')
