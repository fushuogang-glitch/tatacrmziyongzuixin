"""
每日补款提醒任务
运行方式：
  python3 -m tasks.debt_reminder
或通过 crontab 每天早9点执行：
  0 9 * * * cd /www/nuota-crm && source venv/bin/activate && python3 -m tasks.debt_reminder
"""
from datetime import date, timedelta
from loguru import logger

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.member import Payment, Member
from models.booking import Consultant
from services.notify_service import send_wecom


def run():
    db = SessionLocal()
    today = date.today()
    tomorrow = today + timedelta(days=1)

    try:
        # 查出 due_date 在 今天/明天、debt_amount>0、尚未提醒 的记录
        pending = (
            db.query(Payment)
            .filter(
                Payment.debt_amount > 0,
                Payment.due_date.isnot(None),
                Payment.due_date <= tomorrow,
                Payment.due_notified == False,
                Payment.pay_status.in_(["partial", "pending"]),
            )
            .all()
        )

        if not pending:
            logger.info(f"[debt_reminder] {today} 无待追款记录")
            return

        for p in pending:
            member = db.query(Member).filter(Member.id == p.member_id).first()
            consultant = db.query(Consultant).filter(Consultant.id == p.consultant_id).first() if p.consultant_id else None

            member_name = member.name if member else f"学员#{p.member_id}"
            member_phone = member.phone if member else ""
            due_str = p.due_date.strftime("%Y年%m月%d日")
            debt_str = f"¥{float(p.debt_amount):,.0f}"
            consultant_phone = consultant.phone if consultant else None

            if p.due_date <= today:
                urgency = "🔴【今日到期】"
            else:
                urgency = "🟡【明日到期】"

            msg = (
                f"{urgency} 补款提醒\n"
                f"学员：{member_name}（{member_phone}）\n"
                f"欠款金额：{debt_str}\n"
                f"补款截止：{due_str}\n"
                f"负责老师：{consultant.name if consultant else '待分配'}\n"
                f"请及时跟进收款 🙏"
            )

            mentioned = []
            if consultant_phone:
                mentioned.append(consultant_phone)
            if member_phone:
                mentioned.append(member_phone)

            sent = send_wecom(msg, mentioned_mobiles=mentioned)
            if sent:
                p.due_notified = True
                logger.info(f"[debt_reminder] 已提醒 {member_name} 欠款 {debt_str}，截止 {due_str}")
            else:
                logger.warning(f"[debt_reminder] 发送失败 payment_id={p.id}")

        db.commit()
        logger.info(f"[debt_reminder] 共处理 {len(pending)} 条追款提醒")

    except Exception as e:
        logger.error(f"[debt_reminder] 异常: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    run()
