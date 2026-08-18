const state = {
  config: null,
  session: null,
  consultant: null,
  inventory: [],
  orders: [],
  officialProducts: [],
  productAccess: new Set(),
};

const productAccessCatalog = [
  {
    key: "norsk-nettkatalog",
    title: "Norsk Nettkatalog",
    description: "Den norske nettkatalogen med produkter fra Tupperwares nettbutikk.",
    accessLabel: "Kjøpes separat",
    accessType: "entitlement",
  },
  {
    key: "norsk-produktkatalog",
    title: "Norsk produktkatalog",
    description: "Den digitale produktkatalogen som bygger på PDF-katalogen.",
    accessLabel: "Kjøpes separat",
    accessType: "entitlement",
  },
  {
    key: "egne-varer",
    title: "Egne varer",
    description: "Egen varekatalog, lagerstyring og bestillinger direkte til deg.",
    accessLabel: "Tilleggsprodukt - kjøpes separat",
    accessType: "entitlement",
  },
];

const els = {
  loginView: document.querySelector("#loginView"),
  loginForm: document.querySelector("#loginForm"),
  loginButton: document.querySelector("#loginButton"),
  resetPasswordButton: document.querySelector("#resetPasswordButton"),
  loginMessage: document.querySelector("#loginMessage"),
  passwordSetupForm: document.querySelector("#passwordSetupForm"),
  passwordSetupButton: document.querySelector("#passwordSetupButton"),
  passwordSetupMessage: document.querySelector("#passwordSetupMessage"),
  manageView: document.querySelector("#manageView"),
  accountArea: document.querySelector("#accountArea"),
  accountName: document.querySelector("#accountName"),
  logoutButton: document.querySelector("#logoutButton"),
  manageTitle: document.querySelector("#manageTitle"),
  viewCatalogLink: document.querySelector("#viewCatalogLink"),
  inventoryView: document.querySelector("#inventoryView"),
  ordersView: document.querySelector("#ordersView"),
  profileView: document.querySelector("#profileView"),
  reportView: document.querySelector("#reportView"),
  profileForm: document.querySelector("#profileForm"),
  saveProfile: document.querySelector("#saveProfile"),
  profilePhotoPreview: document.querySelector("#profilePhotoPreview"),
  profileReference: document.querySelector("#profileReference"),
  profileShopState: document.querySelector("#profileShopState"),
  profileAccessState: document.querySelector("#profileAccessState"),
  profileAccessList: document.querySelector("#profileAccessList"),
  shopAccessSettings: document.querySelector("#shopAccessSettings"),
  shopAccessCodeField: document.querySelector("#shopAccessCodeField"),
  shopAccessCodeHelp: document.querySelector("#shopAccessCodeHelp"),
  inventoryCount: document.querySelector("#inventoryCount"),
  inventoryList: document.querySelector("#inventoryList"),
  inventoryValueBadge: document.querySelector("#inventoryValueBadge"),
  reportTotalValue: document.querySelector("#reportTotalValue"),
  reportUnitCount: document.querySelector("#reportUnitCount"),
  reportLineCount: document.querySelector("#reportLineCount"),
  reportVisibleValue: document.querySelector("#reportVisibleValue"),
  reportVisibleCount: document.querySelector("#reportVisibleCount"),
  reportHiddenValue: document.querySelector("#reportHiddenValue"),
  reportHiddenCount: document.querySelector("#reportHiddenCount"),
  reportVat: document.querySelector("#reportVat"),
  reportExVat: document.querySelector("#reportExVat"),
  reportVatAmount: document.querySelector("#reportVatAmount"),
  reportIncVat: document.querySelector("#reportIncVat"),
  reportVatNote: document.querySelector("#reportVatNote"),
  inventoryReportBody: document.querySelector("#inventoryReportBody"),
  reportTableUnits: document.querySelector("#reportTableUnits"),
  reportTableValue: document.querySelector("#reportTableValue"),
  reportNote: document.querySelector("#reportNote"),
  printInventoryReport: document.querySelector("#printInventoryReport"),
  orderList: document.querySelector("#orderList"),
  newOrderCount: document.querySelector("#newOrderCount"),
  refreshOrders: document.querySelector("#refreshOrders"),
  addFromTupperware: document.querySelector("#addFromTupperware"),
  addCustomProduct: document.querySelector("#addCustomProduct"),
  productEditor: document.querySelector("#productEditor"),
  productForm: document.querySelector("#productForm"),
  editorEyebrow: document.querySelector("#editorEyebrow"),
  editorTitle: document.querySelector("#editorTitle"),
  closeEditor: document.querySelector("#closeEditor"),
  deleteProduct: document.querySelector("#deleteProduct"),
  saveProduct: document.querySelector("#saveProduct"),
  officialPicker: document.querySelector("#officialPicker"),
  closeOfficialPicker: document.querySelector("#closeOfficialPicker"),
  officialSearchForm: document.querySelector("#officialSearchForm"),
  officialSearchInput: document.querySelector("#officialSearchInput"),
  officialResults: document.querySelector("#officialResults"),
  toast: document.querySelector("#toast"),
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  }[character]));
}

