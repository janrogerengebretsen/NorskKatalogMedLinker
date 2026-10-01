const params = new URLSearchParams(window.location.search);
const adminMode = params.get("admin") === "1";

function cleanReference(value) {
  return String(value || "").trim().replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 80);
}

function storedReference() {
  try {
    return cleanReference(localStorage.getItem("tupperwareConsultantRef"));
  } catch {
    return "";
  }
}

// A consultant is selected only through the explicit ref in the shared URL.
const referenceCode = cleanReference(params.get("ref"));
const shareUrls = {
  store: new URL(`/no/?ref=${encodeURIComponent(referenceCode)}&country=NO`, "https://tupperware-eu.com").toString(),
  official: new URL(`/?ref=${encodeURIComponent(referenceCode)}`, window.location.origin).toString(),
  digital: new URL(`/digital-katalog?ref=${encodeURIComponent(referenceCode)}`, window.location.origin).toString(),
  september: new URL(`/siste-maanedstilbud?ref=${encodeURIComponent(referenceCode)}`, window.location.origin).toString(),
  winter: new URL(`/tw-host-vinter-2026-27?ref=${encodeURIComponent(referenceCode)}`, window.location.origin).toString(),
  own: new URL(`/egne-varer?ref=${encodeURIComponent(referenceCode)}`, window.location.origin).toString(),
  party: new URL(`/party?ref=${encodeURIComponent(referenceCode)}`, window.location.origin).toString(),
};
const shareDetails = {
  store: {
    title: "Handle hos din Tupperware-konsulent",
    text: "Åpne Tupperwares norske nettbutikk med konsulentens personlige referanse.",
    filename: "konsulentens-tupperware-side",
  },
  official: {
    title: "Velkommen til Tupperware Norsk Nettkatalog",
    text: "Se Tupperwares produkter og finn dine favoritter.",
    filename: "tupperware-nettkatalog",
  },
  digital: {
    title: "Velkommen til den digitale produktkatalogen",
    text: "Bla i katalogheftet og åpne personlige produktlenker.",
    filename: "digital-produktkatalog",
  },
  september: {
    title: "Velkommen til månedens tilbud",
    text: "Se den nyeste månedskatalogen med personlige produktlenker.",
    filename: "siste-maanedstilbud",
  },
  winter: {
    title: "Tupperware høst/vinter 2026-2027",
    text: "Bla i den nye sesongkatalogen og åpne personlige produktlenker.",
    filename: "tw-host-vinter-2026-2027",
  },
  own: {
    title: "Velkommen til konsulentens egne varer",
    text: "Se produkter som er tilgjengelige fra konsulentens eget lager.",
    filename: "egne-varer",
  },
  party: {
    title: "Velkommen til party",
    text: "Bli med på party, se fokusprodukter og send bestilling til konsulenten.",
    filename: "party",
  },
};
const productRegister = [
  {
    key: "norsk-nettkatalog",
    title: "Norsk Nettkatalog",
    description: "Den norske nettkatalogen med produkter fra Tupperwares nettbutikk.",
    accessLabel: "Kjøpes separat",
    accessType: "entitlement",
  },
  {
    key: "norsk-produktkatalog",
    title: "Digital Produktkatalog",
    description: "Den digitale produktkatalogen som bygger på PDF-katalogen.",
    accessLabel: "Kjøpes separat",
    accessType: "entitlement",
  },
  {
    key: "egne-varer",
    title: "Egne varer",
    description: "Egen varekatalog, lagerstyring og bestillinger direkte til konsulenten.",
    accessLabel: "Tilleggsprodukt - kjøpes separat",
    accessType: "entitlement",
  },
  {
    key: "party",
    title: "Party",
    description: "Digital og fysisk party-lÃ¸sning med pÃ¥melding, fokusprodukter og bestillinger.",
    accessLabel: "Tilleggsprodukt - kjÃ¸pes separat",
    accessType: "entitlement",
  },
  {
    key: "maanedstilbud",
    title: "Månedens tilbudskatalog",
    description: "Abonnement på den nyeste månedskatalogen med aktuelle tilbud.",
    accessLabel: "Abonnement",
    accessType: "entitlement",
  },
  {
    key: "tw-host-vinter-2026-27",
    title: "TWHøstVinter202627",
    description: "Digital høst- og vinterkatalog 2026-2027 med personlige produktlenker.",
    accessLabel: "Abonnement",
    accessType: "entitlement",
  },
];
let consultantName = referenceCode;
let consultantProfile = null;
let toastTimer;
const adminState = {
  config: null,
  session: null,
  consultants: [],
  filtered: [],
  productAccess: [],
  payments: [],
};

const adminProductLinks = {
  "norsk-nettkatalog": reference => new URL(`/?ref=${encodeURIComponent(reference)}`, window.location.origin).toString(),
  "norsk-produktkatalog": reference => new URL(`/digital-katalog?ref=${encodeURIComponent(reference)}`, window.location.origin).toString(),
  "egne-varer": reference => new URL(`/egne-varer?ref=${encodeURIComponent(reference)}`, window.location.origin).toString(),
  party: reference => new URL(`/party?ref=${encodeURIComponent(reference)}`, window.location.origin).toString(),
  maanedstilbud: reference => new URL(`/siste-maanedstilbud?ref=${encodeURIComponent(reference)}`, window.location.origin).toString(),
  "tw-host-vinter-2026-27": reference => new URL(`/tw-host-vinter-2026-27?ref=${encodeURIComponent(reference)}`, window.location.origin).toString(),
};

function selectedAdminConsultant() {
  const reference = document.querySelector("#adminConsultantSelect")?.value;
  return adminState.consultants.find(item => item.reference_code === reference) || null;
}

