-- 创建 Analyst 信息表
-- 用于管理分析师的业务资料（与用户账号系统解耦）

-- 创建表
CREATE TABLE IF NOT EXISTS analyst (
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

-- 添加注释
COMMENT ON TABLE analyst IS 'Analyst 信息表，存储分析师的业务资料（姓名、地区、SFC 编号等）';
COMMENT ON COLUMN analyst.full_name IS '英文姓名';
COMMENT ON COLUMN analyst.chinese_name IS '中文姓名';
COMMENT ON COLUMN analyst.email IS '邮箱地址（用于业务记录和与用户账号的隐式关联）';
COMMENT ON COLUMN analyst.suffix IS '后缀（如：CFA, CPA）';
COMMENT ON COLUMN analyst.region_id IS '所属地区（外键关联到 region 表）';
COMMENT ON COLUMN analyst.sfc IS 'SFC 编号（证监会牌照号）';
COMMENT ON COLUMN analyst.is_active IS '是否激活状态';

-- 创建索引
CREATE INDEX idx_analyst_email ON analyst(email);
CREATE INDEX idx_analyst_region_id ON analyst(region_id);
CREATE INDEX idx_analyst_is_active ON analyst(is_active);

-- 启用行级安全（RLS）
ALTER TABLE analyst ENABLE ROW LEVEL SECURITY;

-- RLS Policy 1: 所有认证用户可以查看 Analyst 信息
CREATE POLICY "All authenticated users can view analysts"
ON analyst FOR SELECT
TO authenticated
USING (true);

-- RLS Policy 2: 只有 Admin 可以创建 Analyst 信息
CREATE POLICY "Only Admin can create analysts"
ON analyst FOR INSERT
TO authenticated
WITH CHECK (get_current_role() = 'admin');

-- RLS Policy 3: 只有 Admin 可以更新 Analyst 信息
CREATE POLICY "Only Admin can update analysts"
ON analyst FOR UPDATE
TO authenticated
USING (get_current_role() = 'admin')
WITH CHECK (get_current_role() = 'admin');

-- RLS Policy 4: 只有 Admin 可以删除 Analyst 信息
CREATE POLICY "Only Admin can delete analysts"
ON analyst FOR DELETE
TO authenticated
USING (get_current_role() = 'admin');

-- 创建更新时间戳触发器
CREATE OR REPLACE FUNCTION update_analyst_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER analyst_updated_at
  BEFORE UPDATE ON analyst
  FOR EACH ROW
  EXECUTE FUNCTION update_analyst_updated_at();
