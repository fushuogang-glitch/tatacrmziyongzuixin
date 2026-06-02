# 模型统一导入点
from models.member import Member, Payment, PaymentService
from models.session import Session, Enrollment
from models.checkin import Checkin
from models.referral import Referral
from models.reward import VisitReward
from models.booking import Consultant, VisitBooking, ConsultantApplication, ConsultantInviteCode, ConsultantSchedule
from models.handbook import Handbook, AdminUser
from models.service import (
    Service, ServicePackage, ServiceOrder, ServiceWorkLog, UserAgreement
)
from models.followup import FollowUp
from models.branch import Branch
from models.enterprise import Enterprise, EnterpriseInvite
from models.consumption import PackageConsumption
from models.course_session import CourseSession, CourseEnrollment as CourseEnrollmentV2, CourseCheckin, CourseFollowup
from models.agent import AgentApiKey
from models.webhook_event import WebhookEvent
from models.purchase import Purchase
from models.recharge import Recharge, RechargeConsumption
from models.deep_analysis import MemberDeepAnalysis, ConsultantTalentAnalysis

__all__ = [
    "Member", "Payment", "PaymentService",
    "Session", "Enrollment",
    "Checkin",
    "Referral",
    "VisitReward",
    "Consultant", "VisitBooking", "ConsultantApplication", "ConsultantInviteCode", "ConsultantSchedule",
    "Handbook", "AdminUser",
    "Service", "ServicePackage", "ServiceOrder", "ServiceWorkLog",
    "UserAgreement",
    "FollowUp",
    "Branch",
    "Enterprise", "EnterpriseInvite",
    "PackageConsumption",
    "CourseSession", "CourseEnrollmentV2", "CourseCheckin", "CourseFollowup",
    "AgentApiKey", "WebhookEvent",
    "MemberDeepAnalysis", "ConsultantTalentAnalysis",
]
