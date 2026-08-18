drop function if exists public.my_consultant_profile();

create function public.my_consultant_profile()
returns table (
  id uuid,
  reference_code text,
  display_name text,
  email text,
  phone text,
  municipality text,
  county text,
  profile_image_url text,
  catalog_slug text,
  status public.consultant_status,
  public_listing boolean,
  show_email boolean,
  show_phone boolean,
  vat_status public.consultant_vat_status,
  organization_number text,
  vat_number text,
  own_product_vat_rate numeric,
  own_product_prices_include_vat boolean
)
language sql
stable
security definer
set search_path = public
as $$
  select
    consultants.id,
    consultants.reference_code,
    consultants.display_name,
    consultants.email,
    consultants.phone,
    consultants.municipality,
    consultants.county,
    consultants.profile_image_url,
    consultants.catalog_slug,
    consultants.status,
    consultants.public_listing,
    consultants.show_email,
    consultants.show_phone,
    consultants.vat_status,
    consultants.organization_number,
    consultants.vat_number,
    consultants.own_product_vat_rate,
    consultants.own_product_prices_include_vat
  from public.consultants
  where consultants.user_id = auth.uid()
  limit 1;
$$;

revoke all on function public.my_consultant_profile() from public;
grant execute on function public.my_consultant_profile() to authenticated;

create or replace function public.update_my_consultant_profile(
  p_display_name text,
  p_email text default null,
  p_phone text default null,
  p_municipality text default null,
  p_county text default null,
  p_profile_image_url text default null,
  p_public_listing boolean default true,
  p_show_email boolean default false,
  p_show_phone boolean default false,
  p_vat_status public.consultant_vat_status default 'not_registered',
  p_organization_number text default null,
  p_vat_number text default null,
  p_own_product_vat_rate numeric default 25.00,
  p_own_product_prices_include_vat boolean default true
)
returns setof public.consultants
language plpgsql
security definer
set search_path = public
as $$
begin
  if auth.uid() is null then
    raise exception 'Du må være logget inn.';
  end if;

  if nullif(trim(p_display_name), '') is null then
    raise exception 'Navn må fylles ut.';
  end if;

  if p_own_product_vat_rate < 0 or p_own_product_vat_rate > 100 then
    raise exception 'MVA-satsen må være mellom 0 og 100.';
  end if;

  return query
  update public.consultants
  set
    display_name = trim(p_display_name),
    email = nullif(trim(p_email), ''),
    phone = nullif(trim(p_phone), ''),
    municipality = nullif(trim(p_municipality), ''),
    county = nullif(trim(p_county), ''),
    profile_image_url = nullif(trim(p_profile_image_url), ''),
    public_listing = p_public_listing,
    show_email = p_show_email and nullif(trim(p_email), '') is not null,
    show_phone = p_show_phone and nullif(trim(p_phone), '') is not null,
    consented_at = case
      when p_public_listing then coalesce(consultants.consented_at, now())
      else consultants.consented_at
    end,
    vat_status = p_vat_status,
    organization_number = nullif(trim(p_organization_number), ''),
    vat_number = nullif(trim(p_vat_number), ''),
    own_product_vat_rate = p_own_product_vat_rate,
    own_product_prices_include_vat = p_own_product_prices_include_vat,
    updated_at = now()
  where user_id = auth.uid()
  returning consultants.*;
end;
$$;

revoke all on function public.update_my_consultant_profile(
  text,
  text,
  text,
  text,
  text,
  text,
  boolean,
  boolean,
  boolean,
  public.consultant_vat_status,
  text,
  text,
  numeric,
  boolean
) from public;

grant execute on function public.update_my_consultant_profile(
  text,
  text,
  text,
  text,
  text,
  text,
  boolean,
  boolean,
  boolean,
  public.consultant_vat_status,
  text,
  text,
  numeric,
  boolean
) to authenticated;
