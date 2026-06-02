"""采购管理模型 purchases - 2026-06-02"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text, Boolean, Date, func
from database import Base


class Purchase(Base):
    """采购/支出记录表 purchases
    
    业务范围：所有支出（物料/办公/差旅/外包/水电房租等全口径）
    录入权限：分公司管理员（自动绑定本分公司）+ 超管（可任意分公司）
    用途：财务系统拉数 → 进项发票/期间费用
    """
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)  # 所属分公司·必填
    
    # 核心字段（九哥定的 8 项）
    supplier = Column(String(200), nullable=False)              # 供应商
    purchase_date = Column(Date, nullable=False, index=True)    # 采购日期
    item = Column(String(500), nullable=False)                  # 产品/服务（描述）
    qty = Column(Numeric(10, 2), default=1)                     # 数量
    amount = Column(Numeric(12, 2), nullable=False)             # 采购金额（含税）
    tax_amount = Column(Numeric(12, 2), default=0)              # 税额
    invoice_no = Column(String(100))                            # 发票号
    
    # 扩展字段
    category = Column(String(50), default="other")              # material/office/travel/outsource/utility/rent/other
    pay_method = Column(String(20))                             # cash/wechat/alipay/public_account/private_account/bank
    has_invoice = Column(Boolean, default=False)                # 是否取得发票
    reimbursed = Column(Boolean, default=False)                 # 是否报销/已支付
    
    # 录入审计
    created_by = Column(Integer, ForeignKey("admin_users.id"))  # 谁录的
    remark = Column(Text)
    receipt_image = Column(String(500))                         # 发票/小票图片
    
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
