create table if not exists public.catalog_sync_state (
  key text primary key,
  last_attempt_at timestamptz,
  last_success_at timestamptz,
  sync_started_at timestamptz,
  status text not null default 'never',
  http_status integer,
  error_message text,
  products_found integer,
  updated_at timestamptz not null default now()
);

create table if not exists public.catalog_sync_events (
  id bigserial primary key,
  created_at timestamptz not null default now(),
  key text not null,
  source_url text not null,
  status text not null,
  http_status integer,
  duration_ms integer,
  error_message text,
  products_found integer,
  details jsonb not null default '{}'::jsonb
);

alter table public.catalog_sync_state enable row level security;
alter table public.catalog_sync_events enable row level security;

drop policy if exists "Admins read catalog sync state"
on public.catalog_sync_state;
create policy "Admins read catalog sync state"
on public.catalog_sync_state for select
to authenticated
using (public.is_admin());

drop policy if exists "Admins read catalog sync events"
on public.catalog_sync_events;
create policy "Admins read catalog sync events"
on public.catalog_sync_events for select
to authenticated
using (public.is_admin());

revoke all on public.catalog_sync_state from public;
revoke all on public.catalog_sync_events from public;
grant select on public.catalog_sync_state to authenticated;
grant select on public.catalog_sync_events to authenticated;

create or replace function public.begin_catalog_sync(
  p_sync_token text,
  p_key text,
  p_min_age_seconds integer default 900
)
returns table (
  should_sync boolean,
  last_success_at timestamptz,
  status text
)
language plpgsql
security definer
set search_path = public, private, extensions, pg_temp
as $$
declare
  expected_hash text;
  current_state public.catalog_sync_state%rowtype;
  sync_key text := btrim(coalesce(p_key, 'official_products'));
  min_age interval := make_interval(secs => greatest(coalesce(p_min_age_seconds, 900), 60));
begin
  select token_hash
  into expected_hash
  from private.catalog_sync_settings
  where singleton = true;

  if expected_hash is null
    or encode(digest(coalesce(p_sync_token, ''), 'sha256'), 'hex') <> expected_hash
  then
    raise exception 'Invalid catalog sync token';
  end if;

  insert into public.catalog_sync_state (key, status)
  values (sync_key, 'never')
  on conflict (key) do nothing;

  select *
  into current_state
  from public.catalog_sync_state
  where key = sync_key
  for update;

  if current_state.sync_started_at is not null
    and current_state.sync_started_at > now() - interval '5 minutes'
  then
    return query select false, current_state.last_success_at, current_state.status;
    return;
  end if;

  if current_state.last_success_at is not null
    and current_state.last_success_at > now() - min_age
  then
    return query select false, current_state.last_success_at, current_state.status;
    return;
  end if;

  update public.catalog_sync_state
  set sync_started_at = now(),
      last_attempt_at = now(),
      status = 'running',
      http_status = null,
      error_message = null,
      updated_at = now()
  where key = sync_key;

  return query select true, current_state.last_success_at, 'running'::text;
end;
$$;

create or replace function public.finish_catalog_sync(
  p_sync_token text,
  p_key text,
  p_source_url text,
  p_status text,
  p_http_status integer default null,
  p_duration_ms integer default null,
  p_error_message text default null,
  p_products_found integer default null,
  p_details jsonb default '{}'::jsonb
)
returns table (
  key text,
  last_success_at timestamptz,
  status text
)
language plpgsql
security definer
set search_path = public, private, extensions, pg_temp
as $$
declare
  expected_hash text;
  sync_key text := btrim(coalesce(p_key, 'official_products'));
  sync_status text := btrim(coalesce(p_status, 'sync_failed'));
begin
  select token_hash
  into expected_hash
  from private.catalog_sync_settings
  where singleton = true;

  if expected_hash is null
    or encode(digest(coalesce(p_sync_token, ''), 'sha256'), 'hex') <> expected_hash
  then
    raise exception 'Invalid catalog sync token';
  end if;

  insert into public.catalog_sync_state (key, status)
  values (sync_key, 'never')
  on conflict (key) do nothing;

  insert into public.catalog_sync_events (
    key,
    source_url,
    status,
    http_status,
    duration_ms,
    error_message,
    products_found,
    details
  )
  values (
    sync_key,
    btrim(coalesce(p_source_url, '')),
    sync_status,
    p_http_status,
    p_duration_ms,
    nullif(btrim(coalesce(p_error_message, '')), ''),
    p_products_found,
    coalesce(p_details, '{}'::jsonb)
  );

  update public.catalog_sync_state state
  set sync_started_at = null,
      last_attempt_at = now(),
      last_success_at = case when sync_status = 'success' then now() else state.last_success_at end,
      status = sync_status,
      http_status = p_http_status,
      error_message = case
        when sync_status = 'success' then null
        else nullif(btrim(coalesce(p_error_message, '')), '')
      end,
      products_found = coalesce(p_products_found, state.products_found),
      updated_at = now()
  where state.key = sync_key;

  return query
  select state.key, state.last_success_at, state.status
  from public.catalog_sync_state state
  where state.key = sync_key;
end;
$$;

revoke all on function public.begin_catalog_sync(text, text, integer) from public;
revoke all on function public.finish_catalog_sync(text, text, text, text, integer, integer, text, integer, jsonb) from public;
grant execute on function public.begin_catalog_sync(text, text, integer) to anon, authenticated;
grant execute on function public.finish_catalog_sync(text, text, text, text, integer, integer, text, integer, jsonb) to anon, authenticated;

comment on table public.catalog_sync_state is
  'Current status for on-demand official Tupperware catalog synchronization.';

comment on table public.catalog_sync_events is
  'System log of attempts to refresh the official Tupperware catalog. Does not log customer visits.';
