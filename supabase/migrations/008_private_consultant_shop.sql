alter table public.consultants
  add column own_shop_enabled boolean not null default false,
  add column own_shop_access_mode text not null default 'public'
    check (own_shop_access_mode in ('public', 'code')),
  add column own_shop_access_code_hash text;

update public.consultants
set own_shop_enabled = true
where reference_code = 'LISBETHOVERBYE';

drop view if exists public.public_consultant_inventory;
revoke select on public.inventory from anon;

create or replace function public.consultant_shop_status(
  p_reference_code text
)
returns table (
  enabled boolean,
  access_mode text,
  has_products boolean
)
language sql
stable
security definer
set search_path = public
as $$
  select
    consultants.own_shop_enabled,
    consultants.own_shop_access_mode,
    exists (
      select 1
      from public.inventory
      where inventory.consultant_id = consultants.id
        and inventory.is_active = true
        and inventory.is_for_sale = true
        and inventory.quantity > 0
        and inventory.sale_price_nok is not null
    )
  from public.consultants
  where consultants.reference_code = upper(trim(p_reference_code))
    and consultants.status = 'active'
    and consultants.public_listing = true
  limit 1;
$$;

revoke all on function public.consultant_shop_status(text) from public;
grant execute on function public.consultant_shop_status(text) to anon, authenticated;

create or replace function public.get_consultant_shop_inventory(
  p_reference_code text,
  p_access_code text default null
)
returns table (
  id uuid,
  reference_code text,
  consultant_name text,
  source_type text,
  product_handle text,
  article_number text,
  product_name text,
  description text,
  image_url text,
  source_product_url text,
  category text,
  quantity integer,
  sale_price_nok numeric,
  updated_at timestamptz
)
language plpgsql
stable
security definer
set search_path = public, extensions
as $$
declare
  selected_consultant public.consultants%rowtype;
begin
  select *
  into selected_consultant
  from public.consultants
  where consultants.reference_code = upper(trim(p_reference_code))
    and consultants.status = 'active'
    and consultants.public_listing = true;

  if not found or not selected_consultant.own_shop_enabled then
    raise exception 'Denne konsulentbutikken er ikke aktiv.';
  end if;

  if selected_consultant.own_shop_access_mode = 'code'
    and (
      selected_consultant.own_shop_access_code_hash is null
      or nullif(trim(p_access_code), '') is null
      or crypt(
        trim(p_access_code),
        selected_consultant.own_shop_access_code_hash
      ) <> selected_consultant.own_shop_access_code_hash
    )
  then
    raise exception 'Tilgangskoden er ikke riktig.';
  end if;

  return query
  select
    inventory.id,
    selected_consultant.reference_code,
    selected_consultant.display_name,
    inventory.source_type,
    inventory.product_handle,
    inventory.article_number,
    inventory.product_name,
    inventory.description,
    inventory.image_url,
    inventory.source_product_url,
    inventory.category,
    inventory.quantity,
    inventory.sale_price_nok,
    inventory.updated_at
  from public.inventory
  where inventory.consultant_id = selected_consultant.id
    and inventory.is_active = true
    and inventory.is_for_sale = true
    and inventory.quantity > 0
    and inventory.sale_price_nok is not null
  order by inventory.product_name;
end;
$$;

revoke all on function public.get_consultant_shop_inventory(text, text) from public;
grant execute on function public.get_consultant_shop_inventory(text, text)
to anon, authenticated;

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
  own_product_prices_include_vat boolean,
  own_shop_enabled boolean,
  own_shop_access_mode text,
  own_shop_has_access_code boolean
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
    consultants.own_product_prices_include_vat,
    consultants.own_shop_enabled,
    consultants.own_shop_access_mode,
    consultants.own_shop_access_code_hash is not null
  from public.consultants
  where consultants.user_id = auth.uid()
  limit 1;
$$;

revoke all on function public.my_consultant_profile() from public;
grant execute on function public.my_consultant_profile() to authenticated;

create or replace function public.update_my_consultant_shop_settings(
  p_enabled boolean,
  p_access_mode text,
  p_new_access_code text default null
)
returns table (
  own_shop_enabled boolean,
  own_shop_access_mode text,
  own_shop_has_access_code boolean
)
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  current_consultant public.consultants%rowtype;
  cleaned_code text;
