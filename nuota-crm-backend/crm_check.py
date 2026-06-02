from database import SessionLocal
from sqlalchemy import text
db = SessionLocal()

print('=== 服务列表 ===')
rows = db.execute(text("SELECT id, name, category FROM services ORDER BY id")).fetchall()
for r in rows:
    print(r)

print('\n=== 课程 ===')
rows = db.execute(text("SELECT id, title, status FROM courses ORDER BY id")).fetchall()
for r in rows:
    print(r)

print('\n=== 课程场次 ===')
rows = db.execute(text("SELECT id, course_id, title, start_date, end_date, status FROM course_sessions ORDER BY id")).fetchall()
for r in rows:
    print(r)

print('\n=== 会员 ===')
rows = db.execute(text("SELECT id, name, phone, member_tier FROM members ORDER BY id")).fetchall()
for r in rows:
    print(r)

print('\n=== 老师 ===')
rows = db.execute(text("SELECT id, name, phone, status FROM consultants ORDER BY id")).fetchall()
for r in rows:
    print(r)

print('\n=== 现有工单 ===')
rows = db.execute(text("SELECT id, order_no, member_id, service_id, consultant_id, status FROM service_orders ORDER BY id")).fetchall()
for r in rows:
    print(r)

db.close()
