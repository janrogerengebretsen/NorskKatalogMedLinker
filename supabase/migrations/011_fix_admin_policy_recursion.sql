-- Avoid recursive RLS evaluation when checking administrator membership.
create or replace function public.is_admin()
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
    where user_id = auth.uid()
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

revoke all on function public.is_admin() from public;
revoke all on function public.is_super_admin() from public;
grant execute on function public.is_admin() to authenticated;
grant execute on function public.is_super_admin() to authenticated;

drop policy if exists "Admins read admin list" on public.admin_users;
drop policy if exists "Super admins manage admin list" on public.admin_users;

create policy "Admins read admin list"
on public.admin_users for select
to authenticated
using (public.is_admin());

create policy "Super admins manage admin list"
on public.admin_users for all
to authenticated
using (public.is_super_admin())
with check (public.is_super_admin());
