-- Initialize default Admin account (idempotent).
-- Dev credential:
--   email: jiang_jiahong@qq.com
--   password: Admin123
--
-- Requirements:
-- - MUST create the user if missing
-- - MUST set app_metadata.role=admin
-- - MUST NOT reset password if user already exists

create extension if not exists pgcrypto;

do $$
declare
  v_email constant text := 'jiang_jiahong@qq.com';
  v_password constant text := 'Admin123';
  v_user_id uuid;
  v_instance_id uuid;
  v_has_provider_id boolean;
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

    insert into auth.users (
      instance_id,
      id,
      aud,
      role,
      email,
      encrypted_password,
      email_confirmed_at,
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

  -- Ensure email identity exists for password login.
  if not exists (
    select 1
    from auth.identities
    where user_id = v_user_id
      and provider = 'email'
  ) then
    select exists (
      select 1
      from information_schema.columns
      where table_schema = 'auth'
        and table_name = 'identities'
        and column_name = 'provider_id'
    )
    into v_has_provider_id;

    if v_has_provider_id then
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
        v_email,
        now(),
        now(),
        now()
      );
    else
      insert into auth.identities (
        id,
        user_id,
        identity_data,
        provider,
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
        now(),
        now(),
        now()
      );
    end if;
  end if;
end
$$;

