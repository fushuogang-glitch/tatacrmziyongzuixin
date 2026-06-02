content = open('/www/nuota-crm/routers/branches.py', 'r').read()

# 找到router定义，在后面加公开接口
insert_code = '''

# 公开接口（注册页用，不需要token）
@router.get("/public")
def public_branches(db: Session = Depends(get_db)):
    """公开分公司列表（仅名称，注册时选择用）"""
    from models.branch import Branch
    items = db.query(Branch).filter(Branch.status == "active").order_by(Branch.id).all()
    return ok([{"id": b.id, "name": b.name, "short_name": b.short_name, "city": b.city} for b in items])

'''

# 在第一个 @router 之前插入
import re
match = re.search(r'(@router\.(get|post|put|delete)\()', content)
if match:
    pos = match.start()
    content = content[:pos] + insert_code + content[pos:]
    open('/www/nuota-crm/routers/branches.py', 'w').write(content)
    print("done - public branches endpoint added")
else:
    print("could not find insertion point")
