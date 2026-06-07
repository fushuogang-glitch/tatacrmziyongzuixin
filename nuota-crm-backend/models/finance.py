"""财务管理 v2.2 — 分公司固定成本 + 盈亏平衡参数
按分公司(branch)组织，配合 purchases(采购) + payments(收费) + salary_records(工资)
实现按月独立记账 + 盈亏平衡点核算
"""
from sqlalchemy import (
    Column, Integer, String, Numeric, DateTime, ForeignKey, Text, func, UniqueConstraint
)
from database import Base


class BranchFixedCost(Base):
    """分公司固定成本 branch_fixed_costs
    周期性固定支出：房租/水电/折旧/保险等（员工底薪从 salary_records 单独取）
    """
    __tablename__ = "branch_fixed_costs"
    __table_args__ = (
        UniqueConstraint("branch_id", "cost_month", "category", "item", name="uq_fixed_cost"),
    )

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, index=True)
    cost_month = Column(String(7), nullable=False, index=True)   # YYYY-MM
    category = Column(String(30), default="other_fixed")          # rent/utility/depreciation/insurance/other_fixed
    item = Column(String(200), nullable=False)                    # 科目名称（门店房租/水电费…）
    amount = Column(Numeric(12, 2), nullable=False, default=0)
    remark = Column(Text)
    created_by = Column(Integer, ForeignKey("admin_users.id"))
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class BranchBreakevenConfig(Base):
    """分公司盈亏平衡参数 branch_breakeven_config"""
    __tablename__ = "branch_breakeven_config"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False, unique=True, index=True)
    commission_rate = Column(Numeric(5, 4), default=0.05)         # 提成率（占销售额）
    variable_extra_rate = Column(Numeric(5, 4), default=0)        # 其他变动成本率
    default_variable_rate = Column(Numeric(5, 4), default=0.35)   # 收入为0时回退的变动成本率
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
