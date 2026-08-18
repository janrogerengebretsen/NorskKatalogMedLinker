alter table public.consultants
  rename column default_vat_rate to own_product_vat_rate;

alter table public.consultants
  rename column prices_include_vat to own_product_prices_include_vat;

alter table public.inventory
  add column is_for_sale boolean not null default false,
  add column sale_price_nok numeric(12, 2)
    check (sale_price_nok is null or sale_price_nok >= 0);

comment on column public.consultants.vat_status is
  'MVA-status for sales where the consultant is the seller.';
comment on column public.consultants.own_product_vat_rate is
  'Default MVA rate for the consultant own inventory sales only.';
comment on column public.consultants.own_product_prices_include_vat is
  'Whether prices for the consultant own inventory include MVA.';
comment on column public.inventory.sale_price_nok is
  'Price set by the consultant for an own inventory item. Tupperware catalog prices are not stored here.';

drop view public.public_consultants;

create view public.public_consultants
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
  public_listing
from public.consultants
where status = 'active' and public_listing = true;

grant select on public.public_consultants to anon, authenticated;

revoke select (
  vat_status,
  own_product_vat_rate,
  own_product_prices_include_vat
) on public.consultants from anon;