begin
  if auth.uid() is null then
    raise exception 'Du må være logget inn.';
  end if;

  if p_access_mode not in ('public', 'code') then
    raise exception 'Ugyldig tilgangsvalg.';
  end if;

  cleaned_code := nullif(trim(p_new_access_code), '');

  if cleaned_code is not null
    and (char_length(cleaned_code) < 4 or char_length(cleaned_code) > 40)
  then
    raise exception 'Kundekoden må inneholde mellom 4 og 40 tegn.';
  end if;

  select *
  into current_consultant
  from public.consultants
  where user_id = auth.uid();

  if not found then
    raise exception 'Fant ikke konsulentprofilen.';
  end if;

  if p_enabled
    and p_access_mode = 'code'
    and cleaned_code is null
    and current_consultant.own_shop_access_code_hash is null
  then
    raise exception 'Velg en kundekode før kodebeskyttelsen aktiveres.';
  end if;

  return query
  update public.consultants
  set
    own_shop_enabled = p_enabled,
    own_shop_access_mode = p_access_mode,
    own_shop_access_code_hash = case
      when cleaned_code is not null
        then crypt(cleaned_code, gen_salt('bf'))
      else consultants.own_shop_access_code_hash
    end,
    updated_at = now()
  where user_id = auth.uid()
  returning
    consultants.own_shop_enabled,
    consultants.own_shop_access_mode,
    consultants.own_shop_access_code_hash is not null;
end;
$$;

revoke all on function public.update_my_consultant_shop_settings(
  boolean,
  text,
  text
) from public;
grant execute on function public.update_my_consultant_shop_settings(
  boolean,
  text,
  text
) to authenticated;

drop function if exists public.submit_consultant_inventory_order(
  text,
  jsonb,
  jsonb
);

create function public.submit_consultant_inventory_order(
  p_reference_code text,
  p_customer jsonb,
  p_items jsonb,
  p_access_code text default null
)
returns uuid
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  selected_consultant public.consultants%rowtype;
  new_order_id uuid;
  customer_name text;
  customer_email text;
  customer_phone text;
  customer_message text;
  item jsonb;
  selected_inventory public.inventory%rowtype;
  requested_quantity integer;
begin
  customer_name := trim(coalesce(p_customer->>'name', ''));
  customer_email := nullif(trim(coalesce(p_customer->>'email', '')), '');
  customer_phone := nullif(trim(coalesce(p_customer->>'phone', '')), '');
  customer_message := nullif(trim(coalesce(p_customer->>'message', '')), '');

  if char_length(customer_name) < 2 or char_length(customer_name) > 120 then
    raise exception 'Oppgi kundens navn.';
  end if;

  if customer_email is null and customer_phone is null then
    raise exception 'Oppgi e-postadresse eller telefonnummer.';
  end if;

  if jsonb_typeof(p_items) <> 'array'
    or jsonb_array_length(p_items) < 1
    or jsonb_array_length(p_items) > 30 then
    raise exception 'Bestillingen må inneholde mellom 1 og 30 varer.';
  end if;

  select *
  into selected_consultant
  from public.consultants
  where consultants.reference_code = upper(trim(p_reference_code))
    and consultants.status = 'active'
    and consultants.public_listing = true
    and consultants.own_shop_enabled = true;

  if not found then
    raise exception 'Konsulentbutikken finnes ikke eller er ikke aktiv.';
  end if;

  if selected_consultant.own_shop_access_mode = 'code'
    and (
      selected_consultant.own_shop_access_code_hash is null
      or nullif(trim(p_access_code), '') is null
      or crypt(
        trim(p_access_code),
        selected_consultant.own_shop_access_code_hash
      ) <> selected_consultant.own_shop_access_code_hash
    )
  then
    raise exception 'Tilgangskoden er ikke riktig.';
  end if;

  insert into public.order_requests (
    consultant_id,
    customer_name,
    customer_email,
    customer_phone,
    customer_message,
    order_source
  )
  values (
    selected_consultant.id,
    customer_name,
    customer_email,
    customer_phone,
    customer_message,
    'consultant_inventory'
  )
  returning id into new_order_id;

  for item in select * from jsonb_array_elements(p_items)
  loop
    requested_quantity := greatest(
      1,
      least(99, coalesce((item->>'quantity')::integer, 1))
    );

    select *
    into selected_inventory
    from public.inventory
    where id = (item->>'inventory_id')::uuid
      and consultant_id = selected_consultant.id
      and is_active = true
      and is_for_sale = true
      and quantity >= requested_quantity
      and sale_price_nok is not null;

    if not found then
      raise exception 'En vare er utsolgt eller tilhører ikke denne konsulenten.';
    end if;

    insert into public.order_items (
      order_request_id,
      inventory_item_id,
      product_handle,
      article_number,
      product_name,
      quantity,
      observed_price_nok
    )
    values (
      new_order_id,
      selected_inventory.id,
      selected_inventory.product_handle,
      selected_inventory.article_number,
      selected_inventory.product_name,
      requested_quantity,
      selected_inventory.sale_price_nok
    );
  end loop;

  return new_order_id;
end;
$$;

revoke all on function public.submit_consultant_inventory_order(
  text,
  jsonb,
  jsonb,
  text
) from public;
grant execute on function public.submit_consultant_inventory_order(
  text,
  jsonb,
  jsonb,
  text
) to anon, authenticated;
