-- Initialize default Admin account (idempotent).
-- Dev credential:
--   email: admin@neolyst.com
--   password: Admin123
--
-- Requirements:
--   - MUST create the user if missing
--   - MUST set app_metadata.role=admin
--   - MUST NOT reset password if user already exists
--
-- WARNING: Direct INSERT to auth.users is NOT recommended.
-- Prefer using Supabase Admin API (see web/scripts/init-default-admin.mjs).
-- This migration exists for bootstrap scenarios where API is not available.

create extension if not exists pgcrypto;

do $$
declare
  v_email constant text := 'admin@neolyst.com';
  v_password constant text := 'Admin123';
  v_user_id uuid;
  v_instance_id uuid;
begin
  select id
  into v_instance_id
  from auth.instances
  limit 1;

  if v_instance_id is null then
    v_instance_id := '00000000-0000-0000-0000-000000000000'::uuid;
    insert into auth.instances (id, uuid, raw_base_config, created_at, updated_at)
    values (v_instance_id, v_instance_id, '{}'::text, now(), now())
    on conflict (id) do nothing;
  end if;

  select id
  into v_user_id
  from auth.users
  where lower(email) = lower(v_email)
  order by created_at asc
  limit 1;

  if v_user_id is null then
    v_user_id := gen_random_uuid();

    -- Insert with ALL required token fields set to empty string (NOT NULL)
    -- gotrue expects these to be non-null strings
    insert into auth.users (
      instance_id,
      id,
      aud,
      role,
      email,
      encrypted_password,
      email_confirmed_at,
      confirmation_token,
      recovery_token,
      email_change_token_new,
      email_change_token_current,
      email_change,
      raw_app_meta_data,
      raw_user_meta_data,
      created_at,
      updated_at
    )
    values (
      v_instance_id,
      v_user_id,
      'authenticated',
      'authenticated',
      v_email,
      extensions.crypt(v_password, extensions.gen_salt('bf')),
      now(),
      '',  -- confirmation_token: empty string, NOT NULL
      '',  -- recovery_token: empty string, NOT NULL
      '',  -- email_change_token_new: empty string, NOT NULL
      '',  -- email_change_token_current: empty string, NOT NULL
      '',  -- email_change: empty string, NOT NULL
      jsonb_build_object(
        'provider', 'email',
        'providers', jsonb_build_array('email'),
        'role', 'admin'
      ),
      jsonb_build_object('full_name', 'System Administrator'),
      now(),
      now()
    );
  else
    update auth.users
    set raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb)
      || jsonb_build_object(
        'provider', 'email',
        'providers', jsonb_build_array('email'),
        'role', 'admin'
      ),
      raw_user_meta_data = coalesce(raw_user_meta_data, '{}'::jsonb)
      || jsonb_build_object('full_name', 'System Administrator'),
      email_confirmed_at = coalesce(email_confirmed_at, now()),
      updated_at = now()
    where id = v_user_id;
  end if;

  -- Ensure email identity exists for password login
  if not exists (
    select 1
    from auth.identities
    where user_id = v_user_id
      and provider = 'email'
  ) then
    insert into auth.identities (
      id,
      user_id,
      identity_data,
      provider,
      provider_id,
      last_sign_in_at,
      created_at,
      updated_at
    )
    values (
      gen_random_uuid(),
      v_user_id,
      jsonb_build_object(
        'sub', v_user_id::text,
        'email', v_email,
        'email_verified', true
      ),
      'email',
      v_email,  -- provider_id: MUST be set for email provider
      now(),
      now(),
      now()
    );
  end if;
end
$$;
