with saved_consultant as (
  insert into public.consultants (
    reference_code,
    display_name,
    catalog_slug,
    status,
    public_listing,
    consented_at,
    verified_at
  ) values (
    'LISBETHOVERBYE',
    'Lisbeth Øverbye',
    'lisbeth-overbye',
    'active',
    true,
    now(),
    now()
  )
  on conflict (reference_code) do update set
    display_name = excluded.display_name,
    catalog_slug = excluded.catalog_slug,
    status = excluded.status,
    public_listing = excluded.public_listing,
    consented_at = excluded.consented_at,
    verified_at = excluded.verified_at
  returning id
)
insert into public.subscriptions (consultant_id, plan, status)
select id, 'free', 'active'
from saved_consultant
where not exists (
  select 1
  from public.subscriptions
  where consultant_id = saved_consultant.id and ends_at is null
);