function adminMailContent(consultant) {
  const mailCatalogs = [
    { key: "maanedstilbud", title: "Siste månedskatalog" },
    { key: "tw-host-vinter-2026-27", title: "Høst- og vinterkatalog 2026/2027" },
  ];
  const links = mailCatalogs
    .filter(product => consultant.product_access.has(product.key))
    .map(product => `${product.title}\n${adminProductLinks[product.key](consultant.reference_code)}`)
    .join("\n\n");
  const firstName = consultant.display_name.trim().split(/\s+/)[0] || consultant.display_name;
  return {
    subject: "Dine digitale Tupperware-kataloger",
    body: `Hei ${firstName}!\n\nHer er de digitale Tupperware-katalogene dine:\n\n${links || "Du har foreløpig ingen av disse katalogene aktive."}\n\nLenkene inneholder din personlige konsulentreferanse og kan deles direkte med kundene dine.\n\nSLIK BRUKES KATALOGENE\n\nKunden blar i katalogen og klikker på et produkt for å åpne det i Tupperwares nettbutikk. Kunden kan gå frem og tilbake mellom katalogen og nettbutikken, legge flere produkter i handlekurven og sende inn én samlet bestilling til slutt.\n\nBestilling og betaling gjennomføres direkte i Tupperwares nettbutikk. Det er alltid pris og lagerstatus i nettbutikken som gjelder. Varene sendes normalt hjem til kunden innen 7–10 dager.\n\nKatalogene fungerer på mobil, nettbrett og PC. Dersom katalogen åpnes inne i Messenger eller Facebook, bør kunden kopiere lenken, åpne Google Chrome og lime lenken inn i adressefeltet.\n\nHele katalogen eller utvalgte sider kan også skrives ut eller lagres som PDF.\n\nPERSONLIG KONTAKTSIDE\n\nPå den siste siden i katalogen vises konsulentens navn, telefonnummer og e-postadresse. Der finnes også QR-koder og lenker til konsulentens side hos Tupperware og den digitale katalogen. Den siste siden kan derfor brukes som kontaktark eller skrives ut sammen med utvalgte katalogsider.\n\nJeg bruker nå Gmail-adressen jan.roger.engebretsen@gmail.com. Bruk gjerne denne adressen dersom du oppdager feil eller har spørsmål.\n\nVennlig hilsen\nJan Roger Engebretsen\njan.roger.engebretsen@gmail.com`,
  };
}

function renderAdminMail(consultant) {
  const recipient = document.querySelector("#adminMailRecipient");
  const disabled = !consultant || !consultant.email;
  document.querySelector("#adminCopyMail").disabled = disabled;
  document.querySelector("#adminOpenGmail").disabled = disabled;
  recipient.textContent = !consultant
    ? "Velg en konsulent først."
    : consultant.email
      ? `Til: ${consultant.display_name} <${consultant.email}>`
      : `${consultant.display_name} mangler e-postadresse.`;
}

function paymentStatusLabel(status) {
  return { paid: "Betalt", gift: "Gave", unpaid: "Ikke betalt", refunded: "Tilbakebetalt" }[status] || status;
}

function formatNok(value) {
  return new Intl.NumberFormat("nb-NO", { style: "currency", currency: "NOK", maximumFractionDigits: 0 }).format(Number(value || 0));
}

async function loadAdminAccounting() {
  const month = document.querySelector("#adminAccountingMonth").value;
  if (!month) return;
  const start = `${month}-01`;
  const next = new Date(`${start}T12:00:00`);
  next.setMonth(next.getMonth() + 1);
  const end = next.toISOString().slice(0, 10);
  try {
    adminState.payments = await jsonRequest(
      `${adminState.config.supabaseUrl}/rest/v1/consultant_product_payments?select=id,consultant_id,product_key,amount_nok,payment_status,paid_at,note&paid_at=gte.${start}&paid_at=lt.${end}&order=paid_at.desc,created_at.desc`,
      { headers: adminHeaders() },
    );
    renderAdminAccounting();
  } catch (error) {
    document.querySelector("#adminAccountingSummary").innerHTML = `<p class="admin-product-empty">Regnskapstabellen må opprettes i Supabase før oversikten kan brukes.</p>`;
    document.querySelector("#adminAccountingRows").replaceChildren();
  }
}

function renderAdminAccounting() {
  const paid = adminState.payments.filter(item => item.payment_status === "paid");
  const refunded = adminState.payments.filter(item => item.payment_status === "refunded");
  const revenue = paid.reduce((sum, item) => sum + Number(item.amount_nok), 0)
    - refunded.reduce((sum, item) => sum + Number(item.amount_nok), 0);
  const count = status => adminState.payments.filter(item => item.payment_status === status).length;
  document.querySelector("#adminAccountingSummary").innerHTML = `
    <div class="admin-accounting-card"><span>Omsetning</span><strong>${formatNok(revenue)}</strong></div>
    <div class="admin-accounting-card"><span>Betalt</span><strong>${count("paid")}</strong></div>
    <div class="admin-accounting-card"><span>Gaver</span><strong>${count("gift")}</strong></div>
    <div class="admin-accounting-card"><span>Ikke betalt</span><strong>${count("unpaid")}</strong></div>`;
  const body = document.querySelector("#adminAccountingRows");
  body.replaceChildren(...adminState.payments.map(payment => {
    const consultant = adminState.consultants.find(item => item.id === payment.consultant_id);
    const product = productRegister.find(item => item.key === payment.product_key);
    const row = document.createElement("tr");
    row.innerHTML = `<td>${payment.paid_at}</td><td>${consultant?.display_name || "Ukjent"}</td><td>${product?.title || payment.product_key}</td><td>${paymentStatusLabel(payment.payment_status)}</td><td>${formatNok(payment.amount_nok)}</td>`;
    return row;
  }));
  if (!adminState.payments.length) {
    const row = document.createElement("tr");
    row.innerHTML = `<td colspan="5">Ingen registreringer denne måneden.</td>`;
    body.append(row);
  }
}

function showToast(message) {
  const toast = document.querySelector("#hubToast");
  toast.textContent = message;
  toast.classList.add("visible");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("visible"), 2600);
}

async function jsonRequest(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error_description || payload.message || payload.error || "Noe gikk galt");
  }
  return payload;
}

function adminHeaders(extra = {}) {
  return {
    apikey: adminState.config.supabaseAnonKey,
    Authorization: `Bearer ${adminState.session.access_token}`,
    "Content-Type": "application/json",
    ...extra,
  };
}

function saveAdminSession(session) {
  adminState.session = session;
  try {
    sessionStorage.setItem("consultantManageSession", JSON.stringify(session));
  } catch {
    // Innloggingen virker fortsatt frem til fanen lukkes.
  }
}

function restoredAdminSession() {
  try {
    const session = JSON.parse(sessionStorage.getItem("consultantManageSession") || "null");
    if (session?.access_token && session?.user?.id) return session;
  } catch {
    return null;
  }
  return null;
}

