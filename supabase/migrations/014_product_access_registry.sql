create table if not exists public.products (
  product_key text primary key check (product_key ~ '^[a-z0-9-]{3,80}$'),
  title text not null,
  description text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.consultant_product_access (
  consultant_id uuid not null references public.consultants(id) on delete cascade,
  product_key text not null references public.products(product_key) on delete cascade,
  is_active boolean not null default true,
  granted_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (consultant_id, product_key)
);

insert into public.products (product_key, title, description)
values
  ('norsk-nettkatalog', 'Norsk Nettkatalog', 'Den norske nettkatalogen med produkter fra Tupperwares nettbutikk.'),
  ('norsk-produktkatalog', 'Norsk produktkatalog', 'Den digitale produktkatalogen som bygger på PDF-katalogen.'),
  ('egne-varer', 'Egne varer', 'Konsulentens egen varekatalog, lagerstyring og bestillingsmottak.')
on conflict (product_key) do update
set title = excluded.title, description = excluded.description,
    is_active = true, updated_at = now();

insert into public.consultant_product_access (consultant_id, product_key)
select id, 'norsk-produktkatalog' from public.consultants where status = 'active'
on conflict (consultant_id, product_key) do update set is_active = true, updated_at = now();

insert into public.consultant_product_access (consultant_id, product_key)
select id, 'norsk-nettkatalog' from public.consultants
where reference_code in ('LISBETHOVERBYE', 'VIVIANKONGSVOLD')
on conflict (consultant_id, product_key) do update set is_active = true, updated_at = now();

-- Existing enabled shops keep their access when the paid product is introduced.
insert into public.consultant_product_access (consultant_id, product_key)
select id, 'egne-varer' from public.consultants where own_shop_enabled = true
on conflict (consultant_id, product_key) do update set is_active = true, updated_at = now();

alter table public.products enable row level security;
alter table public.consultant_product_access enable row level security;

drop policy if exists "Everyone reads active products" on public.products;
create policy "Everyone reads active products" on public.products for select
using (is_active = true);

drop policy if exists "Admins manage products" on public.products;
create policy "Admins manage products" on public.products for all to authenticated
using (public.is_admin()) with check (public.is_admin());

drop policy if exists "Consultants read own product access" on public.consultant_product_access;
create policy "Consultants read own product access"
on public.consultant_product_access for select to authenticated
using (public.owns_consultant(consultant_id) or public.is_admin());

drop policy if exists "Admins manage product access" on public.consultant_product_access;
create policy "Admins manage product access"
on public.consultant_product_access for all to authenticated
using (public.is_admin()) with check (public.is_admin());

grant select on public.products to anon, authenticated;
grant select, insert, update, delete on public.products to authenticated;
grant select, insert, update, delete on public.consultant_product_access to authenticated;

create or replace function public.consultant_product_access_list(p_reference_code text)
returns table (product_key text)
language sql stable security definer set search_path = public
as $$
  select access.product_key
  from public.consultant_product_access access
  join public.consultants on consultants.id = access.consultant_id
  join public.products on products.product_key = access.product_key
  where consultants.reference_code = upper(trim(p_reference_code))
    and consultants.status = 'active' and consultants.public_listing = true
    and access.is_active = true and products.is_active = true
  order by access.product_key;
$$;

revoke all on function public.consultant_product_access_list(text) from public;
grant execute on function public.consultant_product_access_list(text) to anon, authenticated;

create or replace function public.my_product_access()
returns table (product_key text)
language sql stable security definer set search_path = public
as $$
  select access.product_key
  from public.consultant_product_access access
  join public.consultants on consultants.id = access.consultant_id
  join public.products on products.product_key = access.product_key
  where consultants.user_id = auth.uid()
    and access.is_active = true and products.is_active = true
  order by access.product_key;
$$;

revoke all on function public.my_product_access() from public;
grant execute on function public.my_product_access() to authenticated;

create or replace function public.update_my_consultant_shop_settings(
  p_enabled boolean, p_access_mode text, p_new_access_code text default null
)
returns table (
  own_shop_enabled boolean,
  own_shop_access_mode text,
  own_shop_has_access_code boolean
)
language plpgsql security definer set search_path = public, extensions
as $$
declare
  current_consultant public.consultants%rowtype;
  cleaned_code text;
  has_shop_access boolean;
begin
  if auth.uid() is null then raise exception 'Du må være logget inn.'; end if;
  if p_access_mode not in ('public', 'code') then raise exception 'Ugyldig tilgangsvalg.'; end if;

  cleaned_code := nullif(trim(p_new_access_code), '');
  if cleaned_code is not null and (char_length(cleaned_code) < 4 or char_length(cleaned_code) > 40)
  then raise exception 'Kundekoden må inneholde mellom 4 og 40 tegn.'; end if;

  select * into current_consultant from public.consultants where user_id = auth.uid();
  if not found then raise exception 'Fant ikke konsulentprofilen.'; end if;

  select exists (
    select 1 from public.consultant_product_access access
    where access.consultant_id = current_consultant.id
      and access.product_key = 'egne-varer' and access.is_active = true
  ) into has_shop_access;

  if p_enabled and not has_shop_access then
    raise exception 'Egne varer er et tilleggsprodukt. Kontakt administrator for å kjøpe tilgang.';
  end if;
  if p_enabled and p_access_mode = 'code' and cleaned_code is null
    and current_consultant.own_shop_access_code_hash is null
  then raise exception 'Velg en kundekode før kodebeskyttelsen aktiveres.'; end if;

  return query update public.consultants set
    own_shop_enabled = p_enabled and has_shop_access,
    own_shop_access_mode = p_access_mode,
    own_shop_access_code_hash = case
      when cleaned_code is not null then crypt(cleaned_code, gen_salt('bf'))
      else consultants.own_shop_access_code_hash end,
    updated_at = now()
  where user_id = auth.uid()
  returning consultants.own_shop_enabled, consultants.own_shop_access_mode,
    consultants.own_shop_access_code_hash is not null;
end;
$$;

revoke all on function public.update_my_consultant_shop_settings(boolean, text, text) from public;
grant execute on function public.update_my_consultant_shop_settings(boolean, text, text) to authenticated;
