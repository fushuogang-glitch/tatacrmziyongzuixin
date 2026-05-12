# 诺控·塔塔学员管理系统 PRD
**版本：** V1.0  
**日期：** 2026-05-12  
**产品主体：** 武汉诺塔智控科技有限公司  
**负责人：** 九亿  
**开发方式：** Claude Code AI全栈自研  

---

## 一、产品概述

塔塔战略扩张年度课程配套CRM系统，覆盖学员全生命周期管理：
报名缴费 → 扫脸签到 → 课程手册 → 推荐裂变 → 权益兑换 → 下店预约 → 续费管理

**两端产品：**
- 微信小程序（学员端）
- Web管理后台（塔塔内部）

---

## 二、技术栈

| 层级 | 技术选型 |
|------|---------|
| 小程序前端 | uni-app + Vue3（编译微信小程序） |
| 管理后台前端 | Vue3 + Element Plus |
| 后端 | Python FastAPI |
| 数据库 | PostgreSQL 15 |
| 缓存 | Redis |
| 人脸识别 | 腾讯云人脸核身 API |
| 文件存储 | 本地 + 猫九NAS同步 |
| 部署 | 诺控2号机（10.18.18.3），Nginx反向代理 |
| 版本控制 | Git，本地仓库 |

---

## 三、数据库设计

### 3.1 学员表 `members`
```sql
CREATE TABLE members (
  id              SERIAL PRIMARY KEY,
  name            VARCHAR(50) NOT NULL,         -- 姓名
  phone           VARCHAR(20) UNIQUE NOT NULL,   -- 手机号（唯一标识）
  enterprise_name VARCHAR(100),                  -- 企业名称
  city            VARCHAR(50),                   -- 城市
  role            VARCHAR(20),                   -- 角色：boss/manager/consultant
  face_token      TEXT,                          -- 人脸特征token（腾讯云）
  member_type     VARCHAR(20) DEFAULT 'trial',   -- trial试听/annual年费/vip专案
  member_no       VARCHAR(20) UNIQUE,            -- 学员编号（如 TT-2026-0001）
  enroll_date     DATE,                          -- 入学日期
  expire_date     DATE,                          -- 到期日期
  referral_code   VARCHAR(20) UNIQUE,            -- 专属推荐码
  referred_by     INTEGER REFERENCES members(id), -- 推荐人ID
  status          VARCHAR(20) DEFAULT 'active',  -- active/expired/frozen
  created_at      TIMESTAMP DEFAULT NOW(),
  updated_at      TIMESTAMP DEFAULT NOW()
);
```

### 3.2 缴费记录表 `payments`
```sql
CREATE TABLE payments (
  id          SERIAL PRIMARY KEY,
  member_id   INTEGER REFERENCES members(id),
  amount      DECIMAL(10,2),                    -- 金额
  pay_type    VARCHAR(20),                       -- trial试听/annual年费
  pay_status  VARCHAR(20) DEFAULT 'pending',     -- pending/paid/refunded
  pay_time    TIMESTAMP,
  remark      TEXT,
  created_at  TIMESTAMP DEFAULT NOW()
);
```

### 3.3 课程场次表 `sessions`
```sql
CREATE TABLE sessions (
  id           SERIAL PRIMARY KEY,
  session_no   VARCHAR(20) UNIQUE,               -- 期号：如 2026-07-001
  start_date   DATE,
  end_date     DATE,
  location     VARCHAR(100),
  city         VARCHAR(50),
  capacity     INTEGER DEFAULT 100,              -- 容量上限
  enrolled     INTEGER DEFAULT 0,               -- 已报名数
  status       VARCHAR(20) DEFAULT 'open',       -- open/full/closed/finished
  created_at   TIMESTAMP DEFAULT NOW()
);
```

### 3.4 报名记录表 `enrollments`
```sql
CREATE TABLE enrollments (
  id          SERIAL PRIMARY KEY,
  member_id   INTEGER REFERENCES members(id),
  session_id  INTEGER REFERENCES sessions(id),
  enroll_time TIMESTAMP DEFAULT NOW(),
  status      VARCHAR(20) DEFAULT 'enrolled',    -- enrolled/attended/absent
  UNIQUE(member_id, session_id)
);
```