function formatNok(value) {
  return new Intl.NumberFormat("nb-NO", {
    style: "currency",
    currency: "NOK",
    maximumFractionDigits: Number(value) % 1 ? 2 : 0,
  }).format(Number(value || 0));
}

function formatDate(value) {
  return new Intl.DateTimeFormat("nb-NO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function refreshIcons() {
  if (window.lucide) window.lucide.createIcons();
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => els.toast.classList.remove("show"), 2800);
}

async function jsonRequest(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload.message
      || payload.error_description
      || payload.error
      || (response.status === 429
        ? "Supabase har nådd grensen for e-postutsending. Vent en stund før du prøver igjen."
        : "Noe gikk galt.");
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return payload;
}

function supabaseHeaders(extra = {}) {
  return {
    apikey: state.config.supabaseAnonKey,
    Authorization: `Bearer ${state.session.access_token}`,
    "Content-Type": "application/json",
    ...extra,
  };
}

function saveSession(session) {
  state.session = session;
  try {
    sessionStorage.setItem("consultantManageSession", JSON.stringify(session));
  } catch {
    // Innloggingen virker fortsatt frem til siden lukkes.
  }
}

function restoredSession() {
  try {
    const session = JSON.parse(sessionStorage.getItem("consultantManageSession") || "null");
    if (session?.access_token && session?.user?.id) return session;
  } catch {
    return null;
  }
  return null;
}

function clearSession() {
  state.session = null;
  state.consultant = null;
  try {
    sessionStorage.removeItem("consultantManageSession");
  } catch {
    // Ingen lokal økt å fjerne.
  }
}

async function loadConfig() {
  state.config = await jsonRequest("/api/public-config");
  if (!state.config.configured) throw new Error("Databasen er ikke koblet til løsningen.");
}

