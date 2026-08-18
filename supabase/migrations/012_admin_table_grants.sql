-- RLS decides which authenticated users may use these privileges.
grant select, insert, update, delete on public.consultants to authenticated;
grant select, insert, update, delete on public.admin_users to authenticated;