function clearAdminSession() {
  adminState.session = null;
  try {
    sessionStorage.removeItem("consultantManageSession");
  } catch {
    // Det er nok å tømme minnet hvis nettleserlagring er utilgjengelig.
  }
}

function consultantLabel(consultant) {
  const status = consultant.status === "active" ? "Aktiv" : "Ikke aktiv";
  return `${consultant.display_name} (${consultantLinkUseCount(consultant)}) - ${consultant.reference_code} - ${status}`;
}

function consultantLinkUseCount(consultant) {
  const counts = Object.values(consultant?.catalog_counts || {});
  return counts.length
    ? counts.reduce((total, count) => total + Number(count || 0), 0)
    : Number(consultant?.link_use_count || 0);
}

function consultantCatalogUseCount(consultant, productKey) {
  if (productKey === "maanedstilbud") {
    return Object.entries(consultant?.catalog_counts || {})
      .filter(([key]) => /^\w+-20\d{2}$/.test(key))
      .reduce((total, [, count]) => total + Number(count || 0), 0);
  }
  return Number(consultant?.catalog_counts?.[productKey] || 0);
}

const catalogCountLabels = {
  "norsk-nettkatalog": "Norsk nettkatalog",
  "norsk-produktkatalog": "Digital produktkatalog",
  "september-2026": "September 2026",
  "oktober-2026": "Oktober 2026",
  "tw-host-vinter-2026-27": "Høst/vinter 2026–27",
};

function consultantCatalogBreakdown(consultant) {
  const rows = Object.entries(consultant?.catalog_counts || {})
    .filter(([, count]) => Number(count) > 0)
    .map(([key, count]) => `${catalogCountLabels[key] || key}: ${Number(count)}`);
  return rows.length
    ? `<small class="admin-catalog-breakdown">${rows.join("<br>")}</small>`
    : `<small class="admin-catalog-breakdown">Ingen registrerte katalogåpninger</small>`;
}

function renderAdminConsultants(search = "") {
  const normalized = search.trim().toLocaleLowerCase("nb-NO");
  adminState.filtered = adminState.consultants.filter(consultant => {
    const haystack = [
      consultant.display_name,
      consultant.reference_code,
      consultant.municipality,
      consultant.county,
      consultant.status,
    ].filter(Boolean).join(" ").toLocaleLowerCase("nb-NO");
    return !normalized || haystack.includes(normalized);
  });

  const select = document.querySelector("#adminConsultantSelect");
  const emptyOption = new Option("Ingen konsulent valgt", "");
  emptyOption.selected = !referenceCode;
  select.replaceChildren(
    emptyOption,
    ...adminState.filtered.map(consultant => (
      new Option(consultantLabel(consultant), consultant.reference_code)
    )),
  );
  const current = adminState.filtered.find(consultant => consultant.reference_code === referenceCode);
  if (current) select.value = referenceCode;
  document.querySelector("#adminResultCount").textContent = `${adminState.filtered.length} konsulenter`;
  document.querySelector("#adminOpenConsultant").disabled = !adminState.filtered.length;
  document.querySelector("#adminPrevious").disabled = !adminState.filtered.length;
  document.querySelector("#adminNext").disabled = !adminState.filtered.length;
  updateAdminCurrent();
  renderAdminOverview();
}

function renderAdminOverview() {
  const head = document.querySelector("#adminConsultantOverviewHead");
  const body = document.querySelector("#adminConsultantOverview");
  if (!head || !body) return;
  const overviewProducts = [
    { key: "maanedstilbud", label: "Måned", title: "Månedens tilbudskatalog" },
    { key: "tw-host-vinter-2026-27", label: "Høst/vinter", title: "Høst- og vinterkatalog 2026/2027" },
    { key: "norsk-nettkatalog", label: "Nett", title: "Norsk Nettkatalog" },
    { key: "norsk-produktkatalog", label: "PDF", title: "Digital Produktkatalog" },
    { key: "egne-varer", label: "Egne", title: "Egne varer" },
    { key: "party", label: "Party", title: "Party" },
  ];
  head.innerHTML = `<tr><th class="admin-consultant-column">Konsulent / ref.</th><th class="admin-total-column" title="Totalt antall katalogåpninger">Totalt</th>${overviewProducts.map(product => `<th class="admin-product-column" title="${product.title}">${product.label}</th>`).join("")}</tr>`;
  body.replaceChildren(...adminState.consultants.map(consultant => {
    const row = document.createElement("tr");
    const accessCells = overviewProducts.map(product => {
      const active = consultant.product_access.has(product.key);
      const opens = consultantCatalogUseCount(consultant, product.key);
      return `<td><div class="admin-access-cell"><button type="button" class="admin-access-toggle ${active ? "is-active" : ""}" data-overview-access="${product.key}" data-access-consultant="${consultant.reference_code}" title="${active ? "Fjern tilgang" : "Gi tilgang"}" aria-label="${active ? "Fjern tilgang" : "Gi tilgang"}"><i data-lucide="${active ? "check-circle-2" : "ban"}"></i></button><span class="admin-open-count" title="Antall katalogåpninger">${opens}</span></div></td>`;
    }).join("");
    row.innerHTML = `<td class="admin-consultant-column"><button type="button" class="admin-overview-link" data-admin-select="${consultant.reference_code}">${consultant.display_name}</button><code>${consultant.reference_code}</code></td><td class="admin-total-column"><strong>${consultantLinkUseCount(consultant)}</strong></td>${accessCells}`;
    return row;
  }));
  if (window.lucide) window.lucide.createIcons();
}

function updateAdminCurrent() {
  const select = document.querySelector("#adminConsultantSelect");
  const selected = adminState.filtered.find(item => item.reference_code === select.value);
  document.querySelector("#adminCurrentConsultant").textContent = selected
    ? `${selected.display_name} · ${selected.reference_code}${selected.own_shop_enabled ? " · Egen butikk aktiv" : ""}`
    : "Ingen konsulent passer søket.";
  renderAdminProductAccess(selected);
  renderAdminMail(selected);
  renderAdminConsultantEdit(selected);
}

function renderAdminConsultantEdit(consultant) {
  const form = document.querySelector("#adminConsultantEditForm");
  const fields = form.querySelectorAll("input, button");
  fields.forEach(field => { field.disabled = !consultant; });
  document.querySelector("#adminEditName").value = consultant?.display_name || "";
  document.querySelector("#adminEditEmail").value = consultant?.email || "";
  document.querySelector("#adminEditPhone").value = consultant?.phone || "";
  document.querySelector("#adminEditReference").value = consultant?.reference_code || "";
  document.querySelector("#adminEditMessage").textContent = consultant
    ? "Endringer lagres direkte i konsulentregisteret."
    : "Velg en konsulent først.";
}

