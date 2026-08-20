alter table public.consultants
add column if not exists link_use_count bigint not null default 0;

comment on column public.consultants.link_use_count is
  'Simple counter for how many times a consultant catalog link has been opened. This is not a visit log.';

create or replace function public.increment_consultant_link_use(p_reference_code text)
returns table (
  link_use_count bigint
)
language sql
security definer
set search_path = public
as $$
  update public.consultants
  set link_use_count = consultants.link_use_count + 1,
      updated_at = now()
  where consultants.reference_code = upper(trim(p_reference_code))
    and consultants.status = 'active'
    and consultants.public_listing = true
  returning consultants.link_use_count;
$$;

grant execute on function public.increment_consultant_link_use(text) to anon, authenticated;
