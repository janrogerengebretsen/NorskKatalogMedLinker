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
  from public.catalog_sync_state as state
  where state.key = sync_key;
end;
$$;

revoke all on function public.finish_catalog_sync(text, text, text, text, integer, integer, text, integer, jsonb) from public;
grant execute on function public.finish_catalog_sync(text, text, text, text, integer, integer, text, integer, jsonb) to anon, authenticated;
