-- Fix NULL string fields in auth.users that cause gotrue to fail.
-- Error: "sql: Scan error on column index X, name "xxx": converting NULL to string is unsupported"
--
-- Root cause: Direct INSERT to auth.users bypasses gotrue validation,
-- leaving token fields as NULL instead of empty strings.

do $$
begin
  -- Fix users table NULL string fields
  UPDATE auth.users SET
    confirmation_token = COALESCE(confirmation_token, ''),
    recovery_token = COALESCE(recovery_token, ''),
    email_change_token_new = COALESCE(email_change_token_new, ''),
    email_change_token_current = COALESCE(email_change_token_current, ''),
    email_change = COALESCE(email_change, '')
  WHERE
    confirmation_token IS NULL OR
    recovery_token IS NULL OR
    email_change_token_new IS NULL OR
    email_change_token_current IS NULL OR
    email_change IS NULL;

  -- Fix identities table NULL provider_id for email provider
  UPDATE auth.identities
  SET provider_id = identity_data->>'email'
  WHERE provider = 'email' AND provider_id IS NULL;

  raise notice 'Fixed auth.users and auth.identities NULL fields';
end
$$;
