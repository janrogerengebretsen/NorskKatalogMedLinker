create table if not exists public.consultant_product_payments (
  id uuid primary key default gen_random_uuid(),
  consultant_id uuid not null references public.consultants(id) on delete restrict,
  product_key text not null references public.products(product_key) on delete restrict,
  amount_nok numeric(12, 2) not null default 0 check (amount_nok >= 0),
  payment_status text not null default 'paid'
    check (payment_status in ('paid', 'gift', 'unpaid', 'refunded')),
  paid_at date not null default current_date,
  note text,
  source_key text unique,
  created_by uuid references auth.users(id) on delete set null default auth.uid(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists consultant_product_payments_paid_at_idx
  on public.consultant_product_payments (paid_at desc);
create index if not exists consultant_product_payments_consultant_idx
  on public.consultant_product_payments (consultant_id, paid_at desc);

alter table public.consultant_product_payments enable row level security;

drop policy if exists "Superadmins manage product payments" on public.consultant_product_payments;
create policy "Superadmins manage product payments"
on public.consultant_product_payments for all to authenticated
using (public.is_super_admin())
with check (public.is_super_admin());

grant select, insert, update, delete on public.consultant_product_payments to authenticated;
