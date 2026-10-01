create or replace function public.superadmin_update_consultant(
  p_reference_code text,
  p_display_name text,
  p_email text default null,
  p_phone text default null
)
returns table (
  display_name text,
  email text,
  phone text
)
language plpgsql
security definer
set search_path = public
as $$
declare
  target_id uuid;
  cleaned_name text := trim(coalesce(p_display_name, ''));
  cleaned_email text := nullif(lower(trim(coalesce(p_email, ''))), '');
  cleaned_phone text := nullif(trim(coalesce(p_phone, '')), '');
begin
  if not public.is_super_admin() then
    raise exception 'Bare superadministrator kan endre konsulentopplysninger.';
  end if;
  if char_length(cleaned_name) < 2 or char_length(cleaned_name) > 120 then
    raise exception 'Navnet må inneholde mellom 2 og 120 tegn.';
  end if;
  if cleaned_email is not null and cleaned_email !~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$' then
    raise exception 'E-postadressen er ikke gyldig.';
  end if;
  if cleaned_phone is not null and char_length(cleaned_phone) > 40 then
    raise exception 'Telefonnummeret er for langt.';
  end if;

  update public.consultants
  set display_name = cleaned_name,
      email = cleaned_email,
      phone = cleaned_phone,
      updated_at = now()
  where reference_code = upper(trim(p_reference_code))
  returning id into target_id;

  if target_id is null then
    raise exception 'Fant ikke konsulenten.';
  end if;

  insert into public.audit_log (actor_user_id, entity_type, entity_id, action, details)
  values (
    auth.uid(), 'consultant', target_id::text, 'superadmin_update_contact',
    jsonb_build_object('reference_code', upper(trim(p_reference_code)))
  );

  return query
  select c.display_name, c.email, c.phone
  from public.consultants c
  where c.id = target_id;
end;
$$;

revoke all on function public.superadmin_update_consultant(text, text, text, text) from public;
grant execute on function public.superadmin_update_consultant(text, text, text, text) to authenticated;