async function updateAdminConsultant(event) {
  event.preventDefault();
  const consultant = selectedAdminConsultant();
  if (!consultant) return;
  const button = document.querySelector("#adminEditSave");
  const message = document.querySelector("#adminEditMessage");
  button.disabled = true;
  message.textContent = "Lagrer opplysningene ...";
  try {
    const result = await jsonRequest(
      `${adminState.config.supabaseUrl}/rest/v1/rpc/superadmin_update_consultant`,
      {
        method: "POST",
        headers: adminHeaders(),
        body: JSON.stringify({
          p_reference_code: consultant.reference_code,
          p_display_name: document.querySelector("#adminEditName").value.trim(),
          p_email: document.querySelector("#adminEditEmail").value.trim() || null,
          p_phone: document.querySelector("#adminEditPhone").value.trim() || null,
        }),
      },
    );
    const saved = result[0];
    if (!saved) throw new Error("Databasen returnerte ingen oppdaterte opplysninger.");
    consultant.display_name = saved.display_name;
    consultant.email = saved.email;
    consultant.phone = saved.phone;
    message.textContent = "Opplysningene er lagret.";
    renderAdminMail(consultant);
    renderAdminOverview();
    showToast("Konsulentopplysningene er oppdatert");
    window.setTimeout(() => window.location.reload(), 650);
  } catch (error) {
    message.textContent = error.message || "Kunne ikke lagre opplysningene.";
  } finally {
    button.disabled = false;
  }
}

async function createAdminConsultant(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = document.querySelector("#adminCreateSave");
  const message = document.querySelector("#adminCreateMessage");
  const reference = cleanReference(document.querySelector("#adminCreateReference").value).toUpperCase();
  if (!reference) {
    message.textContent = "Skriv inn en gyldig konsulentreferanse.";
    return;
  }
  button.disabled = true;
  message.textContent = "Oppretter konsulenten ...";
  try {
    const result = await jsonRequest(
      `${adminState.config.supabaseUrl}/rest/v1/rpc/superadmin_create_consultant`,
      {
        method: "POST",
        headers: adminHeaders(),
        body: JSON.stringify({
          p_reference_code: reference,
          p_display_name: document.querySelector("#adminCreateName").value.trim(),
          p_email: document.querySelector("#adminCreateEmail").value.trim(),
          p_phone: document.querySelector("#adminCreatePhone").value.trim(),
        }),
      },
    );
    const created = result[0];
    if (!created) throw new Error("Databasen returnerte ingen ny konsulent.");
    message.textContent = "Konsulenten er opprettet med de to nyeste katalogene.";
    form.reset();
    showToast("Konsulenten er opprettet");
    window.setTimeout(() => {
      const url = new URL(window.location.href);
      url.searchParams.set("ref", created.reference_code);
      window.location.assign(url.toString());
    }, 700);
  } catch (error) {
    message.textContent = error.message || "Kunne ikke opprette konsulenten.";
  } finally {
    button.disabled = false;
  }
}

function renderAdminProductAccess(consultant) {
  const list = document.querySelector("#adminProductAccessList");
  if (!consultant) {
    list.innerHTML = `<p class="admin-product-empty">Velg en konsulent først.</p>`;
    return;
  }
  list.innerHTML = productRegister.map(product => {
    const active = consultant.product_access.has(product.key);
    return `
      <div class="admin-product-row">
        <div>
          <strong>${product.title}</strong>
          <span>${active ? "Kjøpt og aktiv" : "Ikke kjøpt"}</span>
        </div>
        <button type="button" class="${active ? "revoke" : ""}"
          data-product-access="${product.key}">
          <i data-lucide="${active ? "lock-keyhole" : "key-round"}"></i>
          <span>${active ? "Fjern tilgang" : "Gi tilgang"}</span>
        </button>
      </div>
    `;
  }).join("");
  if (window.lucide) window.lucide.createIcons();
}

function openAdminConsultant(reference) {
  if (!reference) return;
  const url = new URL("/mine-sider", window.location.origin);
  url.searchParams.set("ref", reference);
  window.location.assign(url);
}

function moveAdminConsultant(direction) {
  if (!adminState.filtered.length) return;
  const select = document.querySelector("#adminConsultantSelect");
  const currentIndex = Math.max(0, adminState.filtered.findIndex(item => item.reference_code === select.value));
  const nextIndex = (currentIndex + direction + adminState.filtered.length) % adminState.filtered.length;
  openAdminConsultant(adminState.filtered[nextIndex].reference_code);
}

async function verifySuperAdmin() {
  const userId = adminState.session?.user?.id;
  if (!userId) throw new Error("Innloggingen mangler brukerinformasjon.");
  const rows = await jsonRequest(
    `${adminState.config.supabaseUrl}/rest/v1/admin_users?select=is_super_admin&user_id=eq.${encodeURIComponent(userId)}&limit=1`,
    { headers: adminHeaders() },
  );
  if (!rows[0]?.is_super_admin) throw new Error("Denne brukeren er ikke registrert som superadministrator.");
}

async function loadAdminConsultants() {
  const [consultants, productAccess, catalogCounters] = await Promise.all([
    jsonRequest(
      `${adminState.config.supabaseUrl}/rest/v1/consultants?select=id,reference_code,display_name,email,phone,status,public_listing,municipality,county,own_shop_enabled,link_use_count&order=display_name.asc&limit=500`,
      { headers: adminHeaders() },
    ),
    jsonRequest(
      `${adminState.config.supabaseUrl}/rest/v1/consultant_product_access?select=consultant_id,product_key,is_active`,
      { headers: adminHeaders() },
    ),
    jsonRequest(
      `${adminState.config.supabaseUrl}/rest/v1/consultant_catalog_use_counters?select=consultant_id,catalog_key,open_count,last_opened_at`,
      { headers: adminHeaders() },
    ).catch(() => []),
  ]);
  adminState.productAccess = productAccess;
  adminState.consultants = consultants.map(consultant => ({
    ...consultant,
    catalog_counts: Object.fromEntries(catalogCounters
      .filter(item => item.consultant_id === consultant.id)
      .map(item => [item.catalog_key, Number(item.open_count || 0)])),
    product_access: new Set(productAccess
      .filter(item => item.consultant_id === consultant.id && item.is_active)
      .map(item => item.product_key)),
  }));
  renderAdminConsultants();
  document.querySelector("#adminPaymentProduct").replaceChildren(...productRegister.map(product => new Option(product.title, product.key)));
  await loadAdminAccounting();
}