async function login(email, password) {
  return jsonRequest(`${state.config.supabaseUrl}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: {
      apikey: state.config.supabaseAnonKey,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });
}

async function requestPasswordRecovery(email) {
  const redirectTo = encodeURIComponent(`${location.origin}/konsulent`);
  return jsonRequest(`${state.config.supabaseUrl}/auth/v1/recover?redirect_to=${redirectTo}`, {
    method: "POST",
    headers: {
      apikey: state.config.supabaseAnonKey,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email }),
  });
}

async function loadAuthUser(accessToken) {
  return jsonRequest(`${state.config.supabaseUrl}/auth/v1/user`, {
    headers: {
      apikey: state.config.supabaseAnonKey,
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

async function updatePassword(password) {
  return jsonRequest(`${state.config.supabaseUrl}/auth/v1/user`, {
    method: "PUT",
    headers: supabaseHeaders(),
    body: JSON.stringify({ password }),
  });
}

async function restoreAuthLink() {
  const values = new URLSearchParams(location.hash.replace(/^#/, ""));
  const accessToken = values.get("access_token");
  const type = values.get("type");
  if (!accessToken || !["invite", "recovery"].includes(type)) return false;

  const user = await loadAuthUser(accessToken);
  saveSession({
    access_token: accessToken,
    refresh_token: values.get("refresh_token") || "",
    expires_in: Number(values.get("expires_in") || 3600),
    token_type: values.get("token_type") || "bearer",
    user,
  });
  els.loginForm.hidden = true;
  els.passwordSetupForm.hidden = false;
  return true;
}

async function loadConsultant() {
  const rows = await jsonRequest(
    `${state.config.supabaseUrl}/rest/v1/rpc/my_consultant_profile`,
    {
      method: "POST",
      headers: supabaseHeaders(),
      body: "{}",
    },
  );
  if (!rows.length) {
    throw new Error("Brukerkontoen er ikke koblet til en konsulentprofil ennå.");
  }
  state.consultant = rows[0];
}

async function loadProductAccess() {
  const rows = await jsonRequest(
    `${state.config.supabaseUrl}/rest/v1/rpc/my_product_access`,
    { method: "POST", headers: supabaseHeaders(), body: "{}" },
  );
  state.productAccess = new Set(rows.map(row => row.product_key));
}

async function loadInventory() {
  const consultantId = encodeURIComponent(state.consultant.id);
  state.inventory = await jsonRequest(
    `${state.config.supabaseUrl}/rest/v1/inventory?select=*&consultant_id=eq.${consultantId}&order=updated_at.desc`,
    { headers: supabaseHeaders() },
  );
  renderInventory();
}

async function loadOrders() {
  const consultantId = encodeURIComponent(state.consultant.id);
  state.orders = await jsonRequest(
    `${state.config.supabaseUrl}/rest/v1/order_requests?select=*,order_items(*)&consultant_id=eq.${consultantId}&order=created_at.desc&limit=100`,
    { headers: supabaseHeaders() },
  );
  renderOrders();
}

function inventoryRow(item) {
  const source = item.source_type === "custom" ? "Egen vare" : "Fra Tupperware";
  return `
    <article class="inventory-row">
      ${item.image_url
        ? `<img src="${escapeHtml(item.image_url)}" alt="">`
        : `<span class="inventory-image-placeholder"><i data-lucide="image"></i></span>`}
      <div class="inventory-main">
        <strong>${escapeHtml(item.product_name)}</strong>
        <small>${escapeHtml(item.article_number ? `Art.nr. ${item.article_number}` : "Uten artikkelnummer")}</small>
        <small class="inventory-source">${source}</small>
      </div>
      <div class="inventory-number"><span>På lager</span><strong>${item.quantity} stk.</strong></div>
      <div class="inventory-price"><span>Kundepris</span><strong>${formatNok(item.sale_price_nok)}</strong></div>
      <span class="inventory-status ${item.is_for_sale && item.is_active ? "" : "hidden-item"}">
        ${item.is_for_sale && item.is_active ? "Vises i katalogen" : "Skjult"}
      </span>
      <button class="edit-button" type="button" data-edit="${escapeHtml(item.id)}" aria-label="Rediger ${escapeHtml(item.product_name)}">
        <i data-lucide="pencil"></i>
      </button>
    </article>`;
}

function renderInventory() {
  els.inventoryCount.textContent = `${state.inventory.length} ${state.inventory.length === 1 ? "vare" : "varer"}`;
  els.inventoryList.innerHTML = state.inventory.length
    ? state.inventory.map(inventoryRow).join("")
    : `<div class="list-empty">Du har ingen egne varer ennå. Hent et produkt fra Tupperware eller opprett en egen vare.</div>`;
  renderInventoryReport();
  refreshIcons();
}

function inventoryLineValue(item) {
  const quantity = Math.max(0, Number(item.quantity) || 0);
  const price = Math.max(0, Number(item.sale_price_nok) || 0);
  return quantity * price;
}

function lineLabel(count) {
  return `${count} ${count === 1 ? "varelinje" : "varelinjer"}`;
}

function renderInventoryReport() {
  const totalUnits = state.inventory.reduce((sum, item) => sum + Math.max(0, Number(item.quantity) || 0), 0);
  const totalValue = state.inventory.reduce((sum, item) => sum + inventoryLineValue(item), 0);
  const visibleItems = state.inventory.filter(item => item.is_active && item.is_for_sale);
  const hiddenItems = state.inventory.filter(item => !item.is_active || !item.is_for_sale);
  const visibleValue = visibleItems.reduce((sum, item) => sum + inventoryLineValue(item), 0);
  const hiddenValue = hiddenItems.reduce((sum, item) => sum + inventoryLineValue(item), 0);
  const missingPriceCount = state.inventory.filter(item => (Number(item.quantity) || 0) > 0 && !(Number(item.sale_price_nok) > 0)).length;

  els.inventoryValueBadge.textContent = formatNok(totalValue);
  els.reportTotalValue.textContent = formatNok(totalValue);
  els.reportUnitCount.textContent = totalUnits;
  els.reportLineCount.textContent = state.inventory.length;
  els.reportVisibleValue.textContent = formatNok(visibleValue);
  els.reportVisibleCount.textContent = lineLabel(visibleItems.length);
  els.reportHiddenValue.textContent = formatNok(hiddenValue);
  els.reportHiddenCount.textContent = lineLabel(hiddenItems.length);
  els.reportTableUnits.textContent = totalUnits;
  els.reportTableValue.textContent = formatNok(totalValue);

  els.inventoryReportBody.innerHTML = state.inventory.length
    ? state.inventory.map(item => {
      const visible = item.is_active && item.is_for_sale;
      return `<tr>
        <td><strong>${escapeHtml(item.product_name || "Navnløs vare")}</strong>${item.article_number ? `<br><small>${escapeHtml(item.article_number)}</small>` : ""}</td>
        <td><span class="report-status${visible ? "" : " hidden-item"}">${visible ? "Vises" : "Skjult"}</span></td>
        <td>${Math.max(0, Number(item.quantity) || 0)}</td>
        <td>${formatNok(item.sale_price_nok)}</td>
        <td><strong>${formatNok(inventoryLineValue(item))}</strong></td>
      </tr>`;
    }).join("")
    : `<tr><td class="report-empty" colspan="5">Ingen varer er registrert ennå.</td></tr>`;

  const vatRegistered = state.consultant?.vat_status === "registered";
  els.reportVat.hidden = !vatRegistered;
  if (vatRegistered) {
    const rate = Math.max(0, Number(state.consultant.own_product_vat_rate) || 0);
    const includesVat = Boolean(state.consultant.own_product_prices_include_vat);
    const exVat = includesVat && rate ? totalValue / (1 + rate / 100) : totalValue;
    const vatAmount = includesVat ? totalValue - exVat : totalValue * rate / 100;
    const incVat = includesVat ? totalValue : totalValue + vatAmount;
    els.reportExVat.textContent = formatNok(exVat);
    els.reportVatAmount.textContent = formatNok(vatAmount);
    els.reportIncVat.textContent = formatNok(incVat);
    els.reportVatNote.textContent = `${rate}% MVA. ${includesVat ? "Registrerte kundepriser inkluderer MVA." : "MVA er beregnet i tillegg til registrerte kundepriser."}`;
  }

  const updated = new Intl.DateTimeFormat("nb-NO", { dateStyle: "long", timeStyle: "short" }).format(new Date());
  const missingPriceNote = missingPriceCount ? ` ${lineLabel(missingPriceCount)} med lagerbeholdning mangler pris og er derfor beregnet til 0 kr.` : "";
  els.reportNote.textContent = `Oppdatert ${updated}. Salgsverdi er antall på lager multiplisert med kundepris. Salgsverdi er ikke det samme som regnskapsmessig innkjøpsverdi.${missingPriceNote}`;
}

const orderStatus = {
  new: "Ny",
  contacted: "Kontaktet",
  completed: "Fullført",
  cancelled: "Avbrutt",
};

function orderCard(order) {
  const items = order.order_items || [];
  const total = items.reduce((sum, item) => sum + Number(item.observed_price_nok || 0) * item.quantity, 0);
  return `
    <article class="order-card ${order.status === "new" ? "new" : ""}">
      <header>
        <div>
          <h3>${escapeHtml(order.customer_name)}</h3>
          <p class="order-contact">${escapeHtml([order.customer_email, order.customer_phone].filter(Boolean).join(" · "))}</p>
        </div>
        <span>${formatDate(order.created_at)}</span>
      </header>
      ${order.customer_message ? `<p class="order-message">${escapeHtml(order.customer_message)}</p>` : ""}
      <ul class="order-items">
        ${items.map(item => `
          <li>
            <span>${item.quantity} × ${escapeHtml(item.product_name)}</span>
            <strong>${formatNok(Number(item.observed_price_nok || 0) * item.quantity)}</strong>
          </li>`).join("")}
      </ul>
      <footer class="order-footer">
        <strong>${formatNok(total)}</strong>
        <select data-order-status="${escapeHtml(order.id)}" aria-label="Status for bestilling fra ${escapeHtml(order.customer_name)}">
          ${Object.entries(orderStatus).map(([value, label]) => `
            <option value="${value}" ${order.status === value ? "selected" : ""}>${label}</option>`).join("")}
        </select>
      </footer>
    </article>`;
}

function renderOrders() {
  const newCount = state.orders.filter(order => order.status === "new").length;
  els.newOrderCount.textContent = newCount ? String(newCount) : "";
  els.orderList.innerHTML = state.orders.length
    ? state.orders.map(orderCard).join("")
    : `<div class="list-empty">Ingen bestillingsforespørsler ennå.</div>`;
}

function showManageView() {
  const name = state.consultant.display_name;
  els.loginView.hidden = true;
  els.manageView.hidden = false;
  els.accountArea.hidden = false;
  els.accountName.textContent = name;
  els.manageTitle.textContent = `${name}s egne varer`;
  els.viewCatalogLink.href = `/egne-varer?ref=${encodeURIComponent(state.consultant.reference_code)}`;
  els.viewCatalogLink.hidden = !state.consultant.own_shop_enabled
    || !state.productAccess.has("egne-varer");
  fillProfileForm();
  refreshIcons();
}

function profileField(name) {
  return els.profileForm.elements.namedItem(name);
}

function renderProfilePhoto(url) {
  els.profilePhotoPreview.innerHTML = url
    ? `<img src="${escapeHtml(url)}" alt="">`
    : `<i data-lucide="user-round"></i>`;
  refreshIcons();
}

function updateShopSettingsState() {
  const hasShopAccess = state.productAccess.has("egne-varer");
  if (!hasShopAccess) profileField("own_shop_enabled").checked = false;
  const enabled = profileField("own_shop_enabled").checked;
  const codeProtected = profileField("own_shop_access_mode").value === "code";
  profileField("own_shop_enabled").disabled = !hasShopAccess;
  els.profileShopState.textContent = !hasShopAccess
    ? "Krever tilgang"
    : enabled ? "Aktiv" : "Ikke aktiv";
  els.profileShopState.classList.toggle("active", hasShopAccess && enabled);
  els.shopAccessSettings.setAttribute("aria-disabled", String(!hasShopAccess || !enabled));
  els.shopAccessCodeField.hidden = !codeProtected;
  const hasCode = Boolean(state.consultant?.own_shop_has_access_code);
  els.shopAccessCodeHelp.textContent = hasCode
    ? "En kundekode er allerede lagret. La feltet stå tomt for å beholde den, eller skriv en ny kode."
    : "Velg en kode på minst 4 tegn som du kan sende til kundene du inviterer.";
}

function renderProfileAccess() {
  const activeCount = state.productAccess.size;
  els.profileAccessState.textContent = `${activeCount} aktive`;
  els.profileAccessState.classList.toggle("active", activeCount > 0);
  els.profileAccessList.innerHTML = productAccessCatalog.map(product => {
    const allowed = state.productAccess.has(product.key);
    return `
      <article class="access-card ${allowed ? "active" : "locked"}">
        <div class="access-card-head">
          <div>
            <strong>${escapeHtml(product.title)}</strong>
            <p>${escapeHtml(product.description)}</p>
          </div>
          <span class="access-badge ${allowed ? "active" : "locked"}">${allowed ? "Tilgang" : "Låst"}</span>
        </div>
        <div class="access-meta">
          <span>${escapeHtml(product.accessLabel)}</span>
          <span>${allowed ? "Konsulenten kan bruke denne løsningen." : "Konsulenten har ikke tilgang til denne løsningen."}</span>
        </div>
      </article>
    `;
  }).join("");
}

function fillProfileForm() {
  const consultant = state.consultant;
  profileField("display_name").value = consultant.display_name || "";
  profileField("email").value = consultant.email || "";
  profileField("phone").value = consultant.phone || "";
  profileField("municipality").value = consultant.municipality || "";
  profileField("county").value = consultant.county || "";
  profileField("public_listing").checked = Boolean(consultant.public_listing);
  profileField("show_email").checked = Boolean(consultant.show_email);
  profileField("show_phone").checked = Boolean(consultant.show_phone);
  profileField("vat_status").value = consultant.vat_status || "not_registered";
  profileField("organization_number").value = consultant.organization_number || "";
  profileField("vat_number").value = consultant.vat_number || "";
  profileField("own_product_vat_rate").value = consultant.own_product_vat_rate ?? 25;
  profileField("own_product_prices_include_vat").checked = Boolean(
    consultant.own_product_prices_include_vat,
  );
  profileField("own_shop_enabled").checked = Boolean(consultant.own_shop_enabled);
  profileField("own_shop_access_mode").value = consultant.own_shop_access_mode || "public";
  profileField("own_shop_access_code").value = "";
  els.profileReference.textContent = consultant.reference_code;
  renderProfilePhoto(consultant.profile_image_url);
  updateShopSettingsState();
  renderProfileAccess();
}

async function saveProfile(event) {
  event.preventDefault();
  els.saveProfile.disabled = true;
  try {
    const uploadedImage = await uploadImage(profileField("profile_image_file").files[0]);
    const rows = await jsonRequest(
      `${state.config.supabaseUrl}/rest/v1/rpc/update_my_consultant_profile`,
      {
        method: "POST",
        headers: supabaseHeaders(),
        body: JSON.stringify({
          p_display_name: profileField("display_name").value.trim(),
          p_email: profileField("email").value.trim() || null,
          p_phone: profileField("phone").value.trim() || null,
          p_municipality: profileField("municipality").value.trim() || null,
          p_county: profileField("county").value.trim() || null,
          p_profile_image_url: uploadedImage || state.consultant.profile_image_url || null,
          p_public_listing: profileField("public_listing").checked,
          p_show_email: profileField("show_email").checked,
          p_show_phone: profileField("show_phone").checked,
          p_vat_status: profileField("vat_status").value,
          p_organization_number: profileField("organization_number").value.trim() || null,
          p_vat_number: profileField("vat_number").value.trim() || null,
          p_own_product_vat_rate: Number(profileField("own_product_vat_rate").value || 0),
          p_own_product_prices_include_vat: profileField("own_product_prices_include_vat").checked,
        }),
      },
    );
    if (!rows.length) throw new Error("Fant ikke konsulentprofilen.");
    const shopRows = await jsonRequest(
      `${state.config.supabaseUrl}/rest/v1/rpc/update_my_consultant_shop_settings`,
      {
        method: "POST",
        headers: supabaseHeaders(),
        body: JSON.stringify({
          p_enabled: profileField("own_shop_enabled").checked,
          p_access_mode: profileField("own_shop_access_mode").value,
          p_new_access_code: profileField("own_shop_access_code").value.trim() || null,
        }),
      },
    );
    if (!shopRows.length) throw new Error("Kunne ikke lagre butikkinnstillingene.");
    state.consultant = { ...rows[0], ...shopRows[0] };
    showManageView();
    renderInventoryReport();
    renderProfileAccess();
    profileField("profile_image_file").value = "";
    profileField("own_shop_access_code").value = "";
    showToast("Profilen er lagret.");
  } catch (error) {
    showToast(error.message);
  } finally {
    els.saveProfile.disabled = false;
  }
}

function formField(name) {
  return els.productForm.elements.namedItem(name);
}

function openEditor(item = null) {
  els.productForm.reset();
  formField("id").value = item?.id || "";
  formField("source_type").value = item?.source_type || "custom";
  formField("product_handle").value = item?.product_handle || `custom-${crypto.randomUUID()}`;
  formField("product_name").value = item?.product_name || "";
  formField("article_number").value = item?.article_number || "";
  formField("category").value = item?.category || "";
  formField("sale_price_nok").value = item?.sale_price_nok ?? "";
  formField("quantity").value = item?.quantity ?? 1;
  formField("description").value = item?.description || "";
  formField("image_url").value = item?.image_url || "";
  formField("source_product_url").value = item?.source_product_url || "";
  formField("is_for_sale").checked = item ? Boolean(item.is_for_sale) : true;
  const isOfficial = formField("source_type").value === "official";
  els.editorEyebrow.textContent = isOfficial ? "KOPIERT FRA TUPPERWARE" : "KONSULENTENS EGEN VARE";
  els.editorTitle.textContent = item ? "Rediger vare" : "Opprett vare";
  els.deleteProduct.hidden = !item;
  els.productEditor.showModal();
  refreshIcons();
}

async function uploadImage(file) {
  if (!file?.size) return "";
  if (file.size > 5 * 1024 * 1024) throw new Error("Bildet kan ikke være større enn 5 MB.");
  const extension = (file.name.split(".").pop() || "jpg").toLowerCase().replace(/[^a-z0-9]/g, "");
  const filename = `${state.consultant.id}/${crypto.randomUUID()}.${extension}`;
  const response = await fetch(
    `${state.config.supabaseUrl}/storage/v1/object/consultant-products/${filename}`,
    {
      method: "POST",
      headers: {
        apikey: state.config.supabaseAnonKey,
        Authorization: `Bearer ${state.session.access_token}`,
        "Content-Type": file.type,
        "x-upsert": "false",
      },
      body: file,
    },
  );
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.message || "Kunne ikke laste opp bildet.");
  return `${state.config.supabaseUrl}/storage/v1/object/public/consultant-products/${filename}`;
}

async function saveProduct(event) {
  event.preventDefault();
  els.saveProduct.disabled = true;
  const id = formField("id").value;
  try {
    const uploadedImage = await uploadImage(formField("image_file").files[0]);
    const body = {
      consultant_id: state.consultant.id,
      source_type: formField("source_type").value,
      product_handle: formField("product_handle").value,
      product_name: formField("product_name").value.trim(),
      article_number: formField("article_number").value.trim() || null,
      category: formField("category").value.trim() || null,
      sale_price_nok: Number(formField("sale_price_nok").value),
      quantity: Number(formField("quantity").value),
      description: formField("description").value.trim() || null,
      image_url: uploadedImage || formField("image_url").value.trim() || null,
      source_product_url: formField("source_product_url").value.trim() || null,
      is_for_sale: formField("is_for_sale").checked,
      is_active: true,
    };
    const url = id
      ? `${state.config.supabaseUrl}/rest/v1/inventory?id=eq.${encodeURIComponent(id)}`
      : `${state.config.supabaseUrl}/rest/v1/inventory`;
    await jsonRequest(url, {
      method: id ? "PATCH" : "POST",
      headers: supabaseHeaders({ Prefer: "return=minimal" }),
      body: JSON.stringify(body),
    });
    els.productEditor.close();
    await loadInventory();
    showToast("Varen er lagret.");
  } catch (error) {
    showToast(error.message);
  } finally {
    els.saveProduct.disabled = false;
  }
}

async function deleteProduct() {
  const id = formField("id").value;
  if (!id || !window.confirm("Vil du slette varen fra din egen katalog?")) return;
  try {
    await jsonRequest(
      `${state.config.supabaseUrl}/rest/v1/inventory?id=eq.${encodeURIComponent(id)}`,
      { method: "DELETE", headers: supabaseHeaders({ Prefer: "return=minimal" }) },
    );
    els.productEditor.close();
    await loadInventory();
    showToast("Varen er slettet.");
  } catch (error) {
    showToast(error.message);
  }
}

function officialResult(product) {
  return `
    <article class="official-result">
      ${product.image ? `<img src="${escapeHtml(product.image)}" alt="">` : `<span></span>`}
      <div>
        <strong>${escapeHtml(product.title)}</strong>
        <small>Art.nr. ${escapeHtml(product.articleNumber || "ikke oppgitt")} · ${formatNok(product.price)}</small>
      </div>
      <button type="button" data-official="${escapeHtml(product.handle)}">Bruk som utgangspunkt</button>
    </article>`;
}

async function searchOfficial(event) {
  event.preventDefault();
  const query = els.officialSearchInput.value.trim();
  if (!query) return;
  els.officialResults.innerHTML = "<p>Søker i Tupperwares produkter ...</p>";
  try {
    const payload = await jsonRequest(`/api/products?q=${encodeURIComponent(query)}&limit=30&sort=title`);
    state.officialProducts = payload.products || [];
    els.officialResults.innerHTML = state.officialProducts.length
      ? state.officialProducts.map(officialResult).join("")
      : "<p>Ingen produkter passer søket.</p>";
  } catch (error) {
    els.officialResults.innerHTML = `<p>${escapeHtml(error.message)}</p>`;
  }
}

function chooseOfficial(handle) {
  const product = state.officialProducts.find(item => item.handle === handle);
  if (!product) return;
  els.officialPicker.close();
  openEditor({
    source_type: "official",
    product_handle: product.handle,
    product_name: product.title,
    article_number: product.articleNumber,
    description: product.description,
    image_url: product.image,
    source_product_url: product.url,
    sale_price_nok: product.price,
    quantity: 1,
    is_for_sale: true,
  });
}

async function updateOrderStatus(orderId, status) {
  try {
    await jsonRequest(
      `${state.config.supabaseUrl}/rest/v1/order_requests?id=eq.${encodeURIComponent(orderId)}`,
      {
        method: "PATCH",
        headers: supabaseHeaders({ Prefer: "return=minimal" }),
        body: JSON.stringify({ status }),
      },
    );
    await loadOrders();
    showToast("Bestillingsstatus er oppdatert.");
  } catch (error) {
    showToast(error.message);
  }
}

async function initializeAuthenticated() {
  await loadConsultant();
  await loadProductAccess();
  showManageView();
  await Promise.all([loadInventory(), loadOrders()]);
}

els.loginForm.addEventListener("submit", async event => {
  event.preventDefault();
  const form = new FormData(els.loginForm);
  els.loginButton.disabled = true;
  els.loginMessage.textContent = "Logger inn ...";
  try {
    saveSession(await login(form.get("email"), form.get("password")));
    await initializeAuthenticated();
    els.loginMessage.textContent = "";
  } catch (error) {
    clearSession();
    els.loginMessage.textContent = error.message;
  } finally {
    els.loginButton.disabled = false;
  }
});
els.resetPasswordButton.addEventListener("click", async () => {
  const email = String(new FormData(els.loginForm).get("email") || "").trim();
  if (!email) {
    els.loginMessage.textContent = "Skriv inn e-postadressen først.";
    return;
  }
  els.resetPasswordButton.disabled = true;
  els.loginMessage.textContent = "Sender passordlenke ...";
  try {
    await requestPasswordRecovery(email);
    els.loginMessage.textContent = "Passordlenken er sendt. Se også i søppelpost.";
  } catch (error) {
    els.loginMessage.textContent = error.message;
  } finally {
    els.resetPasswordButton.disabled = false;
  }
});
els.passwordSetupForm.addEventListener("submit", async event => {
  event.preventDefault();
  const form = new FormData(els.passwordSetupForm);
  const password = String(form.get("password") || "");
  const confirmation = String(form.get("password_confirm") || "");
  if (password !== confirmation) {
    els.passwordSetupMessage.textContent = "Passordene er ikke like.";
    return;
  }
  els.passwordSetupButton.disabled = true;
  els.passwordSetupMessage.textContent = "Lagrer passord ...";
  try {
    const user = await updatePassword(password);
    saveSession({ ...state.session, user });
    history.replaceState(null, "", `${location.pathname}${location.search}`);
    await initializeAuthenticated();
    els.passwordSetupMessage.textContent = "";
  } catch (error) {
    els.passwordSetupMessage.textContent = error.message;
  } finally {
    els.passwordSetupButton.disabled = false;
  }
});
els.logoutButton.addEventListener("click", () => {
  clearSession();
  location.reload();
});
document.querySelector(".manage-tabs").addEventListener("click", event => {
  const button = event.target.closest("[data-view]");
  if (!button) return;
  document.querySelectorAll(".manage-tabs button").forEach(item => item.classList.toggle("active", item === button));
  els.inventoryView.hidden = button.dataset.view !== "inventory";
  els.ordersView.hidden = button.dataset.view !== "orders";
  els.profileView.hidden = button.dataset.view !== "profile";
  els.reportView.hidden = button.dataset.view !== "report";
});
els.addCustomProduct.addEventListener("click", () => openEditor());
els.addFromTupperware.addEventListener("click", () => {
  els.officialSearchInput.value = "";
  els.officialResults.innerHTML = "<p>Søk etter produktet du har på eget lager.</p>";
  els.officialPicker.showModal();
});
els.closeEditor.addEventListener("click", () => els.productEditor.close());
els.closeOfficialPicker.addEventListener("click", () => els.officialPicker.close());
els.productForm.addEventListener("submit", saveProduct);
els.deleteProduct.addEventListener("click", deleteProduct);
els.inventoryList.addEventListener("click", event => {
  const button = event.target.closest("[data-edit]");
  if (button) openEditor(state.inventory.find(item => item.id === button.dataset.edit));
});
els.officialSearchForm.addEventListener("submit", searchOfficial);
els.officialResults.addEventListener("click", event => {
  const button = event.target.closest("[data-official]");
  if (button) chooseOfficial(button.dataset.official);
});
els.orderList.addEventListener("change", event => {
  const select = event.target.closest("[data-order-status]");
  if (select) updateOrderStatus(select.dataset.orderStatus, select.value);
});
els.refreshOrders.addEventListener("click", loadOrders);
els.profileForm.addEventListener("submit", saveProfile);
els.printInventoryReport.addEventListener("click", () => {
  document.body.classList.add("printing-inventory-report");
  window.print();
});
window.addEventListener("afterprint", () => document.body.classList.remove("printing-inventory-report"));
profileField("profile_image_file").addEventListener("change", event => {
  const file = event.target.files[0];
  renderProfilePhoto(file ? URL.createObjectURL(file) : state.consultant?.profile_image_url);
});
profileField("own_shop_enabled").addEventListener("change", updateShopSettingsState);
profileField("own_shop_access_mode").addEventListener("change", updateShopSettingsState);

(async () => {
  refreshIcons();
  try {
    await loadConfig();
    if (await restoreAuthLink()) return;
    const session = restoredSession();
    if (session) {
      saveSession(session);
      await initializeAuthenticated();
    }
  } catch (error) {
    clearSession();
    els.loginMessage.textContent = error.message;
  }
})();
