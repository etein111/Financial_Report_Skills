-- 启用 pgcrypto 扩展（用于密码加密）
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 用户角色枚举
CREATE TYPE user_role AS ENUM ('admin', 'sa', 'analyst');

COMMENT ON TYPE user_role IS '用户角色：admin（系统管理员）、sa（合规人员）、analyst（普通分析师）';

-- 初始化默认 Admin 用户
DELETE FROM auth.users WHERE email = 'admin@neolyst.com';

INSERT INTO auth.users (
  instance_id,
  id,
  aud,
  role,
  email,
  encrypted_password,
  email_confirmed_at,
  raw_user_meta_data,
  raw_app_meta_data,
  created_at,
  updated_at
) VALUES (
  (SELECT id FROM auth.instances LIMIT 1),
  gen_random_uuid(),
  'authenticated',
  'authenticated',
  'admin@neolyst.com',
  crypt('Admin123', gen_salt('bf')),
  now(),
  '{"full_name": "Admin", "role": "admin"}'::jsonb,
  '{"role": "admin", "provider": "email"}'::jsonb,
  now(),
  now()
);

-- Region 表
DROP TABLE IF EXISTS region CASCADE;

CREATE TABLE region (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR UNIQUE NOT NULL,
  code VARCHAR UNIQUE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

COMMENT ON TABLE region IS '地区表';
COMMENT ON COLUMN region.name IS '地区名称';
COMMENT ON COLUMN region.code IS '地区代码';

ALTER TABLE region ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Region is viewable by all authenticated users"
  ON region FOR SELECT TO authenticated USING (true);

CREATE POLICY "Region can be created by admin only"
  ON region FOR INSERT TO authenticated
  WITH CHECK ((auth.jwt()->'app_metadata'->>'role') = 'admin');

CREATE POLICY "Region can be updated by admin only"
  ON region FOR UPDATE TO authenticated
  USING ((auth.jwt()->'app_metadata'->>'role') = 'admin')
  WITH CHECK ((auth.jwt()->'app_metadata'->>'role') = 'admin');

CREATE POLICY "Region can be deleted by admin only"
  ON region FOR DELETE TO authenticated
  USING ((auth.jwt()->'app_metadata'->>'role') = 'admin');

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER region_updated_at
  BEFORE UPDATE ON region FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- Region 初始化数据
INSERT INTO region (name, code) VALUES
  ('China', 'CN'),
  ('Hong Kong', 'HK'),
  ('Japan', 'JP'),
  ('Taiwan', 'TW'),
  ('Korea', 'KR'),
  ('India', 'IN'),
  ('Macau', 'MO'),
  ('United States', 'US');

-- Analyst 表
DROP TABLE IF EXISTS analyst CASCADE;

CREATE TABLE analyst (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  full_name VARCHAR NOT NULL,
  chinese_name VARCHAR,
  email VARCHAR UNIQUE NOT NULL,
  suffix VARCHAR,
  region_id UUID REFERENCES region(id) ON DELETE SET NULL,
  sfc VARCHAR,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

COMMENT ON TABLE analyst IS 'Analyst 信息表';
COMMENT ON COLUMN analyst.full_name IS '英文姓名';
COMMENT ON COLUMN analyst.chinese_name IS '中文姓名';
COMMENT ON COLUMN analyst.email IS '邮箱地址';
COMMENT ON COLUMN analyst.suffix IS '后缀';
COMMENT ON COLUMN analyst.region_id IS '所属地区（外键）';
COMMENT ON COLUMN analyst.sfc IS 'SFC 编号';
COMMENT ON COLUMN analyst.is_active IS '是否激活状态';

ALTER TABLE analyst ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Analyst is viewable by all authenticated users"
  ON analyst FOR SELECT TO authenticated USING (true);

CREATE POLICY "Analyst can be created by admin only"
  ON analyst FOR INSERT TO authenticated
  WITH CHECK ((auth.jwt()->'app_metadata'->>'role') = 'admin');

CREATE POLICY "Analyst can be updated by admin only"
  ON analyst FOR UPDATE TO authenticated
  USING ((auth.jwt()->'app_metadata'->>'role') = 'admin')
  WITH CHECK ((auth.jwt()->'app_metadata'->>'role') = 'admin');

CREATE POLICY "Analyst can be deleted by admin only"
  ON analyst FOR DELETE TO authenticated
  USING ((auth.jwt()->'app_metadata'->>'role') = 'admin');

CREATE TRIGGER analyst_updated_at
  BEFORE UPDATE ON analyst FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- 验证
SELECT
  'region' as table_name,
  COUNT(*) as row_count
FROM region
UNION ALL
SELECT
  'analyst' as table_name,
  COUNT(*) as row_count
FROM analyst;

SELECT
  id,
  email,
  raw_app_meta_data->>'role' as role,
  email_confirmed_at,
  created_at
FROM auth.users
WHERE email = 'admin@neolyst.com';