### 3.5 签到记录表 `checkins`
```sql
CREATE TABLE checkins (
  id           SERIAL PRIMARY KEY,
  member_id    INTEGER REFERENCES members(id),
  session_id   INTEGER REFERENCES sessions(id),
  checkin_day  INTEGER,                          -- 第几天：1/2/3
  checkin_time TIMESTAMP DEFAULT NOW(),
  method       VARCHAR(20) DEFAULT 'face',       -- face/manual
  operator_id  INTEGER,                          -- 手动签到时操作员ID
  UNIQUE(member_id, session_id, checkin_day)
);
```

### 3.6 推荐记录表 `referrals`
```sql
CREATE TABLE referrals (
  id            SERIAL PRIMARY KEY,
  referrer_id   INTEGER REFERENCES members(id), -- 推荐人
  referee_id    INTEGER REFERENCES members(id), -- 被推荐人
  status        VARCHAR(20) DEFAULT 'pending',   -- pending/confirmed/invalid
  confirm_time  TIMESTAMP,                       -- 被推荐人缴费成功时间
  reward_type   VARCHAR(20),                     -- visit_once/full_package
  reward_status VARCHAR(20) DEFAULT 'pending',   -- pending/activated/used/expired
  created_at    TIMESTAMP DEFAULT NOW()
);
```

### 3.7 下店权益表 `visit_rewards`
```sql
CREATE TABLE visit_rewards (
  id            SERIAL PRIMARY KEY,
  member_id     INTEGER REFERENCES members(id),
  source        VARCHAR(20),                     -- referral推荐所得
  referral_id   INTEGER REFERENCES referrals(id),
  status        VARCHAR(20) DEFAULT 'available', -- available/booked/used/expired
  activate_time TIMESTAMP,
  expire_time   TIMESTAMP,                       -- 激活后24个月
  used_time     TIMESTAMP,
  booking_id    INTEGER,                         -- 关联预约ID
  created_at    TIMESTAMP DEFAULT NOW()
);
```

### 3.8 下店预约表 `visit_bookings`
```sql
CREATE TABLE visit_bookings (
  id            SERIAL PRIMARY KEY,
  member_id     INTEGER REFERENCES members(id),
  reward_id     INTEGER REFERENCES visit_rewards(id),
  consultant_id INTEGER,                         -- 顾问ID
  apply_time    TIMESTAMP DEFAULT NOW(),
  preferred_date DATE,                           -- 学员期望日期
  confirmed_date DATE,                           -- 确认日期
  status        VARCHAR(20) DEFAULT 'pending',   -- pending/confirmed/completed/cancelled
  duration_days INTEGER DEFAULT 2,              -- 下店天数
  city          VARCHAR(50),
  address       TEXT,
  remark        TEXT,
  complete_time TIMESTAMP,
  member_rating INTEGER,                         -- 学员评分1-5
  created_at    TIMESTAMP DEFAULT NOW()
);
```

### 3.9 顾问表 `consultants`
```sql
CREATE TABLE consultants (
  id              SERIAL PRIMARY KEY,
  name            VARCHAR(50),
  phone           VARCHAR(20),
  monthly_days    INTEGER DEFAULT 14,            -- 每月可下店天数
  course_days     INTEGER DEFAULT 8,             -- 每月课程占用天数
  status          VARCHAR(20) DEFAULT 'active',
  created_at      TIMESTAMP DEFAULT NOW()
);
```

### 3.10 课程手册表 `handbooks`
```sql
CREATE TABLE handbooks (
  id           SERIAL PRIMARY KEY,
  member_id    INTEGER REFERENCES members(id),
  session_id   INTEGER REFERENCES sessions(id),
  day1_data    JSONB,                            -- Day1填写内容
  day2_data    JSONB,                            -- Day2填写内容
  day3_data    JSONB,                            -- Day3填写内容
  is_complete  BOOLEAN DEFAULT FALSE,
  sign_time    TIMESTAMP,                        -- 老师签字确认时间
  consultant_id INTEGER,
  created_at   TIMESTAMP DEFAULT NOW(),
  UNIQUE(member_id, session_id)
);
```

---

## 四、后端API设计（FastAPI）