async function toggleAdminProductAccess(productKey) {
  const selectedReference = document.querySelector("#adminConsultantSelect").value;
  const consultant = adminState.consultants.find(item => item.reference_code === selectedReference);
  if (!consultant) return;
  const button = document.querySelector(`[data-product-access="${productKey}"]`);
  button.disabled = true;
  try {
    const nextActive = !consultant.product_access.has(productKey);
    await jsonRequest(
      `${adminState.config.supabaseUrl}/rest/v1/consultant_product_access?on_conflict=consultant_id,product_key`,
      {
        method: "POST",
        headers: adminHeaders({ Prefer: "resolution=merge-duplicates,return=minimal" }),
        body: JSON.stringify({
          consultant_id: consultant.id,
          product_key: productKey,
          is_active: nextActive,
          updated_at: new Date().toISOString(),
        }),
      },
    );
    if (productKey === "egne-varer" && !nextActive && consultant.own_shop_enabled) {
      await jsonRequest(
        `${adminState.config.supabaseUrl}/rest/v1/consultants?id=eq.${encodeURIComponent(consultant.id)}`,
        {
          method: "PATCH",
          headers: adminHeaders({ Prefer: "return=minimal" }),
          body: JSON.stringify({ own_shop_enabled: false }),
        },
      );
      consultant.own_shop_enabled = false;
    }
    if (productKey === "egne-varer" && nextActive && !consultant.own_shop_enabled) {
      await jsonRequest(
        `${adminState.config.supabaseUrl}/rest/v1/consultants?id=eq.${encodeURIComponent(consultant.id)}`,
        {
          method: "PATCH",
          headers: adminHeaders({ Prefer: "return=minimal" }),
          body: JSON.stringify({ own_shop_enabled: true }),
        },
      );
      consultant.own_shop_enabled = true;
    }
    if (nextActive) consultant.product_access.add(productKey);
    else consultant.product_access.delete(productKey);
    if (consultant.reference_code === referenceCode && consultantProfile?.productAccess) {
      if (nextActive) consultantProfile.productAccess.add(productKey);
      else consultantProfile.productAccess.delete(productKey);
      renderProductRegistry(consultantProfile);
      updateVisibleModules();
    }
    updateAdminCurrent();
    renderAdminOverview();
    showToast(nextActive
      ? "Produkttilgangen er gitt"
      : "Produkttilgangen er fjernet");
    window.setTimeout(() => window.location.reload(), 250);
  } catch (error) {
    showToast(error.message);
  } finally {
    button.disabled = false;
  }
}

async function showAdminBrowser() {
  await verifySuperAdmin();
  await loadAdminConsultants();
  document.querySelector("#adminLoginForm").hidden = true;
  document.querySelector("#adminBrowser").hidden = false;
  document.querySelector("#adminAccountName").textContent = adminState.session.user.email || "Superadministrator";
  if (window.lucide) window.lucide.createIcons();
}

async function initializeAdminSwitcher() {
  adminState.config = await jsonRequest("/api/public-config");
  if (!adminState.config.configured) throw new Error("Databasen er ikke koblet til løsningen.");
  const session = restoredAdminSession();
  if (!session) return;
  saveAdminSession(session);
  try {
    await showAdminBrowser();
  } catch {
    clearAdminSession();
  }
}

async function copyText(value) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const input = document.createElement("textarea");
  input.value = value;
  input.style.position = "fixed";
  input.style.opacity = "0";
  document.body.appendChild(input);
  input.select();
  document.execCommand("copy");
  input.remove();
}

async function copyAdminMail() {
  const consultant = selectedAdminConsultant();
  if (!consultant?.email) return;
  const mail = adminMailContent(consultant);
  await copyText(`Til: ${consultant.email}\nEmne: ${mail.subject}\n\n${mail.body}`);
  showToast("E-posten er kopiert");
}

function openAdminGmail() {
  const consultant = selectedAdminConsultant();
  if (!consultant?.email) return;
  const mail = adminMailContent(consultant);
  const url = new URL("https://mail.google.com/mail/");
  url.searchParams.set("view", "cm");
  url.searchParams.set("fs", "1");
  url.searchParams.set("to", consultant.email);
  url.searchParams.set("su", mail.subject);
  url.searchParams.set("body", mail.body);
  window.open(url.toString(), "_blank", "noopener");
}

async function registerAdminPayment(event) {
  event.preventDefault();
  const consultant = selectedAdminConsultant();
  if (!consultant) return showToast("Velg en konsulent først");
  const form = event.currentTarget;
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;
  try {
    await jsonRequest(`${adminState.config.supabaseUrl}/rest/v1/consultant_product_payments`, {
      method: "POST",
      headers: adminHeaders({ Prefer: "return=minimal" }),
      body: JSON.stringify({
        consultant_id: consultant.id,
        product_key: document.querySelector("#adminPaymentProduct").value,
        amount_nok: Number(document.querySelector("#adminPaymentAmount").value),
        payment_status: document.querySelector("#adminPaymentStatus").value,
        paid_at: document.querySelector("#adminPaymentDate").value,
        note: document.querySelector("#adminPaymentNote").value.trim() || null,
      }),
    });
    document.querySelector("#adminPaymentNote").value = "";
    const paidMonth = document.querySelector("#adminPaymentDate").value.slice(0, 7);
    document.querySelector("#adminAccountingMonth").value = paidMonth;
    await loadAdminAccounting();
    showToast("Betalingen er registrert");
  } catch (error) {
    showToast(error.message || "Kunne ikke registrere betalingen");
  } finally {
    button.disabled = false;
  }
}

function qrDataUrl(value, width = 360) {
  return new Promise((resolve, reject) => {
    if (!window.QRCode) return reject(new Error("QR-biblioteket mangler"));
    window.QRCode.toDataURL(value, {
      width,
      margin: 2,
      errorCorrectionLevel: "M",
      color: { dark: "#202825", light: "#ffffff" },
    }, (error, url) => error ? reject(error) : resolve(url));
  });
}

