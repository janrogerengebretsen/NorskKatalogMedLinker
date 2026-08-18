create extension if not exists pgcrypto;

create type public.consultant_status as enum (
  'pending',
  'active',
  'inactive',
  'rejected'
);

create type public.subscription_plan as enum (
  'free',
  'catalog',
  'shop'
);

create type public.subscription_status as enum (
  'trial',
  'active',
  'past_due',
  'cancelled'
);

create type public.order_status as enum (
  'new',
  'contacted',
  'completed',
  'cancelled'
);

create table public.consultants (
  id uuid primary key default gen_random_uuid(),
  user_id uuid unique references auth.users(id) on delete set null,
  reference_code text not null unique
    check (reference_code ~ '^[A-Z0-9_-]{1,80}$'),
  display_name text not null,
  email text,
  phone text,
  municipality text,
  county text,
  profile_image_url text,
  catalog_slug text not null unique
    check (catalog_slug ~ '^[a-z0-9-]{3,80}$'),
  status public.consultant_status not null default 'pending',
  public_listing boolean not null default false,
  show_email boolean not null default false,
  show_phone boolean not null default false,
  consented_at timestamptz,
  verified_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (not public_listing or consented_at is not null)
);

create table public.admin_users (
  user_id uuid primary key references auth.users(id) on delete cascade,
  is_super_admin boolean not null default false,
  created_at timestamptz not null default now()
);

create table public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  consultant_id uuid not null references public.consultants(id) on delete cascade,
  plan public.subscription_plan not null default 'free',
  status public.subscription_status not null default 'active',
  starts_at timestamptz not null default now(),
  ends_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index subscriptions_one_current
  on public.subscriptions (consultant_id)
  where ends_at is null;

create table public.inventory (
  id uuid primary key default gen_random_uuid(),
  consultant_id uuid not null references public.consultants(id) on delete cascade,
  product_handle text not null,
  article_number text,
  quantity integer not null default 0 check (quantity >= 0),
  note text,
  updated_at timestamptz not null default now(),
  unique (consultant_id, product_handle)
);

create table public.price_history (
  id bigint generated always as identity primary key,
  product_handle text not null,
  article_number text,
  price_nok numeric(12, 2) not null check (price_nok >= 0),
  compare_at_price_nok numeric(12, 2)
    check (compare_at_price_nok is null or compare_at_price_nok >= 0),
  available boolean not null,
  observed_at timestamptz not null default now(),
  source_url text not null
);

create index price_history_product_time
  on public.price_history (product_handle, observed_at desc);

create table public.order_requests (
  id uuid primary key default gen_random_uuid(),
  consultant_id uuid not null references public.consultants(id) on delete restrict,
  customer_name text not null,
  customer_email text,
  customer_phone text,
  customer_message text,
  status public.order_status not null default 'new',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (customer_email is not null or customer_phone is not null)
);

create table public.order_items (
  id uuid primary key default gen_random_uuid(),
  order_request_id uuid not null
    references public.order_requests(id) on delete cascade,
  product_handle text not null,
  article_number text,
  product_name text not null,
  quantity integer not null default 1 check (quantity > 0),
  observed_price_nok numeric(12, 2) check (observed_price_nok >= 0)
);

create table public.audit_log (
  id bigint generated always as identity primary key,
  actor_user_id uuid references auth.users(id) on delete set null,
  entity_type text not null,
  entity_id text not null,
  action text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
set row_security = off
as $$
  select exists (
    select 1 from public.admin_users where user_id = auth.uid()
  );
$$;

create or replace function public.is_super_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
set row_security = off
as $$
  select exists (
    select 1
    from public.admin_users
    where user_id = auth.uid() and is_super_admin = true
  );
$$;

create or replace function public.owns_consultant(target_consultant_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.consultants
    where id = target_consultant_id and user_id = auth.uid()
  );
$$;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger consultants_set_updated_at
before update on public.consultants
for each row execute function public.set_updated_at();

create trigger subscriptions_set_updated_at
before update on public.subscriptions
for each row execute function public.set_updated_at();

create trigger inventory_set_updated_at
before update on public.inventory
for each row execute function public.set_updated_at();

create trigger order_requests_set_updated_at
before update on public.order_requests
for each row execute function public.set_updated_at();

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

alter table public.consultants enable row level security;
alter table public.admin_users enable row level security;
alter table public.subscriptions enable row level security;
alter table public.inventory enable row level security;
alter table public.price_history enable row level security;
alter table public.order_requests enable row level security;
alter table public.order_items enable row level security;
alter table public.audit_log enable row level security;

create policy "Public can read approved consultants"
on public.consultants for select
using (status = 'active' and public_listing = true);

create policy "Consultants can read own profile"
on public.consultants for select
to authenticated
using (user_id = auth.uid() or public.is_admin());

create policy "Consultants can update own profile"
on public.consultants for update
to authenticated
using (user_id = auth.uid())
with check (user_id = auth.uid());

create policy "Admins manage consultants"
on public.consultants for all
to authenticated
using (public.is_admin())
with check (public.is_admin());

create policy "Admins read admin list"
on public.admin_users for select
to authenticated
using (public.is_admin());

create policy "Super admins manage admin list"
on public.admin_users for all
to authenticated
using (public.is_super_admin())
with check (public.is_super_admin());

create policy "Consultants read own subscriptions"
on public.subscriptions for select
to authenticated
using (public.owns_consultant(consultant_id) or public.is_admin());

create policy "Admins manage subscriptions"
on public.subscriptions for all
to authenticated
using (public.is_admin())
with check (public.is_admin());

create policy "Consultants manage own inventory"
on public.inventory for all
to authenticated
using (public.owns_consultant(consultant_id) or public.is_admin())
with check (public.owns_consultant(consultant_id) or public.is_admin());

create policy "Public can read available inventory"
on public.inventory for select
using (
  quantity > 0
  and exists (
    select 1 from public.consultants
    where id = consultant_id
      and status = 'active'
      and public_listing = true
  )
);

create policy "Public can read price history"
on public.price_history for select
using (true);

create policy "Admins manage price history"
on public.price_history for all
to authenticated
using (public.is_admin())
with check (public.is_admin());

create policy "Consultants read own order requests"
on public.order_requests for select
to authenticated
using (public.owns_consultant(consultant_id) or public.is_admin());

create policy "Consultants update own order requests"
on public.order_requests for update
to authenticated
using (public.owns_consultant(consultant_id) or public.is_admin())
with check (public.owns_consultant(consultant_id) or public.is_admin());

create policy "Consultants read own order items"
on public.order_items for select
to authenticated
using (
  exists (
    select 1 from public.order_requests request
    where request.id = order_request_id
      and (
        public.owns_consultant(request.consultant_id)
        or public.is_admin()
      )
  )
);

create policy "Admins read audit log"
on public.audit_log for select
to authenticated
using (public.is_admin());

revoke update on public.consultants from authenticated;
grant update (
  display_name,
  email,
  phone,
  municipality,
  county,
  profile_image_url,
  public_listing,
  show_email,
  show_phone,
  consented_at
) on public.consultants to authenticated;

grant select on public.public_consultants to anon, authenticated;
grant select, insert, update, delete on public.consultants to authenticated;
grant select, insert, update, delete on public.admin_users to authenticated;
