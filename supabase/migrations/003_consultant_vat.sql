create type public.consultant_vat_status as enum (
  'not_registered',
  'registered',
  'exempt'
);

alter table public.consultants
  add column vat_status public.consultant_vat_status
    not null default 'not_registered',
  add column organization_number text,
  add column vat_number text,
  add column default_vat_rate numeric(5, 2)
    not null default 25.00
    check (default_vat_rate >= 0 and default_vat_rate <= 100),
  add column prices_include_vat boolean not null default true,
  add column vat_verified_at timestamptz;

create or replace view public.public_consultants
with (security_invoker = true)
as
select
  id,
  reference_code,
  display_name,
  municipality,
  county,
  profile_image_url,
  catalog_slug,
  status,
  public_listing,
  vat_status,
  default_vat_rate,
  prices_include_vat
from public.consultants
where status = 'active' and public_listing = true;

grant update (
  vat_status,
  organization_number,
  vat_number,
  default_vat_rate,
  prices_include_vat
) on public.consultants to authenticated;

grant select (
  id,
  reference_code,
  display_name,
  municipality,
  county,
  profile_image_url,
  catalog_slug,
  status,
  public_listing,
  vat_status,
  default_vat_rate,
  prices_include_vat
) on public.consultants to anon, authenticated;