async function renderShareItem(key) {
  const link = document.querySelector(`#${key}ShareUrl`);
  const image = document.querySelector(`#${key}Qr`);
  const download = document.querySelector(`#${key}QrDownload`);
  const url = shareUrls[key];
  link.href = url;
  link.textContent = url;
  try {
    const dataUrl = await qrDataUrl(url);
    image.src = dataUrl;
    download.href = dataUrl;
    download.download = `qr-${shareDetails[key].filename}-${referenceCode.toLowerCase()}.png`;
  } catch {
    image.alt = "QR-koden kunne ikke lages";
    download.hidden = true;
  }
}

function loadImage(source) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = source;
  });
}

function wrapCanvasText(context, text, maxWidth) {
  const words = text.split(/\s+/);
  const lines = [];
  let line = "";
  words.forEach(word => {
    const candidate = line ? `${line} ${word}` : word;
    if (line && context.measureText(candidate).width > maxWidth) {
      lines.push(line);
      line = word;
    } else {
      line = candidate;
    }
  });
  if (line) lines.push(line);
  return lines;
}

function drawCenteredLines(context, lines, centerX, startY, lineHeight) {
  lines.forEach((line, index) => context.fillText(line, centerX, startY + (index * lineHeight)));
}

function asciiBytes(value) {
  return new TextEncoder().encode(value);
}

function concatBytes(parts) {
  const length = parts.reduce((sum, part) => sum + part.length, 0);
  const result = new Uint8Array(length);
  let offset = 0;
  parts.forEach(part => {
    result.set(part, offset);
    offset += part.length;
  });
  return result;
}