### 目录结构
```
nuota-crm-backend/
├── main.py
├── config.py                    # 配置（DB/Redis/腾讯云Key）
├── database.py                  # DB连接
├── models/                      # SQLAlchemy模型
│   ├── member.py
│   ├── session.py
│   ├── checkin.py
│   ├── referral.py
│   ├── reward.py
│   └── booking.py
├── routers/                     # API路由
│   ├── auth.py                  # 微信登录/授权
│   ├── members.py               # 学员管理
│   ├── sessions.py              # 课程场次
│   ├── checkin.py               # 签到（含人脸）
│   ├── referrals.py             # 推荐管理
│   ├── rewards.py               # 权益管理
│   ├── bookings.py              # 下店预约
│   ├── handbooks.py             # 课程手册
│   └── admin.py                 # 后台管理接口
├── services/
│   ├── face_service.py          # 腾讯云人脸核身封装
│   ├── referral_service.py      # 推荐链判断+权益触发
│   ├── quota_service.py         # 下店名额管理
│   └── notify_service.py        # 企微/短信通知
├── schemas/                     # Pydantic数据模型
└── utils/
    ├── auth.py                  # JWT
    └── helpers.py
```

### 核心API列表

#### 学员端API

| Method | Path | 说明 |
|--------|------|------|
| POST | /api/auth/wx-login | 微信登录，返回token |
| POST | /api/members/register | 学员注册 |
| GET | /api/members/me | 获取我的信息 |
| POST | /api/face/bind | 绑定人脸（首次） |
| POST | /api/checkin/face | 扫脸签到 |
| GET | /api/sessions/available | 可报名场次列表 |
| POST | /api/sessions/{id}/enroll | 报名课程 |
| GET | /api/referrals/my-code | 我的推荐码 |
| GET | /api/referrals/my-list | 我的推荐记录 |
| GET | /api/rewards/my-rewards | 我的权益 |
| POST | /api/bookings/apply | 申请下店预约 |
| GET | /api/bookings/my-bookings | 我的预约记录 |
| GET | /api/handbooks/{session_id} | 获取手册 |
| PUT | /api/handbooks/{session_id} | 保存手册内容 |

#### 管理后台API

| Method | Path | 说明 |
|--------|------|------|
| GET | /admin/members | 学员列表（分页/筛选）|
| POST | /admin/members | 新增学员 |
| PUT | /admin/members/{id} | 编辑学员 |
| GET | /admin/sessions | 场次列表 |
| POST | /admin/sessions | 新建场次 |
| GET | /admin/checkins/{session_id} | 签到记录 |
| POST | /admin/checkins/manual | 手动签到 |
| GET | /admin/referrals | 推荐记录列表 |
| PUT | /admin/referrals/{id}/confirm | 确认推荐成立 |
| GET | /admin/rewards | 权益台账 |
| GET | /admin/bookings | 预约列表 |
| PUT | /admin/bookings/{id}/confirm | 确认预约+排顾问 |
| PUT | /admin/bookings/{id}/complete | 完成服务 |
| GET | /admin/quota/monthly | 本月名额状态 |
| PUT | /admin/quota/set | 设置月度名额上限 |
| GET | /admin/dashboard | 数据看板 |

---

## 五、微信小程序设计（uni-app）

### 目录结构
```
nuota-crm-miniapp/
├── pages/
│   ├── index/           # 首页（学员证+快捷入口）
│   ├── login/           # 微信授权登录
│   ├── profile/         # 我的信息
│   ├── face/
│   │   ├── bind/        # 绑定人脸
│   │   └── checkin/     # 扫脸签到
│   ├── sessions/
│   │   ├── list/        # 可报名场次
│   │   └── detail/      # 场次详情+报名
│   ├── referral/
│   │   ├── index/       # 推荐中心+进度
│   │   └── poster/      # 推荐海报生成
│   ├── rewards/
│   │   └── index/       # 权益中心
│   ├── booking/
│   │   ├── apply/       # 申请下店
│   │   └── list/        # 我的预约
│   └── handbook/
│       ├── day1/        # Day1手册
│       ├── day2/        # Day2手册
│       └── day3/        # Day3手册
├── components/
│   ├── member-card/     # 学员证组件
│   ├── progress-bar/    # 推荐进度条
│   └── reward-badge/    # 权益徽章
├── store/               # Pinia状态管理
├── api/                 # API请求封装
└── utils/
```

### 页面流程

**首次进入：**
```
小程序首页 → 微信授权登录 → 检查是否注册
    ↓ 未注册                    ↓ 已注册
  填写信息+绑定人脸           进入学员首页
```

**每期上课签到：**
```
首页点「签到」→ 选择当前场次 → 调用腾讯云人脸核身
    → 比对成功 → 签到完成 → 显示第几天打卡
    → 比对失败 → 提示重试 or 联系工作人员
```

