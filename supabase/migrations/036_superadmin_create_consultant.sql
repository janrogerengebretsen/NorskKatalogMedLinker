create or replace function public.superadmin_create_consultant(
  p_reference_code text,
  p_display_name text,
  p_email text,
  p_phone text
)
returns table (
  id uuid,
  reference_code text,
  display_name text,
  email text,
  phone text
)
language plpgsql
security definer
set search_path = public
as $$
declare
  created_id uuid;
  cleaned_reference text := upper(regexp_replace(trim(coalesce(p_reference_code, '')), '[^A-Za-z0-9_-]', '', 'g'));
  cleaned_name text := trim(coalesce(p_display_name, ''));
  cleaned_email text := lower(trim(coalesce(p_email, '')));
  cleaned_phone text := trim(coalesce(p_phone, ''));
begin
  if not public.is_super_admin() then
    raise exception 'Bare superadministrator kan opprette konsulenter.';
  end if;
  if char_length(cleaned_reference) < 2 or char_length(cleaned_reference) > 80 then
    raise exception 'Referansen må inneholde mellom 2 og 80 tegn.';
  end if;
  if char_length(cleaned_name) < 2 or char_length(cleaned_name) > 120 then
    raise exception 'Navnet må inneholde mellom 2 og 120 tegn.';
  end if;
  if cleaned_email !~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$' then
    raise exception 'E-postadressen er ikke gyldig.';
  end if;
  if char_length(cleaned_phone) < 5 or char_length(cleaned_phone) > 40 then
    raise exception 'Mobilnummeret er ikke gyldig.';
  end if;
  if exists (select 1 from public.consultants c where c.reference_code = cleaned_reference) then
    raise exception 'En konsulent med denne referansen finnes allerede.';
  end if;

  insert into public.consultants (
    reference_code, display_name, email, phone, catalog_slug,
    status, public_listing, show_email, show_phone,
    verified_at, consented_at, updated_at
  ) values (
    cleaned_reference, cleaned_name, cleaned_email, cleaned_phone,
    lower(cleaned_reference), 'active', true, true, true,
    now(), now(), now()
  ) returning consultants.id into created_id;

  insert into public.consultant_product_access (
    consultant_id, product_key, is_active, granted_at, updated_at
  ) values
    (created_id, 'maanedstilbud', true, now(), now()),
    (created_id, 'tw-host-vinter-2026-27', true, now(), now())
  on conflict on constraint consultant_product_access_pkey do update
    set is_active = true, updated_at = now();

  insert into public.audit_log (actor_user_id, entity_type, entity_id, action, details)
  values (
    auth.uid(), 'consultant', created_id::text, 'superadmin_create_consultant',
    jsonb_build_object('reference_code', cleaned_reference)
  );

  return query
  select c.id, c.reference_code, c.display_name, c.email, c.phone
  from public.consultants c
  where c.id = created_id;
end;
$$;

revoke all on function public.superadmin_create_consultant(text, text, text, text) from public;
grant execute on function public.superadmin_create_consultant(text, text, text, text) to authenticated;
