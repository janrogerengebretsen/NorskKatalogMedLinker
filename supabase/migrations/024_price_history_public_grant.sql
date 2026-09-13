grant select on public.price_history to anon, authenticated;

drop policy if exists "Public can read price history" on public.price_history;
create policy "Public can read price history"
on public.price_history for select
using (true);
