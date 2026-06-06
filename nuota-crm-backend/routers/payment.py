"""微信支付路由"""
import uuid, logging
from datetime import datetime
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models.member import Member
from models.course_session import CourseSession, CourseEnrollment
from services.wechat_pay import SUB_APPID, SUB_MCH_ID, create_jsapi_order, decrypt_notify
from routers.members import get_current_member

logger = logging.getLogger('payment')
router = APIRouter(prefix='/api/v1/pay', tags=['微信支付'])


def ok(data=None, msg='ok'):
    return {'code': 0, 'msg': msg, 'data': data}


class PayOrderCreate(BaseModel):
    enrollment_id: int
    price_type: Optional[str] = 'trial'


@router.post('/create-order')
def create_order(
    body: PayOrderCreate,
    db: DBSession = Depends(get_db),
    current: Member = Depends(get_current_member),
):
    """小程序端发起微信支付"""
    enroll = db.query(CourseEnrollment).filter(
        CourseEnrollment.id == body.enrollment_id,
        CourseEnrollment.member_id == current.id,
    ).first()
    if not enroll:
        raise HTTPException(404, '报名记录不存在')

    cs = db.query(CourseSession).filter(CourseSession.id == enroll.session_id).first()
    if not cs:
        raise HTTPException(404, '场次不存在')

    if body.price_type == 'normal':
        amount_yuan = float(cs.normal_price or 0)
    else:
        amount_yuan = float(cs.trial_price or 0)
    amount_fen = int(amount_yuan * 100)
    if amount_fen <= 0:
        raise HTTPException(400, '金额异常')

    openid = getattr(current, 'wx_openid', None) or getattr(current, 'openid', None)
    if not openid:
        raise HTTPException(400, '未获取到微信openid，请重新登录')

    out_trade_no = f'TATA{datetime.now().strftime("%Y%m%d%H%M%S")}{uuid.uuid4().hex[:8].upper()}'
    enroll.out_trade_no = out_trade_no
    enroll.paid_amount = amount_yuan
    db.commit()

    try:
        pay_params = create_jsapi_order(
            openid=openid,
            out_trade_no=out_trade_no,
            total_fee=amount_fen,
            description=f'塔塔战略课-{cs.title}',
        )
        return ok(pay_params)
    except Exception as ex:
        logger.error(f'create order failed: {ex}')
        raise HTTPException(500, f'支付下单失败: {ex}')


@router.post('/notify')
async def pay_notify(request: Request, db: DBSession = Depends(get_db)):
    """微信支付异步通知回调"""
    body = await request.body()
    headers = {
        'Wechatpay-Signature': request.headers.get('Wechatpay-Signature', ''),
        'Wechatpay-Timestamp': request.headers.get('Wechatpay-Timestamp', ''),
        'Wechatpay-Nonce': request.headers.get('Wechatpay-Nonce', ''),
        'Wechatpay-Serial': request.headers.get('Wechatpay-Serial', ''),
    }

    try:
        result = decrypt_notify(headers, body.decode('utf-8'))
    except Exception as ex:
        logger.error(f'notify decrypt failed: {ex}')
        return JSONResponse({'code': 'FAIL', 'message': str(ex)}, status_code=400)

    out_trade_no = result.get('out_trade_no', '')
    trade_state = result.get('trade_state', '')
    logger.info(f'pay notify: order={out_trade_no}, state={trade_state}')

    if trade_state == 'SUCCESS':
        enroll = db.query(CourseEnrollment).filter(
            CourseEnrollment.out_trade_no == out_trade_no
        ).first()
        if enroll:
            amount = result.get('amount') or {}
            paid_fen = int(float(enroll.paid_amount or 0) * 100)
            notify_fen = int(amount.get('total') or 0)
            if SUB_MCH_ID and result.get('mchid') not in (SUB_MCH_ID, None):
                logger.warning(f'pay notify mchid mismatch: order={out_trade_no}')
                return JSONResponse({'code': 'FAIL', 'message': '商户号不匹配'}, status_code=400)
            if SUB_APPID and result.get('appid') not in (SUB_APPID, None):
                logger.warning(f'pay notify appid mismatch: order={out_trade_no}')
                return JSONResponse({'code': 'FAIL', 'message': 'appid不匹配'}, status_code=400)
            if paid_fen != notify_fen:
                logger.warning(f'pay notify amount mismatch: order={out_trade_no}, expected={paid_fen}, actual={notify_fen}')
                return JSONResponse({'code': 'FAIL', 'message': '金额不匹配'}, status_code=400)
            if getattr(enroll, 'pay_status', None) == 'paid':
                return JSONResponse({'code': 'SUCCESS', 'message': '成功'})
            enroll.pay_status = 'paid'
            enroll.paid_at = datetime.now()
            enroll.transaction_id = result.get('transaction_id', '')
            db.commit()
            logger.info(f'enrollment {enroll.id} marked as paid')

            try:
                from models.webhook_event import emit_event
                member = db.query(Member).filter(Member.id == enroll.member_id).first()
                emit_event(db, 'payment.completed', {
                    'enrollment_id': enroll.id,
                    'member_name': member.name if member else '',
                    'amount': float(result.get('amount', {}).get('total', 0)) / 100,
                    'out_trade_no': out_trade_no,
                    'transaction_id': result.get('transaction_id', ''),
                })
            except Exception as ex:
                logger.warning(f'emit payment event failed: {ex}')

    return JSONResponse({'code': 'SUCCESS', 'message': '成功'})


@router.get('/status/{enrollment_id}')
def pay_status(
    enrollment_id: int,
    db: DBSession = Depends(get_db),
    current: Member = Depends(get_current_member),
):
    enroll = db.query(CourseEnrollment).filter(
        CourseEnrollment.id == enrollment_id,
        CourseEnrollment.member_id == current.id,
    ).first()
    if not enroll:
        raise HTTPException(404, '记录不存在')
    return ok({
        'pay_status': getattr(enroll, 'pay_status', 'unpaid'),
        'out_trade_no': getattr(enroll, 'out_trade_no', ''),
    })