function jpegPdfBlob(jpegDataUrl, imageWidth, imageHeight) {
  const binary = atob(jpegDataUrl.split(",")[1]);
  const jpeg = Uint8Array.from(binary, character => character.charCodeAt(0));
  const content = asciiBytes("q\n595.28 0 0 841.89 0 0 cm\n/Im0 Do\nQ\n");
  const objects = [
    asciiBytes("<< /Type /Catalog /Pages 2 0 R >>"),
    asciiBytes("<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
    asciiBytes("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>"),
    concatBytes([
      asciiBytes(`<< /Type /XObject /Subtype /Image /Width ${imageWidth} /Height ${imageHeight} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${jpeg.length} >>\nstream\n`),
      jpeg,
      asciiBytes("\nendstream"),
    ]),
    concatBytes([asciiBytes(`<< /Length ${content.length} >>\nstream\n`), content, asciiBytes("endstream")]),
  ];
  const parts = [asciiBytes("%PDF-1.4\n%\xE2\xE3\xCF\xD3\n")];
  const offsets = [0];
  let byteOffset = parts[0].length;
  objects.forEach((object, index) => {
    offsets.push(byteOffset);
    const wrapped = concatBytes([asciiBytes(`${index + 1} 0 obj\n`), object, asciiBytes("\nendobj\n")]);
    parts.push(wrapped);
    byteOffset += wrapped.length;
  });
  const xrefOffset = byteOffset;
  const xref = ["xref", `0 ${objects.length + 1}`, "0000000000 65535 f "];
  offsets.slice(1).forEach(offset => xref.push(`${String(offset).padStart(10, "0")} 00000 n `));
  xref.push("trailer", `<< /Size ${objects.length + 1} /Root 1 0 R >>`, "startxref", String(xrefOffset), "%%EOF");
  parts.push(asciiBytes(`${xref.join("\n")}\n`));
  return new Blob(parts, { type: "application/pdf" });
}

async function downloadPoster(key) {
  const qrSource = await qrDataUrl(shareUrls[key], 720);
  const qrImage = await loadImage(qrSource);

  const details = shareDetails[key];
  const firstName = consultantName.split(" ")[0];
  const title = key === "own" ? `Velkommen til ${firstName}s egne varer` : details.title;
  const canvas = document.createElement("canvas");
  canvas.width = 1654;
  canvas.height = 2339;
  const context = canvas.getContext("2d");
  const centerX = canvas.width / 2;

  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#007b68";
  context.fillRect(0, 0, canvas.width, 245);
  context.fillStyle = "#ffffff";
  context.font = "700 42px Arial";
  context.textAlign = "center";
  context.fillText("TUPPERWARE NORSK NETTKATALOG", centerX, 150);

  context.fillStyle = "#202825";
  context.font = "700 74px Arial";
  const titleLines = wrapCanvasText(context, title, 1350);
  drawCenteredLines(context, titleLines, centerX, 375, 88);
  const titleBottom = 375 + ((titleLines.length - 1) * 88);

  context.fillStyle = "#4a5450";
  context.font = "400 38px Arial";
  const detailLines = wrapCanvasText(context, details.text, 1250);
  drawCenteredLines(context, detailLines, centerX, titleBottom + 100, 52);

  const qrSize = 560;
  const qrY = titleBottom + 220;
  context.strokeStyle = "#d7dedb";
  context.lineWidth = 4;
  context.strokeRect((canvas.width - qrSize) / 2 - 24, qrY - 24, qrSize + 48, qrSize + 48);
  context.drawImage(qrImage, (canvas.width - qrSize) / 2, qrY, qrSize, qrSize);

  const instructionY = qrY + qrSize + 85;
  const instructionX = 180;
  const instructionWidth = canvas.width - 360;
  const instructionHeight = 410;
  const actionText = key === "store"
    ? "Handle i Tupperwares norske nettbutikk."
    : key === "own"
      ? "Se varene konsulenten har på eget lager."
      : "Se katalogen og velg produktene du er interessert i.";

  context.fillStyle = "#edf7f4";
  context.fillRect(instructionX, instructionY, instructionWidth, instructionHeight);
  context.fillStyle = "#007b68";
  context.fillRect(instructionX, instructionY, 12, instructionHeight);
  context.fillStyle = "#202825";
  context.textAlign = "left";
  context.font = "700 39px Arial";
  context.fillText("Slik gjør du", instructionX + 58, instructionY + 62);
  context.font = "400 28px Arial";
  const instructions = [
    "1. Åpne kameraet på mobilen og pek det mot QR-koden.",
    "2. Trykk på lenken som vises på skjermen.",
    `3. ${actionText}`,
    "4. Konsulentens referanse følger lenken automatisk.",
  ];
  instructions.forEach((instruction, index) => {
    context.fillText(instruction, instructionX + 58, instructionY + 125 + (index * 57));
  });
  context.fillStyle = "#465651";
  context.font = "700 24px Arial";
  context.fillText(
    "Pris og lagerstatus hos Tupperware gjelder alltid ved bestilling.",
    instructionX + 58,
    instructionY + 365,
  );
  context.textAlign = "center";

  if (key === "own") {
    context.fillStyle = "#faf1f3";
    context.fillRect(180, instructionY + instructionHeight + 24, canvas.width - 360, 86);
    context.fillStyle = "#802535";
    context.font = "700 25px Arial";
    context.fillText("Varene kommer fra konsulentens eget lager, ikke Tupperwares sentrallager.", centerX, instructionY + instructionHeight + 77);
  }

  context.strokeStyle = "#d7dedb";
  context.lineWidth = 3;
  context.beginPath();
  context.moveTo(180, 2050);
  context.lineTo(canvas.width - 180, 2050);
  context.stroke();
  context.fillStyle = "#202825";
  context.font = "700 34px Arial";
  context.fillText(`Din Tupperware-konsulent: ${consultantName}`, centerX, 2120);
  context.fillStyle = "#4a5450";
  context.font = "400 19px Arial";
  context.fillText(`Konsulentreferanse: ${referenceCode}`, centerX, 2170);
  const urlLines = wrapCanvasText(context, shareUrls[key], 1180);
  drawCenteredLines(context, urlLines, centerX, 2215, 28);

  const pdfBlob = jpegPdfBlob(canvas.toDataURL("image/jpeg", 0.94), canvas.width, canvas.height);
  const downloadUrl = URL.createObjectURL(pdfBlob);
  const link = document.createElement("a");
  link.href = downloadUrl;
  link.download = `${details.filename}-${referenceCode.toLowerCase()}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 30000);
}

function setPersonalLinks(name) {
  consultantName = name;
  document.querySelector("#hubConsultantName").textContent = `Arbeidsflate for ${name}`;
  document.querySelector("#pageConsultantName").textContent = name;
  document.querySelector("#hubReference").textContent = referenceCode;
  document.querySelector("#consultantStoreLink").href = shareUrls.store;
  document.querySelector("#officialCatalogLink").href = shareUrls.official;
  document.querySelector("#digitalCatalogLink").href = shareUrls.digital;
  document.querySelector("#septemberCatalogLink").href = shareUrls.september;
  document.querySelector("#winterCatalogLink").href = shareUrls.winter;
  document.querySelector("#ownCatalogModule").href = shareUrls.own;
  document.querySelector("#partyModule").href = shareUrls.party;
  document.querySelector("#footerCatalogLink").href = shareUrls.official;
  const mailToolLink = document.querySelector("#mailToolLink");
  if (mailToolLink) mailToolLink.href = `/mail-verktøy?ref=${encodeURIComponent(referenceCode)}`;
  document.querySelector("#ownCatalogTitle").textContent = `${name.split(" ")[0]}s egne varer`;
}

function currentProductAccess(product) {
  return Boolean(consultantProfile?.productAccess?.has(product.key));
}

function renderProductRegistry(status) {
  const intro = document.querySelector("#productRegisterIntro");
  const list = document.querySelector("#productRegistryList");
  if (!intro || !list) return;
  const consultantLabel = consultantName || referenceCode;
  const registered = Boolean(status?.registered);
  const activeProducts = productRegister.filter(currentProductAccess);
  intro.textContent = registered
    ? `${consultantLabel} har tilgang til ${activeProducts.length} ${activeProducts.length === 1 ? "produkt" : "produkter"}.`
    : `Konsulenten ${consultantLabel} er ikke registrert ennå.`;
  list.innerHTML = activeProducts.map(product => {
    return `
      <article class="registry-card is-active">
        <div class="registry-card-head">
          <div>
            <strong>${product.title}</strong>
            <p>${product.description}</p>
          </div>
          <span class="module-status active">Tilgang</span>
        </div>
        <div class="registry-meta">
          <span>${product.accessLabel}</span>
        </div>
      </article>
    `;
  }).join("") || `<p class="admin-product-empty">Ingen produkter er åpnet for denne konsulenten ennå.</p>`;
}

function updateVisibleModules() {
  const access = consultantProfile?.productAccess || new Set();
  document.querySelector("#officialCatalogLink").hidden = !access.has("norsk-nettkatalog");
  document.querySelector("#digitalCatalogLink").hidden = !access.has("norsk-produktkatalog");
  document.querySelector("#septemberCatalogLink").hidden = !access.has("maanedstilbud");
  document.querySelector("#winterCatalogLink").hidden = !access.has("tw-host-vinter-2026-27");
  document.querySelector("#ownCatalogModule").hidden = !access.has("egne-varer");
  document.querySelector("#partyModule").hidden = !access.has("party");
  document.querySelector('[data-share="official"]').hidden = !access.has("norsk-nettkatalog");
  document.querySelector('[data-share="digital"]').hidden = !access.has("norsk-produktkatalog");
  document.querySelector('[data-share="september"]').hidden = !access.has("maanedstilbud");
  document.querySelector('[data-share="winter"]').hidden = !access.has("tw-host-vinter-2026-27");
  document.querySelector('[data-share="party"]').hidden = !access.has("party");
}

async function loadConsultant() {
  const response = await fetch(`/api/consultant?ref=${encodeURIComponent(referenceCode)}`);
  const result = await response.json();
  if (!response.ok || !result.found) throw new Error("Konsulenten finnes ikke");
  consultantProfile = result;
  const accessResponse = await fetch(`/api/product-access?ref=${encodeURIComponent(referenceCode)}`);
  const accessResult = await accessResponse.json();
  consultantProfile.productAccess = new Set(
    accessResponse.ok ? accessResult.products || [] : [],
  );
  const name = result.name || result.consultant?.display_name || referenceCode;
  setPersonalLinks(name);
  renderProductRegistry(result);
  updateVisibleModules();
  const shareTasks = [];
  shareTasks.push(renderShareItem("store"));
  if (consultantProfile.productAccess.has("norsk-nettkatalog")) shareTasks.push(renderShareItem("official"));
  if (consultantProfile.productAccess.has("norsk-produktkatalog")) shareTasks.push(renderShareItem("digital"));
  if (consultantProfile.productAccess.has("maanedstilbud")) shareTasks.push(renderShareItem("september"));
  if (consultantProfile.productAccess.has("tw-host-vinter-2026-27")) shareTasks.push(renderShareItem("winter"));
  if (consultantProfile.productAccess.has("party")) shareTasks.push(renderShareItem("party"));
  await Promise.all(shareTasks);

  try {
    const shopResponse = await fetch(`/api/shop-status?ref=${encodeURIComponent(referenceCode)}`);
    const shop = await shopResponse.json();
    if (shopResponse.ok && shop.enabled && shop.hasProducts) {
      document.querySelector("#ownCatalogModule").hidden = false;
      document.querySelector("#ownCatalogShare").hidden = false;
      await renderShareItem("own");
    }
  } catch {
    // The two public catalogs remain available if own-stock status cannot load.
  }
}

document.addEventListener("click", async event => {
  const posterButton = event.target.closest("[data-poster]");
  if (posterButton) {
    try {
      await downloadPoster(posterButton.dataset.poster);
      showToast("PDF-plakaten er lastet ned");
    } catch {
      showToast("Kunne ikke lage PDF-plakaten");
    }
    return;
  }
  const button = event.target.closest("[data-copy]");
  if (!button) return;
  try {
    await copyText(shareUrls[button.dataset.copy]);
    showToast("Lenken er kopiert");
  } catch {
    showToast("Kunne ikke kopiere lenken");
  }
});

document.querySelector("#adminLoginForm").addEventListener("submit", async event => {
  event.preventDefault();
  const button = document.querySelector("#adminLoginButton");
  const message = document.querySelector("#adminLoginMessage");
  button.disabled = true;
  message.textContent = "Kontrollerer innlogging ...";
  try {
    if (!adminState.config) {
      adminState.config = await jsonRequest("/api/public-config");
    }
    if (!adminState.config.configured) throw new Error("Databasen er ikke koblet til løsningen.");
    const session = await jsonRequest(
      `${adminState.config.supabaseUrl}/auth/v1/token?grant_type=password`,
      {
        method: "POST",
        headers: {
          apikey: adminState.config.supabaseAnonKey,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: document.querySelector("#adminEmail").value.trim(),
          password: document.querySelector("#adminPassword").value,
        }),
      },
    );
    saveAdminSession(session);
    await showAdminBrowser();
    document.querySelector("#adminPassword").value = "";
    message.textContent = "";
  } catch (error) {
    clearAdminSession();
    message.textContent = error.message || "Kunne ikke logge inn.";
  } finally {
    button.disabled = false;
  }
});

document.querySelector("#adminLogoutButton").addEventListener("click", () => {
  clearAdminSession();
  adminState.consultants = [];
  adminState.filtered = [];
  document.querySelector("#adminBrowser").hidden = true;
  document.querySelector("#adminLoginForm").hidden = false;
  document.querySelector("#adminPassword").focus();
});

document.querySelector("#adminConsultantSearch").addEventListener("input", event => {
  renderAdminConsultants(event.target.value);
});
document.querySelector("#adminConsultantSelect").addEventListener("change", event => {
  const url = new URL(window.location.href);
  if (event.target.value) url.searchParams.set("ref", event.target.value);
  else url.searchParams.delete("ref");
  window.location.assign(url.toString());
});
document.querySelector("#adminOpenConsultant").addEventListener("click", () => {
  openAdminConsultant(document.querySelector("#adminConsultantSelect").value);
});
document.querySelector("#adminPrevious").addEventListener("click", () => moveAdminConsultant(-1));
document.querySelector("#adminNext").addEventListener("click", () => moveAdminConsultant(1));
document.querySelector("#adminProductAccessList").addEventListener("click", event => {
  const button = event.target.closest("[data-product-access]");
  if (button) toggleAdminProductAccess(button.dataset.productAccess);
});
document.querySelector("#adminConsultantEditForm").addEventListener("submit", updateAdminConsultant);
document.querySelector("#adminConsultantCreateForm").addEventListener("submit", createAdminConsultant);
document.querySelector("#adminConsultantOverview").addEventListener("click", event => {
  const accessButton = event.target.closest("[data-overview-access]");
  if (accessButton) {
    const select = document.querySelector("#adminConsultantSelect");
    select.value = accessButton.dataset.accessConsultant;
    updateAdminCurrent();
    toggleAdminProductAccess(accessButton.dataset.overviewAccess);
    return;
  }
  const button = event.target.closest("[data-admin-select]");
  if (!button) return;
  const url = new URL(window.location.href);
  url.searchParams.set("ref", button.dataset.adminSelect);
  window.location.assign(url.toString());
});
document.querySelector("#adminCopyMail").addEventListener("click", () => copyAdminMail().catch(error => showToast(error.message)));
document.querySelector("#adminOpenGmail").addEventListener("click", openAdminGmail);
document.querySelector("#adminPaymentForm").addEventListener("submit", registerAdminPayment);
document.querySelector("#adminAccountingMonth").addEventListener("change", () => loadAdminAccounting());

window.addEventListener("DOMContentLoaded", async () => {
  const today = new Date();
  const localDate = new Date(today.getTime() - today.getTimezoneOffset() * 60000).toISOString();
  document.querySelector("#adminPaymentDate").value = localDate.slice(0, 10);
  document.querySelector("#adminAccountingMonth").value = localDate.slice(0, 7);
  if (window.lucide) window.lucide.createIcons();
  if (adminMode) {
    document.querySelector("#adminSwitcher").hidden = false;
    initializeAdminSwitcher().catch(error => {
      document.querySelector("#adminLoginMessage").textContent = error.message || "Kunne ikke starte administratorverktøyet.";
    });
  }
  if (!referenceCode) {
    document.querySelector("#hubConsultantName").textContent = "Ingen konsulent valgt";
    document.querySelector("#pageConsultantName").textContent = "INGEN KONSULENT VALGT";
    document.querySelector("#hubReference").textContent = "Velg konsulent via personlig lenke";
    document.querySelector(".share-section").hidden = true;
    return;
  }
  try {
    await loadConsultant();
  } catch {
    document.querySelector("#hubConsultantName").textContent = "Ugyldig konsulent";
    document.querySelector("#pageConsultantName").textContent = "KONSULENTEN FINNES IKKE";
    document.querySelector("#hubReference").textContent = referenceCode || "MANGLER";
    document.querySelector(".share-section").hidden = true;
  }
});
