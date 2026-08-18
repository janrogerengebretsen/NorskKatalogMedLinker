create or replace function public.public_consultant_contact(p_reference_code text)
returns table (
  email text,
  phone text
)
language sql
stable
security definer
set search_path = public
as $$
  select consultants.email, consultants.phone
  from public.consultants
  where consultants.reference_code = upper(trim(p_reference_code))
    and consultants.status = 'active'
    and consultants.public_listing = true
  limit 1;
$$;

grant execute on function public.public_consultant_contact(text) to anon, authenticated;
