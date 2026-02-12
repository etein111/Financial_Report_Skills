-- 创建 RLS 辅助函数：从 JWT 的 app_metadata 中提取用户角色
-- 此函数用于数据库层的权限控制策略

CREATE OR REPLACE FUNCTION get_current_role()
RETURNS VARCHAR AS $$
  SELECT
    CASE
      WHEN auth.jwt()->>'app_metadata'->>'role' IS NOT NULL
      THEN (auth.jwt()->>'app_metadata'->>'role')::VARCHAR
      ELSE 'anonymous'
    END;
$$ LANGUAGE sql SECURITY DEFINER;

-- 添加注释
COMMENT ON FUNCTION get_current_role() IS
'从当前认证用户的 JWT token 中提取角色信息（admin/sa/analyst），用于 RLS policies';