**推荐流程：**
```
推荐中心 → 查看我的推荐码 → 生成专属海报
    → 朋友扫码进入小程序 → 注册时自动绑定推荐关系
    → 朋友缴费成功 → 推荐人权益自动激活
    → 推荐人收到企微通知「您的推荐奖励已到账」
```

---

## 六、管理后台设计（Vue3）

### 目录结构
```
nuota-crm-admin/
├── views/
│   ├── dashboard/       # 数据看板
│   ├── members/         # 学员管理
│   ├── sessions/        # 场次管理
│   ├── checkins/        # 签到管理
│   ├── referrals/       # 推荐管理
│   ├── rewards/         # 权益台账
│   ├── bookings/        # 预约调度
│   ├── consultants/     # 顾问管理
│   └── quota/           # 名额管理
├── components/
├── router/
├── store/
└── api/
```

### 数据看板核心指标
```
┌─────────────────────────────────────┐
│  总学员数    本月新增    试听转正率    │
│   328        24         67%         │
├─────────────────────────────────────┤
│  年度收入    本月收入    续费率       │
│  1640万      120万       82%         │
├─────────────────────────────────────┤
│  推荐转化率  本月下店    权益待兑     │
│   34%         18次        47个       │
└─────────────────────────────────────┘
```

---

## 七、下店名额管理规则

### 计算公式
```
每位顾问每月可下店次数 = (22工作日 - 8课程日 - 2缓冲日) ÷ 2天/次 = 6次
全月总名额 = 顾问人数 × 6次
```

### 名额控制逻辑
- 系统后台每月1日自动重置当月名额
- 学员预约时实时检查当月剩余名额
- 当月名额满 → 系统自动提示「当月已满，是否预约下月」
- 九哥可在后台手动调整月度上限

### 预约审核流程
```
学员提交预约申请
    ↓
系统检查：① 权益余额 ② 当月名额
    ↓ 通过
后台待审核队列
    ↓ 管理员确认
分配顾问 + 确认日期
    ↓
企微通知学员「预约已确认，顾问XXX将于X月X日到店」
    ↓
顾问服务完成 → 管理员标记完成 → 学员评分
```

---

## 八、开发里程碑

| 里程碑 | 截止日期 | 交付内容 |
|--------|---------|---------|
| M0 环境搭建 | Week 1 | 数据库/后端框架/小程序框架跑通 |
| M1 P0核心 | Week 5 | 学员注册+人脸绑定+扫脸签到+推荐码 |
| M2 权益系统 | Week 7 | 推荐权益自动触发+下店预约调度 |
| M3 管理后台 | Week 8 | Web后台全功能上线 |
| M4 测试上线 | Week 9 | 内测+修bug+灰度发布 |
| **🚀 正式上线** | **Week 10（7月底）** | **首期开课投入使用** |

---

## 九、部署架构

```
学员手机（微信小程序）
        ↓ HTTPS
Nginx（诺控2号机 10.18.18.3:443）
        ↓
FastAPI后端（:8000）
        ↓               ↓
PostgreSQL（:5432）   Redis（:6379）
        ↓
猫九NAS同步（10.18.18.5）每小时rsync
```

---

## 十、安全规范

- JWT Token鉴权，有效期7天，自动刷新
- 人脸特征token加密存储，不存明文照片
- 管理后台需要独立账号密码+手机验证码二次验证
- 所有API请求记录日志，存储30天
- 数据库每日凌晨2点自动备份到猫九

---

## 十一、给Claude Code的启动指令

```
你是诺控·塔塔学员管理系统的全栈开发工程师。

请按照本PRD文档，完成以下工程的开发：

1. 后端：Python FastAPI，目录 nuota-crm-backend/
2. 小程序：uni-app + Vue3，目录 nuota-crm-miniapp/
3. 管理后台：Vue3 + Element Plus，目录 nuota-crm-admin/

开发顺序：
① 先搭数据库（执行SQL建表）
② 后端框架+配置
③ 核心API（学员注册/人脸绑定/扫脸签到/推荐码）
④ 小程序核心页面
⑤ 管理后台
⑥ 联调测试

技术要求：
- 代码注释用中文
- 每个模块完成后告知，等待确认再继续
- 遇到需要外部Key（腾讯云/微信）的地方，用占位符CONFIG.XXX代替，统一在config.py配置
- 数据库连接默认：localhost:5432，DB名：nuota_crm

开始前先输出你的开发计划，确认后再动工。
```

---

*PRD Version 1.0 | 九亿出品 | 2026-05-12*
