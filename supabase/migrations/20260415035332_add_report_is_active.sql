ALTER TABLE report ADD COLUMN is_active boolean NOT NULL DEFAULT true;

COMMENT ON COLUMN report.is_active IS '软删除标记，true=正常，false=废弃。不参与状态机流转。';
