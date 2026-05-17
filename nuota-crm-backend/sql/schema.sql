-- =====================================================================
-- 诺控·塔塔学员管理系统 —— 数据库建表脚本
-- 版本：V1.0  |  数据库：PostgreSQL 15  |  DB：nuota_crm
-- 说明：按 PRD 第三节共 10 张表，含外键/唯一约束/常用索引
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 3.1 学员表
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS members (
  id              SERIAL PRIMARY KEY,
  name            VARCHAR(50) NOT NULL,                      -- 姓名
  phone           VARCHAR(20) UNIQUE NOT NULL,               -- 手机号（唯一标识）
  enterprise_name VARCHAR(100),                              -- 企业名称
  city            VARCHAR(50),                               -- 城市
  role            VARCHAR(20),                               -- 角色：boss/manager/consultant
  face_token      TEXT,                                      -- 人脸特征 token（腾讯云，密文）
  member_type     VARCHAR(20) DEFAULT 'trial',               -- trial 试听 / annual 年费 / vip 专案
  member_no       VARCHAR(20) UNIQUE,                        -- 学员编号，如 TT-2026-0001
  enroll_date     DATE,                                      -- 入学日期
  expire_date     DATE,                                      -- 到期日期
  referral_code   VARCHAR(20) UNIQUE,                        -- 专属推荐码
  referred_by     INTEGER REFERENCES members(id),            -- 推荐人 ID
  status          VARCHAR(20) DEFAULT 'active',              -- active / expired / frozen
  openid          VARCHAR(64) UNIQUE,                        -- 微信小程序 openid（可空，兼容后台录入）
  created_at      TIMESTAMP DEFAULT NOW(),
  updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_members_referred_by ON members(referred_by);
CREATE INDEX IF NOT EXISTS idx_members_status      ON members(status);
CREATE INDEX IF NOT EXISTS idx_members_member_type ON members(member_type);
CREATE INDEX IF NOT EXISTS idx_members_openid      ON members(openid);

-- updated_at 自动刷新触发器（members 表）
CREATE OR REPLACE FUNCTION trg_set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS members_set_updated_at ON members;
CREATE TRIGGER members_set_updated_at
  BEFORE UPDATE ON members
  FOR EACH ROW EXECUTE FUNCTION trg_set_updated_at();

-- ---------------------------------------------------------------------
-- 3.2 缴费记录表
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
  id          SERIAL PRIMARY KEY,
  member_id   INTEGER REFERENCES members(id),
  amount      DECIMAL(10,2),                                 -- 金额
  pay_type    VARCHAR(20),                                   -- trial 试听 / annual 年费
  pay_status  VARCHAR(20) DEFAULT 'pending',                 -- pending / paid / refunded
  pay_time    TIMESTAMP,
  remark      TEXT,
  created_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_member_id  ON payments(member_id);
CREATE INDEX IF NOT EXISTS idx_payments_pay_status ON payments(pay_status);

-- ---------------------------------------------------------------------
-- 3.3 课程场次表
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
  id           SERIAL PRIMARY KEY,
  session_no   VARCHAR(20) UNIQUE,                           -- 期号：2026-07-001
  start_date   DATE,
  end_date     DATE,
  location     VARCHAR(100),
  city         VARCHAR(50),
  capacity     INTEGER DEFAULT 100,                          -- 容量上限
  enrolled     INTEGER DEFAULT 0,                            -- 已报名数
  status       VARCHAR(20) DEFAULT 'open',                   -- open / full / closed / finished
  created_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_status     ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_start_date ON sessions(start_date);

-- ---------------------------------------------------------------------
-- 3.4 报名记录表
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS enrollments (
  id          SERIAL PRIMARY KEY,
  member_id   INTEGER REFERENCES members(id),
  session_id  INTEGER REFERENCES sessions(id),
  enroll_time TIMESTAMP DEFAULT NOW(),
  status      VARCHAR(20) DEFAULT 'enrolled',                -- enrolled / attended / absent
  UNIQUE(member_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_enrollments_session_id ON enrollments(session_id);

-- ---------------------------------------------------------------------
-- 3.5 签到记录表
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS checkins (
  id           SERIAL PRIMARY KEY,
  member_id    INTEGER REFERENCES members(id),
  session_id   INTEGER REFERENCES sessions(id),
  checkin_day  INTEGER,                                      -- 第几天：1/2/3
  checkin_time TIMESTAMP DEFAULT NOW(),
  method       VARCHAR(20) DEFAULT 'face',                   -- face 刷脸 / manual 手动
  operator_id  INTEGER,                                      -- 手动签到时操作员 ID
  UNIQUE(member_id, session_id, checkin_day)
);

CREATE INDEX IF NOT EXISTS idx_checkins_session_id ON checkins(session_id);
CREATE INDEX IF NOT EXISTS idx_checkins_member_id  ON checkins(member_id);

-- ---------------------------------------------------------------------
-- 3.6 推荐记录表
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS referrals (
  id            SERIAL PRIMARY KEY,
  referrer_id   INTEGER REFERENCES members(id),              -- 推荐人
  referee_id    INTEGER REFERENCES members(id),              -- 被推荐人
  status        VARCHAR(20) DEFAULT 'pending',               -- pending / confirmed / invalid
  confirm_time  TIMESTAMP,                                   -- 被推荐人缴费成功时间
  reward_type   VARCHAR(20),                                 -- visit_once / full_package
  reward_status VARCHAR(20) DEFAULT 'pending',               -- pending / activated / used / expired
  created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_referrals_referee_id  ON referrals(referee_id);
CREATE INDEX IF NOT EXISTS idx_referrals_status      ON referrals(status);

-- ---------------------------------------------------------------------
-- 3.7 下店权益表
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS visit_rewards (
  id            SERIAL PRIMARY KEY,
  member_id     INTEGER REFERENCES members(id),
  source        VARCHAR(20),                                 -- referral 推荐所得
  referral_id   INTEGER REFERENCES referrals(id),
  status        VARCHAR(20) DEFAULT 'available',             -- available / booked / used / expired
  activate_time TIMESTAMP,
  expire_time   TIMESTAMP,                                   -- 激活后 24 个月
  used_time     TIMESTAMP,
  booking_id    INTEGER,                                     -- 关联预约 ID（建表顺序原因暂不设 FK）
  created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_visit_rewards_member_id ON visit_rewards(member_id);
CREATE INDEX IF NOT EXISTS idx_visit_rewards_status    ON visit_rewards(status);

-- ---------------------------------------------------------------------
-- 3.9 顾问表（预约表依赖 consultant_id，先建顾问表）
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS consultants (
  id              SERIAL PRIMARY KEY,
  name            VARCHAR(50),
  phone           VARCHAR(20),
  monthly_days    INTEGER DEFAULT 14,                        -- 每月可下店天数
  course_days     INTEGER DEFAULT 8,                         -- 每月课程占用天数
  status          VARCHAR(20) DEFAULT 'active',
  created_at      TIMESTAMP DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- 3.8 下店预约表
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS visit_bookings (
  id             SERIAL PRIMARY KEY,
  member_id      INTEGER REFERENCES members(id),
  reward_id      INTEGER REFERENCES visit_rewards(id),
  consultant_id  INTEGER REFERENCES consultants(id),         -- 顾问 ID
  apply_time     TIMESTAMP DEFAULT NOW(),
  preferred_date DATE,                                       -- 学员期望日期
  confirmed_date DATE,                                       -- 确认日期
  status         VARCHAR(20) DEFAULT 'pending',              -- pending / confirmed / completed / cancelled
  duration_days  INTEGER DEFAULT 2,                          -- 下店天数
  city           VARCHAR(50),
  address        TEXT,
  remark         TEXT,
  complete_time  TIMESTAMP,
  member_rating  INTEGER,                                    -- 学员评分 1-5
  created_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_visit_bookings_member_id     ON visit_bookings(member_id);
CREATE INDEX IF NOT EXISTS idx_visit_bookings_consultant_id ON visit_bookings(consultant_id);
CREATE INDEX IF NOT EXISTS idx_visit_bookings_status        ON visit_bookings(status);
CREATE INDEX IF NOT EXISTS idx_visit_bookings_confirmed_date ON visit_bookings(confirmed_date);

-- 回补 visit_rewards.booking_id 的外键（此时 visit_bookings 已建）
ALTER TABLE visit_rewards
  DROP CONSTRAINT IF EXISTS fk_visit_rewards_booking_id;
ALTER TABLE visit_rewards
  ADD CONSTRAINT fk_visit_rewards_booking_id
  FOREIGN KEY (booking_id) REFERENCES visit_bookings(id);

-- ---------------------------------------------------------------------
-- 3.10 课程手册表
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS handbooks (
  id            SERIAL PRIMARY KEY,
  member_id     INTEGER REFERENCES members(id),
  session_id    INTEGER REFERENCES sessions(id),
  day1_data     JSONB,                                       -- Day1 填写内容
  day2_data     JSONB,                                       -- Day2 填写内容
  day3_data     JSONB,                                       -- Day3 填写内容
  is_complete   BOOLEAN DEFAULT FALSE,
  sign_time     TIMESTAMP,                                   -- 老师签字确认时间
  consultant_id INTEGER REFERENCES consultants(id),
  created_at    TIMESTAMP DEFAULT NOW(),
  UNIQUE(member_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_handbooks_session_id ON handbooks(session_id);

-- ---------------------------------------------------------------------
-- 附表：后台管理账号 admin_users（非 PRD 原表，后台登录必需）
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_users (
  id            SERIAL PRIMARY KEY,
  username      VARCHAR(50) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  real_name     VARCHAR(50),
  phone         VARCHAR(20),
  role          VARCHAR(20) DEFAULT 'admin',                -- admin / operator
  status        VARCHAR(20) DEFAULT 'active',
  created_at    TIMESTAMP DEFAULT NOW()
);

COMMIT;
