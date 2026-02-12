-- 创建 Region（地区）表
-- 用于管理系统中的地区数据

-- 创建表
CREATE TABLE IF NOT EXISTS region (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR UNIQUE NOT NULL,
  code VARCHAR UNIQUE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 添加注释
COMMENT ON TABLE region IS '地区表，存储系统中可用的地区信息';
COMMENT ON COLUMN region.name IS '地区名称（如：Hong Kong, Singapore）';
COMMENT ON COLUMN region.code IS '地区代码（如：HK, SG）';

-- 启用行级安全（RLS）
ALTER TABLE region ENABLE ROW LEVEL SECURITY;

-- RLS Policy 1: 所有认证用户可以查看地区
CREATE POLICY "All authenticated users can view regions"
ON region FOR SELECT
TO authenticated
USING (true);

-- RLS Policy 2: 只有 Admin 可以创建地区
CREATE POLICY "Only Admin can create regions"
ON region FOR INSERT
TO authenticated
WITH CHECK (get_current_role() = 'admin');

-- RLS Policy 3: 只有 Admin 可以更新地区
CREATE POLICY "Only Admin can update regions"
ON region FOR UPDATE
TO authenticated
USING (get_current_role() = 'admin')
WITH CHECK (get_current_role() = 'admin');

-- RLS Policy 4: 只有 Admin 可以删除地区
CREATE POLICY "Only Admin can delete regions"
ON region FOR DELETE
TO authenticated
USING (get_current_role() = 'admin');

-- 创建更新时间戳触发器
CREATE OR REPLACE FUNCTION update_region_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER region_updated_at
  BEFORE UPDATE ON region
  FOR EACH ROW
  EXECUTE FUNCTION update_region_updated_at();
