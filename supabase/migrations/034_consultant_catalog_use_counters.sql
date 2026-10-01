create table if not exists public.consultant_catalog_use_counters (
  consultant_id uuid not null references public.consultants(id) on delete cascade,
  catalog_key text not null,
  open_count bigint not null default 0 check (open_count >= 0),
  last_opened_at timestamptz,
  primary key (consultant_id, catalog_key)
);

alter table public.consultant_catalog_use_counters enable row level security;

drop policy if exists "Superadmins read catalog counters"
  on public.consultant_catalog_use_counters;
create policy "Superadmins read catalog counters"
  on public.consultant_catalog_use_counters
  for select
  using (public.is_super_admin());

comment on table public.consultant_catalog_use_counters is
  'Aggregated catalog opening counters. One row per consultant and catalog; no visitor log is stored.';

create or replace function public.increment_consultant_catalog_use(
  p_reference_code text,
  p_catalog_key text
)
returns table (
  catalog_key text,
  open_count bigint,
  total_count bigint
)
language plpgsql
security definer
set search_path = public
as $$
declare
  v_consultant_id uuid;
  v_catalog_key text := lower(trim(coalesce(p_catalog_key, '')));
begin
  if v_catalog_key not in (
    'norsk-nettkatalog',
    'norsk-produktkatalog',
    'september-2026',
    'oktober-2026',
    'tw-host-vinter-2026-27'
  ) then
    return;
  end if;

  select consultants.id
    into v_consultant_id
  from public.consultants
  where consultants.reference_code = upper(trim(p_reference_code))
    and consultants.status = 'active'
    and consultants.public_listing = true;

  if v_consultant_id is null then
    return;
  end if;

  insert into public.consultant_catalog_use_counters (
    consultant_id,
    catalog_key,
    open_count,
    last_opened_at
  ) values (
    v_consultant_id,
    v_catalog_key,
    1,
    now()
  )
  on conflict (consultant_id, catalog_key) do update
    set open_count = consultant_catalog_use_counters.open_count + 1,
        last_opened_at = now();

  return query
  select counters.catalog_key,
         counters.open_count,
         sum(counters.open_count) over ()::bigint
  from public.consultant_catalog_use_counters counters
  where counters.consultant_id = v_consultant_id
  order by counters.catalog_key;
end;
$$;

grant execute on function public.increment_consultant_catalog_use(text, text)
  to anon, authenticated;

grant select on public.consultant_catalog_use_counters to authenticated;

