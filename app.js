const pageParams = new URLSearchParams(window.location.search);

function cleanConsultantRef(value) {
  const cleaned = String(value || "").trim().replace(/[^a-zA-Z0-9_-]/g, "");
  return cleaned.slice(0, 80);
}

function cleanConsultantName(value) {
  return String(value || "").trim().replace(/\s+/g, " ").slice(0, 80);
}

function storedConsultantRef() {
  try {
    return cleanConsultantRef(localStorage.getItem("tupperwareConsultantRef"));
  } catch {
    return "";
  }
}

const requestedConsultantRef = cleanConsultantRef(pageParams.get("ref")) || storedConsultantRef();
const suppliedConsultantName = cleanConsultantName(pageParams.get("consultant"));
let activeConsultantRef = requestedConsultantRef;
let consultantName = suppliedConsultantName;
let ownCatalogRequest = 0;
let superAdminMode = false;

const state = {
  collections: [],
  series: [],
  activeGroup: null,
  activeCollection: "",
  activeSeries: null,
  query: "",
  sort: "newest",
  status: "all",
  request: 0,
  offset: 0,
  total: 0,
};

const els = {
  categoryNav: document.querySelector("#categoryNav"),
  categoryPanel: document.querySelector("#categoryPanel"),
  menuButton: document.querySelector("#menuButton"),
  closeMenuButton: document.querySelector("#closeMenuButton"),
  menuBackdrop: document.querySelector("#menuBackdrop"),
  homeButton: document.querySelector("#homeButton"),
  searchForm: document.querySelector("#searchForm"),
  searchInput: document.querySelector("#searchInput"),
  clearSearch: document.querySelector("#clearSearch"),
  seriesInput: document.querySelector("#seriesInput"),
  seriesOptions: document.querySelector("#seriesOptions"),
  clearSeries: document.querySelector("#clearSeries"),
  mobileSearchForm: document.querySelector("#mobileSearchForm"),
  mobileSearchInput: document.querySelector("#mobileSearchInput"),
  pageTitle: document.querySelector("#pageTitle"),
  pageDescription: document.querySelector("#pageDescription"),
  subcategoryStrip: document.querySelector("#subcategoryStrip"),
  statusSelect: document.querySelector("#statusSelect"),
  sortSelect: document.querySelector("#sortSelect"),
  resetFilters: document.querySelector("#resetFilters"),
  resultCount: document.querySelector("#resultCount"),
  activeFilter: document.querySelector("#activeFilter"),
  productGrid: document.querySelector("#productGrid"),
  loadMoreButton: document.querySelector("#loadMoreButton"),
  productDialog: document.querySelector("#productDialog"),
  dialogContent: document.querySelector("#dialogContent"),
  dialogClose: document.querySelector("#dialogClose"),
  toast: document.querySelector("#toast"),
  consultantMessage: document.querySelector("#consultantMessage"),
  consultantRef: document.querySelector("#consultantRef"),
  consultantBanner: document.querySelector("#consultantBanner"),
  chooseConsultantBanner: document.querySelector("#chooseConsultantBanner"),
  ownCatalogLink: document.querySelector("#ownCatalogLink"),
  officialSourceLink: document.querySelector("#officialSourceLink"),
  consultantDialog: document.querySelector("#consultantDialog"),
  consultantDialogClose: document.querySelector("#consultantDialogClose"),
  consultantSearchForm: document.querySelector("#consultantSearchForm"),
  consultantSearchInput: document.querySelector("#consultantSearchInput"),
  consultantResults: document.querySelector("#consultantResults"),
  withoutConsultant: document.querySelector("#withoutConsultant"),
  inAppWarning: document.querySelector("#inAppWarning"),
  copyCatalogLink: document.querySelector("#copyCatalogLink"),
  closeInAppWarning: document.querySelector("#closeInAppWarning"),
};

const descriptions = {
  "": "Finn Tupperware-produktet som passer hverdagen din.",
  "special-sales": "Aktuelle tilbud og kampanjeprodukter samlet på ett sted.",
  conservation: "Smarte løsninger som holder maten organisert og frisk lenger.",
  preparation: "Redskaper og hjelpere for enklere, raskere matforberedelse.",
  "cooking-and-reheatable": "Produkter for tilberedning, oppvarming og gode resultater.",
  "serving-and-entertaining": "Praktiske og pene produkter til bord og servering.",
  "on-the-go": "Ta med mat og drikke trygt, ryddig og praktisk.",
  other: "Produkter til hjemmet, familien og flere bruksområder.",
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  }[char]));
}

function formatNok(value) {
  return new Intl.NumberFormat("nb-NO", {
    style: "currency",
    currency: "NOK",
    minimumFractionDigits: Number(value) % 1 ? 2 : 0,
    maximumFractionDigits: 2,
  }).format(Number(value || 0));
}

function productUrl(value) {
  try {
    const url = new URL(value);
    if (url.hostname === "tupperware-eu.com" || url.hostname.endsWith(".tupperware-eu.com")) {
      const productMatch = url.pathname.match(/\/(?:[a-z]{2}(?:-[a-z]{2})?\/)?products\/(.+)$/i);
      if (productMatch) {
        url.pathname = `/no/products/${productMatch[1]}`;
      } else if (url.pathname === "" || url.pathname === "/") {
        url.pathname = "/no/";
      } else if (url.pathname !== "/no" && !url.pathname.startsWith("/no/")) {
        url.pathname = `/no${url.pathname.startsWith("/") ? url.pathname : `/${url.pathname}`}`;
      }
      if (activeConsultantRef) {
        url.searchParams.set("ref", activeConsultantRef);
      } else {
        url.searchParams.delete("ref");
      }
    }
    return url.toString();
  } catch {
    return value;
  }
}

function openOfficialStore(url) {
  const storeTab = window.open(productUrl(url), "tupperware-official-store");
  if (!storeTab) return false;
  storeTab.focus();
  return true;
}

function refreshProductLinks() {
  document.querySelectorAll("a.shop-button[href]").forEach(link => {
    link.href = productUrl(link.href);
  });
  document.querySelectorAll("[data-copy]").forEach(button => {
    button.dataset.copy = productUrl(button.dataset.copy);
  });
}

function showConsultant(name, refText, status = "") {
  consultantName = name;
  const hasConsultant = Boolean(activeConsultantRef);
  els.consultantMessage.innerHTML = hasConsultant
    ? `Du handler med Tupperware-konsulent <strong>${escapeHtml(name)}</strong>`
    : escapeHtml(name);
  els.consultantRef.textContent = refText;
  els.chooseConsultantBanner.textContent = hasConsultant ? "Endre" : "Velg konsulent";
  els.ownCatalogLink.hidden = true;
  els.ownCatalogLink.href = hasConsultant
    ? `/egne-varer?ref=${encodeURIComponent(activeConsultantRef)}`
    : "/egne-varer";
  els.officialSourceLink.href = productUrl("https://tupperware-eu.com/no");
  els.consultantBanner.classList.toggle("neutral", !hasConsultant && !status);
  els.consultantBanner.classList.toggle("invalid", status === "invalid");
  els.consultantBanner.classList.toggle("unverified", status === "unverified");
}

function restoredSuperAdminSession() {
  try {
    const session = JSON.parse(sessionStorage.getItem("consultantManageSession") || "null");
    if (session?.access_token && session?.user?.id) return session;
  } catch {
    // The public catalog remains locked when the session cannot be read.
  }
  return null;
}

async function initializeSuperAdminControls() {
  const session = restoredSuperAdminSession();
  if (!session) return;

  try {
    const config = await fetchJson("/api/public-config");
    if (!config.configured || !config.supabaseUrl || !config.supabaseAnonKey) return;
    const response = await fetch(
      `${config.supabaseUrl}/rest/v1/admin_users?select=is_super_admin&user_id=eq.${encodeURIComponent(session.user.id)}&limit=1`,
      {
        headers: {
          apikey: config.supabaseAnonKey,
          Authorization: `Bearer ${session.access_token}`,
        },
      },
    );
    if (!response.ok) return;
    const rows = await response.json();
    if (!rows[0]?.is_super_admin) return;
    superAdminMode = true;
    els.chooseConsultantBanner.hidden = false;
  } catch {
    // Customers and consultants must never receive the consultant switcher by accident.
  }
}

async function refreshOwnCatalogLink() {
  const request = ++ownCatalogRequest;
  const referenceCode = activeConsultantRef;
  els.ownCatalogLink.hidden = true;
  if (!referenceCode) return;

  try {
    const payload = await fetchJson(`/api/shop-status?ref=${encodeURIComponent(referenceCode)}`);
    if (request !== ownCatalogRequest || referenceCode !== activeConsultantRef) return;
    els.ownCatalogLink.href = `/egne-varer?ref=${encodeURIComponent(referenceCode)}`;
    els.ownCatalogLink.hidden = !(payload.enabled && payload.hasProducts);
  } catch {
    // The shop is only shown after its inventory has been confirmed.
  }
}

async function loadConsultant() {
  if (!requestedConsultantRef) {
    activeConsultantRef = "";
    showConsultant("Du har ikke valgt Tupperware-konsulent", "");
    return;
  }
  showConsultant("Kontrollerer konsulent ...", `Ref. ${requestedConsultantRef}`);
  try {
    const payload = await fetchJson(`/api/consultant?ref=${encodeURIComponent(requestedConsultantRef)}`);
    if (!payload.found) {
      activeConsultantRef = "";
      showConsultant("Konsulentreferansen finnes ikke", `Ugyldig ref. ${requestedConsultantRef}`, "invalid");
      return;
    }
    activeConsultantRef = payload.ref;
    showConsultant(
      payload.name || suppliedConsultantName || "Tupperware-konsulent",
      `Ref. ${payload.ref}`,
      "",
    );
    await refreshOwnCatalogLink();
  } catch {
    activeConsultantRef = requestedConsultantRef;
    showConsultant(
      suppliedConsultantName || "Valgt konsulent",
      `Ref. ${requestedConsultantRef} kunne ikke kontrolleres`,
      "unverified",
    );
    await refreshOwnCatalogLink();
  }
}

function consultantLocation(consultant) {
  return [consultant.municipality, consultant.county].filter(Boolean).join(", ");
}

function consultantResult(consultant) {
  const location = consultantLocation(consultant);
  const initials = consultant.display_name
    .split(/\s+/)
    .slice(0, 2)
    .map(part => part.charAt(0))
    .join("")
    .toUpperCase();
  return `
    <button class="consultant-result" type="button"
      data-consultant-ref="${escapeHtml(consultant.reference_code)}"
      data-consultant-name="${escapeHtml(consultant.display_name)}">
      <span class="consultant-avatar">
        ${consultant.profile_image_url
          ? `<img src="${escapeHtml(consultant.profile_image_url)}" alt="">`
          : escapeHtml(initials)}
      </span>
      <span class="consultant-result-text">
        <strong>${escapeHtml(consultant.display_name)}</strong>
        <small>${escapeHtml(location || `Ref. ${consultant.reference_code}`)}</small>
      </span>
      <i data-lucide="chevron-right"></i>
    </button>`;
}

async function loadConsultantChoices(search = "") {
  els.consultantResults.innerHTML = `<div class="consultant-loading">Laster konsulenter ...</div>`;
  try {
    const params = new URLSearchParams({ limit: "50" });
    if (search.trim()) params.set("q", search.trim());
    const payload = await fetchJson(`/api/consultants?${params}`);
    els.consultantResults.innerHTML = payload.consultants.length
      ? payload.consultants.map(consultantResult).join("")
      : `<div class="consultant-empty">Ingen konsulenter passer søket.</div>`;
    refreshIcons();
  } catch (error) {
    els.consultantResults.innerHTML = `
      <div class="consultant-empty">Kunne ikke hente konsulentene. ${escapeHtml(error.message)}</div>`;
  }
}

function openConsultantPicker() {
  if (!superAdminMode) return;
  els.consultantDialog.showModal();
  els.consultantSearchInput.value = "";
  loadConsultantChoices();
  window.setTimeout(() => els.consultantSearchInput.focus(), 0);
}

function rememberConsultant(ref, name = "") {
  activeConsultantRef = cleanConsultantRef(ref);
  consultantName = cleanConsultantName(name);
  const url = new URL(window.location.href);
  if (activeConsultantRef) {
    url.searchParams.set("ref", activeConsultantRef);
  } else {
    url.searchParams.delete("ref");
  }
  url.searchParams.delete("consultant");
  window.history.replaceState({}, "", url);
  try {
    if (activeConsultantRef) {
      localStorage.setItem("tupperwareConsultantRef", activeConsultantRef);
    } else {
      localStorage.removeItem("tupperwareConsultantRef");
    }
  } catch {
    // The URL still keeps the selected consultant when storage is unavailable.
  }
}

async function chooseConsultant(ref, name) {
  if (!superAdminMode) return;
  rememberConsultant(ref, name);
  els.consultantDialog.close();
  showConsultant(name, `Ref. ${activeConsultantRef}`);
  try {
    const payload = await fetchJson(`/api/consultant?ref=${encodeURIComponent(activeConsultantRef)}`);
    if (payload.found) {
      showConsultant(payload.name || name, `Ref. ${payload.ref}`);
    }
  } catch {
    showConsultant(name, `Ref. ${activeConsultantRef} kunne ikke kontrolleres`, "unverified");
  }
  await refreshOwnCatalogLink();
  refreshProductLinks();
  showToast(`${name} er valgt som konsulent.`);
}

function clearConsultant() {
  if (!superAdminMode) return;
  rememberConsultant("");
  els.consultantDialog.close();
  showConsultant("Du har ikke valgt Tupperware-konsulent", "");
  refreshProductLinks();
  showToast("Du fortsetter uten valgt konsulent.");
}

function discountPercent(product) {
  if (!product.compareAtPrice || product.compareAtPrice <= product.price) return 0;
  return Math.round((1 - product.price / product.compareAtPrice) * 100);
}

function refreshIcons() {
  if (window.lucide) window.lucide.createIcons();
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => els.toast.classList.remove("show"), 2600);
}

function isMetaInAppBrowser() {
  const userAgent = navigator.userAgent || navigator.vendor || "";
  return /FBAN|FBAV|FB_IAB|Messenger|Instagram/i.test(userAgent)
    || pageParams.get("inapp-preview") === "1";
}

function catalogShareUrl() {
  const url = new URL(window.location.href);
  url.searchParams.delete("inapp-preview");
  return url.toString();
}

async function copyText(value) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }
  const input = document.createElement("textarea");
  input.value = value;
  input.setAttribute("readonly", "");
  input.style.position = "fixed";
  input.style.opacity = "0";
  document.body.appendChild(input);
  input.select();
  document.execCommand("copy");
  input.remove();
}

function setupInAppWarning() {
  if (!isMetaInAppBrowser()) return;
  try {
    if (sessionStorage.getItem("inAppWarningDismissed") === "1") return;
  } catch {
    // The warning still works when storage is unavailable.
  }
  els.inAppWarning.hidden = false;
}

async function fetchJson(url) {
  const response = await fetch(url);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || "Kunne ikke hente butikkdata.");
  return payload;
}

function selectedGroup() {
  return state.collections.find(group => group.handle === state.activeGroup) || state.collections[0];
}

function seriesSearchKey(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

const seriesPickers = [
  { input: els.seriesInput, options: els.seriesOptions, clear: els.clearSeries },
];

function syncSeriesPickers() {
  const title = state.activeSeries?.title || "";
  seriesPickers.forEach(({ input, clear }) => {
    input.value = title;
    input.closest("[data-series-picker]")?.classList.toggle("has-value", Boolean(title));
    clear.hidden = !title;
  });
}

function closeSeriesPickers() {
  seriesPickers.forEach(({ input, options }) => {
    options.hidden = true;
    input.setAttribute("aria-expanded", "false");
  });
}

function renderSeriesOptions(picker, search = "") {
  const words = seriesSearchKey(search).split(" ").filter(Boolean);
  const matches = state.series.filter(series => {
    const key = seriesSearchKey(series.title);
    return words.every(word => key.includes(word));
  });
  picker.options.innerHTML = matches.length
    ? matches.map(series => `
      <button type="button" role="option"
        aria-selected="${state.activeSeries?.title === series.title}"
        data-series="${escapeHtml(series.title)}">
        <span>${escapeHtml(series.title)}</span>
        <small>${series.count} ${series.count === 1 ? "produkt" : "produkter"}</small>
        ${state.activeSeries?.title === series.title ? `<i data-lucide="check"></i>` : ""}
      </button>`).join("")
    : `<p>Ingen serier passer søket.</p>`;
  picker.options.hidden = false;
  picker.input.setAttribute("aria-expanded", "true");
  refreshIcons();
}

function renderNavigation() {
  els.categoryNav.innerHTML = state.collections.map((group, index) => {
    const open = group.handle === state.activeGroup;
    const active = state.activeCollection === group.handle || (!state.activeCollection && index === 0);
    if (!group.children.length) {
      return `
        <div class="nav-group">
          <button class="nav-main ${active ? "active" : ""}" data-collection="" data-group="">
            <span>${escapeHtml(group.title)}</span>
          </button>
        </div>`;
    }
    return `
      <div class="nav-group ${open ? "open" : ""}" data-nav-group="${escapeHtml(group.handle)}">
        <button class="nav-main ${active ? "active" : ""}" data-collection="${escapeHtml(group.handle)}" data-group="${escapeHtml(group.handle)}">
          <span>${escapeHtml(group.title)}</span>
          <i data-lucide="chevron-down"></i>
        </button>
        <div class="nav-children">
          ${group.children.map(child => `
            <button class="nav-child ${state.activeCollection === child.handle ? "active" : ""}"
              data-collection="${escapeHtml(child.handle)}"
              data-group="${escapeHtml(group.handle)}">${escapeHtml(child.title)}</button>
          `).join("")}
        </div>
      </div>`;
  }).join("");
  refreshIcons();
}

function renderSubcategories() {
  if (state.activeSeries) {
    els.subcategoryStrip.innerHTML = "";
    return;
  }
  const group = selectedGroup();
  if (!group?.children?.length) {
    els.subcategoryStrip.innerHTML = "";
    return;
  }
  els.subcategoryStrip.innerHTML = [
    `<button class="subcategory ${state.activeCollection === group.handle ? "active" : ""}"
      data-collection="${escapeHtml(group.handle)}">${escapeHtml(group.title)}</button>`,
    ...group.children.map(child => `
      <button class="subcategory ${state.activeCollection === child.handle ? "active" : ""}"
        data-collection="${escapeHtml(child.handle)}">${escapeHtml(child.title)}</button>`),
  ].join("");
}

function hasActiveCatalogFilters() {
  return Boolean(
    state.query
    || state.activeCollection
    || state.activeGroup
    || state.activeSeries
    || state.status !== "all"
    || state.sort !== "newest"
  );
}

function syncResetButton() {
  els.resetFilters.hidden = !hasActiveCatalogFilters();
}

function updateHeading() {
  const group = selectedGroup();
  const child = group?.children?.find(item => item.handle === state.activeCollection);
  const statusTitles = {
    active: "Tilgjengelige produkter",
    "temporarily-unavailable": "Midlertidig utsolgt",
    "not-in-current-assortment": "Ikke i dagens sortiment",
  };
  const title = state.query
    ? `Søkeresultater`
    : state.activeSeries?.title || child?.title || statusTitles[state.status] || group?.title || "Alle produkter";
  els.pageTitle.textContent = title;
  if (state.query && state.activeSeries) {
    els.pageDescription.textContent = `Produkter som passer søket «${state.query}» i ${state.activeSeries.title}.`;
  } else if (state.query) {
    els.pageDescription.textContent = `Produkter som passer søket «${state.query}».`;
  } else if (state.activeSeries) {
    els.pageDescription.textContent = `Alle tilgjengelige produkter i ${state.activeSeries.title}.`;
  } else {
    els.pageDescription.textContent = descriptions[group?.handle || ""] || "Utforsk den norske Tupperware-katalogen.";
  }
  const contextLabel = state.activeSeries
    ? `i ${state.activeSeries.title}`
    : child ? `i ${group.title}` : "";
  const statusLabels = {
    active: "tilgjengelige",
    "temporarily-unavailable": "midlertidig utsolgte",
    "not-in-current-assortment": "ikke i dagens sortiment",
  };
  els.activeFilter.textContent = [statusLabels[state.status], contextLabel].filter(Boolean).join(" ");
  syncResetButton();
}

function productCard(product) {
  const archived = product.isInOfficialCatalog === false;
  const discount = archived ? 0 : discountPercent(product);
  const addedAt = product.createdAt || product.publishedAt || product.firstSeenAt;
  const addedDate = addedAt ? new Date(addedAt) : null;
  const ageInDays = addedDate && !Number.isNaN(addedDate.getTime())
    ? (Date.now() - addedDate.getTime()) / 86400000
    : null;
  const isNew = !archived && (
    (ageInDays !== null && ageInDays >= 0 && ageInDays <= 7)
    || product.tags.some(tag => tag.toLowerCase() === "new")
  );
  const addedLabel = addedDate && !Number.isNaN(addedDate.getTime())
    ? addedDate.toLocaleDateString("nb-NO", { day: "numeric", month: "long", year: "numeric" })
    : "";
  const updatedAt = archived
    ? product.removedAt || product.lastSeenAt
    : product.sourceUpdatedAt || product.publishedAt;
  const updatedDate = updatedAt ? new Date(updatedAt) : null;
  const updatedLabel = updatedDate && !Number.isNaN(updatedDate.getTime())
    ? updatedDate.toLocaleDateString("nb-NO", { day: "numeric", month: "long", year: "numeric" })
    : "";
  const lastSeenDate = archived && product.lastSeenAt ? new Date(product.lastSeenAt) : null;
  const lastSeenLabel = lastSeenDate && !Number.isNaN(lastSeenDate.getTime())
    ? lastSeenDate.toLocaleDateString("nb-NO", { day: "numeric", month: "long", year: "numeric" })
    : "";
  const shopUrl = productUrl(product.url);
  const showSeriesLink = product.series
    && state.activeSeries?.title !== product.series
    && state.series.some(series => series.title === product.series);
  return `
    <article class="product-card ${archived ? "archived-product" : ""}" data-handle="${escapeHtml(product.handle)}">
      <div class="product-badges">
        ${archived ? `<span class="badge archived">Ikke i dagens sortiment</span>` : ""}
        ${discount ? `<span class="badge sale">-${discount}%</span>` : ""}
        ${isNew ? `<span class="badge new">Nyhet</span>` : ""}
      </div>
      <button class="product-image" data-detail="${escapeHtml(product.handle)}" aria-label="Vis ${escapeHtml(product.title)}">
        ${product.image
          ? `<img src="${escapeHtml(product.image)}" alt="${escapeHtml(product.title)}" loading="lazy">`
          : `<span class="image-placeholder"><i data-lucide="image"></i></span>`}
      </button>
      <div class="product-meta">
        <div class="card-status-row">
          ${archived
            ? `<div class="stock archived-status">Ikke i dagens sortiment</div>`
            : `<div class="stock ${product.available ? "" : "out"}">${product.available ? "På lager" : "Ikke på lager"}</div>`}
          ${showSeriesLink ? `
            <button class="series-link-button" type="button"
              data-product-series="${escapeHtml(product.series)}"
              aria-label="Vis flere produkter i ${escapeHtml(product.series)}"
              title="Flere produkter i ${escapeHtml(product.series)}">
              <i data-lucide="layout-grid"></i>
            </button>` : ""}
        </div>
        <h2 class="product-title">${escapeHtml(product.title)}</h2>
        <div class="article-number">Art.nr. ${escapeHtml(product.articleNumber || "ikke oppgitt")}</div>
        ${addedLabel ? `<div class="product-date">${archived ? "Registrert" : "Lagt til"} ${escapeHtml(addedLabel)}</div>` : ""}
        ${lastSeenLabel ? `<div class="product-date">Sist sett i nettbutikken ${escapeHtml(lastSeenLabel)}</div>` : ""}
        ${updatedLabel ? `<div class="product-date">Sist endret ${escapeHtml(updatedLabel)}</div>` : ""}
        <div class="price-row">
          <span class="price">${formatNok(product.price)}</span>
          ${archived ? `<span class="last-price-label">Sist registrerte pris</span>` : ""}
          ${!archived && product.compareAtPrice ? `<span class="compare-price">${formatNok(product.compareAtPrice)}</span>` : ""}
          ${discount ? `<span class="discount">Spar ${discount}%</span>` : ""}
        </div>
        ${archived ? `
          <button class="archive-detail-button" data-detail="${escapeHtml(product.handle)}">
            <i data-lucide="archive"></i> Se produktinformasjon
          </button>` : `
          <div class="product-actions">
            <button class="icon-button" data-detail="${escapeHtml(product.handle)}" aria-label="Vis produktdetaljer" title="Produktdetaljer">
              <i data-lucide="eye"></i>
            </button>
            <a class="shop-button" href="${escapeHtml(shopUrl)}" target="tupperware-official-store">
              Se hos Tupperware <i data-lucide="external-link"></i>
            </a>
          </div>`}
      </div>
    </article>`;
}

function renderLoading() {
  els.productGrid.innerHTML = Array.from({ length: 8 }, () => `<div class="product-skeleton"></div>`).join("");
  els.resultCount.textContent = "Laster produkter ...";
}

function renderEmpty() {
  els.productGrid.innerHTML = `
    <div class="empty-state">
      <i data-lucide="search-x"></i>
      <h2>Ingen produkter funnet</h2>
      <p>Prøv et kortere søkeord eller velg en annen kategori.</p>
    </div>`;
  refreshIcons();
}

function renderError(error) {
  els.productGrid.innerHTML = `
    <div class="error-state">
      <i data-lucide="wifi-off"></i>
      <h2>Kunne ikke hente produktene</h2>
      <p>${escapeHtml(error.message)}</p>
    </div>`;
  els.resultCount.textContent = "Butikkdata utilgjengelig";
  refreshIcons();
}

function pageSize() {
  return window.matchMedia("(max-width: 820px)").matches ? 24 : 48;
}

async function loadProducts({ append = false } = {}) {
  const request = ++state.request;
  if (!append) {
    state.offset = 0;
    renderLoading();
  } else {
    els.loadMoreButton.disabled = true;
    els.loadMoreButton.textContent = "Laster flere ...";
  }
  updateHeading();
  const params = new URLSearchParams({
    sort: state.sort,
    status: state.status,
    offset: String(state.offset),
    limit: String(pageSize()),
  });
  if (state.activeCollection) params.set("collection", state.activeCollection);
  if (state.activeSeries) params.set("series", state.activeSeries.title);
  if (state.query) {
    params.set("q", state.query);
  }
  try {
    const payload = await fetchJson(`/api/products?${params}`);
    if (request !== state.request) return;
    state.total = payload.count;
    els.resultCount.textContent = `${payload.count} ${payload.count === 1 ? "produkt" : "produkter"}`;
    if (!payload.products.length && !append) {
      els.loadMoreButton.hidden = true;
      return renderEmpty();
    }
    const cards = payload.products.map(productCard).join("");
    if (append) {
      els.productGrid.insertAdjacentHTML("beforeend", cards);
    } else {
      els.productGrid.innerHTML = cards;
    }
    state.offset += payload.products.length;
    els.loadMoreButton.hidden = state.offset >= payload.count;
    els.loadMoreButton.disabled = false;
    els.loadMoreButton.innerHTML = `Vis flere produkter <i data-lucide="chevron-down"></i>`;
    refreshIcons();
  } catch (error) {
    if (request === state.request) {
      els.loadMoreButton.hidden = true;
      renderError(error);
    }
  }
}

function chooseCollection(collection, group) {
  if (collection && state.status === "not-in-current-assortment") {
    state.status = "all";
    els.statusSelect.value = "all";
  }
  state.query = "";
  state.activeSeries = null;
  state.activeCollection = collection;
  state.activeGroup = group ?? collection;
  els.searchInput.value = "";
  els.mobileSearchInput.value = "";
  els.searchForm.classList.remove("has-value");
  syncSeriesPickers();
  closeSeriesPickers();
  renderNavigation();
  renderSubcategories();
  updateHeading();
  document.body.classList.remove("menu-open");
  loadProducts();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function chooseSeries(title) {
  const series = state.series.find(item => item.title === title);
  if (!series) return;
  state.query = "";
  state.activeSeries = series;
  state.activeCollection = "";
  state.activeGroup = null;
  els.searchInput.value = "";
  els.mobileSearchInput.value = "";
  els.searchForm.classList.remove("has-value");
  syncSeriesPickers();
  closeSeriesPickers();
  renderNavigation();
  renderSubcategories();
  updateHeading();
  document.body.classList.remove("menu-open");
  loadProducts();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function clearSeries() {
  if (!state.activeSeries) {
    seriesPickers.forEach(({ input }) => { input.value = ""; });
    closeSeriesPickers();
    return;
  }
  state.activeSeries = null;
  state.activeCollection = "";
  state.activeGroup = "";
  syncSeriesPickers();
  closeSeriesPickers();
  renderNavigation();
  renderSubcategories();
  updateHeading();
  loadProducts();
}

function runSearch(value) {
  state.query = value.trim();
  els.searchInput.value = state.query;
  els.mobileSearchInput.value = state.query;
  els.searchForm.classList.toggle("has-value", Boolean(state.query));
  updateHeading();
  loadProducts();
}

function resetCatalogView({ notify = true } = {}) {
  state.activeGroup = null;
  state.activeCollection = "";
  state.activeSeries = null;
  state.query = "";
  state.sort = "newest";
  state.status = "all";
  state.offset = 0;
  els.searchInput.value = "";
  els.mobileSearchInput.value = "";
  els.searchForm.classList.remove("has-value");
  els.statusSelect.value = "all";
  els.sortSelect.value = "newest";
  syncSeriesPickers();
  closeSeriesPickers();
  renderNavigation();
  renderSubcategories();
  updateHeading();
  document.body.classList.remove("menu-open");
  loadProducts();
  window.scrollTo({ top: 0, behavior: "smooth" });
  if (notify) showToast("Katalogvisningen er nullstilt.");
}

function detailMarkup(product) {
  const archived = product.isInOfficialCatalog === false;
  const discount = archived ? 0 : discountPercent(product);
  const images = product.images.length ? product.images : [""];
  const shopUrl = productUrl(product.url);
  const lastSeenDate = archived && product.lastSeenAt ? new Date(product.lastSeenAt) : null;
  const lastSeenLabel = lastSeenDate && !Number.isNaN(lastSeenDate.getTime())
    ? lastSeenDate.toLocaleDateString("nb-NO", { day: "numeric", month: "long", year: "numeric" })
    : "";
  return `
    <div class="detail-layout">
      <div class="detail-gallery">
        ${images[0]
          ? `<img class="detail-main-image" id="detailMainImage" src="${escapeHtml(images[0])}" alt="${escapeHtml(product.title)}">`
          : `<div class="detail-main-image image-placeholder"><i data-lucide="image"></i></div>`}
        ${images.length > 1 ? `
          <div class="thumbnails">
            ${images.map((image, index) => `
              <button class="thumbnail ${index === 0 ? "active" : ""}" data-image="${escapeHtml(image)}" aria-label="Vis bilde ${index + 1}">
                <img src="${escapeHtml(image)}" alt="">
              </button>`).join("")}
          </div>` : ""}
      </div>
      <div class="detail-info">
        ${archived
          ? `<div class="stock archived-status">Ikke i dagens sortiment</div>`
          : `<div class="stock ${product.available ? "" : "out"}">${product.available ? "På lager" : "Ikke på lager"}</div>`}
        <h2>${escapeHtml(product.title)}</h2>
        <div class="article-number">Artikkelnummer ${escapeHtml(product.articleNumber || "ikke oppgitt")}</div>
        <div class="detail-price price-row">
          <span class="price">${formatNok(product.price)}</span>
          ${archived ? `<span class="last-price-label">Sist registrerte pris</span>` : ""}
          ${!archived && product.compareAtPrice ? `<span class="compare-price">${formatNok(product.compareAtPrice)}</span>` : ""}
          ${discount ? `<span class="discount">Spar ${discount}%</span>` : ""}
        </div>
        <p class="detail-description">${escapeHtml(product.description || "Produktbeskrivelse kommer fra Tupperwares norske produktside.")}</p>
        ${product.textSource === "automatic-translation" ? `
          <p class="translation-note"><i data-lucide="languages"></i> Automatisk oversatt til norsk fra Tupperwares produkttekst.</p>
        ` : ""}
        ${archived ? `
        <div class="archive-note">
          <i data-lucide="archive"></i>
          <div>
            <strong>Produktet er ikke i dagens Tupperware-sortiment</strong>
            <span>${lastSeenLabel ? `Sist sett i nettbutikken ${escapeHtml(lastSeenLabel)}. ` : ""}Det kan fortsatt finnes hos en konsulent eller på lager i Norge.</span>
          </div>
        </div>` : `
        <div class="detail-actions">
          <a class="shop-button" href="${escapeHtml(shopUrl)}" target="tupperware-official-store">
            Se oppdaterte opplysninger og kjøp hos Tupperware <i data-lucide="external-link"></i>
          </a>
          <button class="icon-button copy-link" data-copy="${escapeHtml(shopUrl)}" aria-label="Kopier produktlenke" title="Kopier produktlenke">
            <i data-lucide="link"></i>
          </button>
        </div>`}
        <div class="order-note ${archived ? "archived-order-note" : ""}">
          ${archived
            ? "Ta kontakt med konsulenten hvis du er interessert i produktet."
            : `
          Du kan også sende meg en e-post for å bestille, så bestiller jeg for deg. Frakt kan tilkomme på billigst mulige måte. Produktet kan også finnes på lager i Norge og leveres raskere.
          `}
        </div>
      </div>
    </div>`;
}

async function openProduct(handle) {
  els.dialogContent.innerHTML = `<div class="detail-layout"><div class="product-skeleton"></div><div class="product-skeleton"></div></div>`;
  els.productDialog.showModal();
  try {
    const payload = await fetchJson(`/api/products/${encodeURIComponent(handle)}`);
    els.dialogContent.innerHTML = detailMarkup(payload.product);
    refreshIcons();
  } catch (error) {
    els.dialogContent.innerHTML = `<div class="error-state"><h2>Kunne ikke åpne produktet</h2><p>${escapeHtml(error.message)}</p></div>`;
  }
}

async function init() {
  initializeSuperAdminControls();
  await loadConsultant();
  try {
    const payload = await fetchJson("/api/navigation");
    state.collections = payload.collections;
    state.series = payload.series || [];
    state.activeGroup = "";
    syncSeriesPickers();
    renderNavigation();
    renderSubcategories();
    updateHeading();
    await loadProducts();
  } catch (error) {
    els.categoryNav.innerHTML = `<p>Kunne ikke laste kategoriene.</p>`;
    renderError(error);
  }
  refreshIcons();
}

els.categoryNav.addEventListener("click", event => {
  const button = event.target.closest("[data-collection]");
  if (!button) return;
  const collection = button.dataset.collection || "";
  const group = button.dataset.group ?? collection;
  if (group && state.activeGroup === group && collection === group) {
    const navGroup = button.closest(".nav-group");
    navGroup?.classList.toggle("open");
    if (state.activeCollection === collection) return;
  }
  chooseCollection(collection, group);
});

els.subcategoryStrip.addEventListener("click", event => {
  const button = event.target.closest("[data-collection]");
  if (button) chooseCollection(button.dataset.collection, state.activeGroup);
});

els.searchForm.addEventListener("submit", event => {
  event.preventDefault();
  runSearch(els.searchInput.value);
});

els.mobileSearchForm.addEventListener("submit", event => {
  event.preventDefault();
  runSearch(els.mobileSearchInput.value);
});

let searchTimer = 0;
els.searchInput.addEventListener("input", () => {
  els.searchForm.classList.toggle("has-value", Boolean(els.searchInput.value));
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => runSearch(els.searchInput.value), 350);
});

els.mobileSearchInput.addEventListener("input", () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => runSearch(els.mobileSearchInput.value), 350);
});

seriesPickers.forEach(picker => {
  picker.input.addEventListener("focus", () => {
    closeSeriesPickers();
    renderSeriesOptions(picker, state.activeSeries ? "" : picker.input.value);
  });
  picker.input.addEventListener("input", () => {
    picker.input.closest("[data-series-picker]")?.classList.toggle("has-value", Boolean(picker.input.value));
    renderSeriesOptions(picker, picker.input.value);
  });
  picker.input.addEventListener("keydown", event => {
    if (event.key === "Escape") {
      closeSeriesPickers();
      picker.input.value = state.activeSeries?.title || "";
    } else if (event.key === "Enter") {
      const exact = state.series.find(series =>
        seriesSearchKey(series.title) === seriesSearchKey(picker.input.value));
      if (exact) {
        event.preventDefault();
        chooseSeries(exact.title);
      }
    }
  });
  picker.options.addEventListener("click", event => {
    const option = event.target.closest("[data-series]");
    if (option) chooseSeries(option.dataset.series);
  });
  picker.clear.addEventListener("click", clearSeries);
});

document.addEventListener("click", event => {
  if (!event.target.closest("[data-series-picker]")) closeSeriesPickers();
});

els.clearSearch.addEventListener("click", () => runSearch(""));
els.statusSelect.addEventListener("change", () => {
  state.status = els.statusSelect.value;
  if (state.status === "not-in-current-assortment") {
    state.activeCollection = "";
    state.activeGroup = null;
    state.activeSeries = null;
    syncSeriesPickers();
    renderNavigation();
    renderSubcategories();
  }
  updateHeading();
  loadProducts();
});
els.sortSelect.addEventListener("change", () => {
  state.sort = els.sortSelect.value;
  syncResetButton();
  loadProducts();
});
els.resetFilters.addEventListener("click", () => resetCatalogView());

els.loadMoreButton.addEventListener("click", () => loadProducts({ append: true }));

els.homeButton.addEventListener("click", () => resetCatalogView());
els.menuButton.addEventListener("click", () => document.body.classList.add("menu-open"));
els.closeMenuButton.addEventListener("click", () => document.body.classList.remove("menu-open"));
els.menuBackdrop.addEventListener("click", () => document.body.classList.remove("menu-open"));

els.copyCatalogLink.addEventListener("click", async () => {
  try {
    await copyText(catalogShareUrl());
    showToast("Kataloglenken er kopiert. Lim den inn i Chrome eller Safari.");
  } catch {
    showToast("Kunne ikke kopiere lenken. Bruk menyen og velg ekstern nettleser.");
  }
});

els.closeInAppWarning.addEventListener("click", () => {
  els.inAppWarning.hidden = true;
  try {
    sessionStorage.setItem("inAppWarningDismissed", "1");
  } catch {
    // Dismissal still applies until the page is reloaded.
  }
});

els.chooseConsultantBanner.addEventListener("click", openConsultantPicker);

els.consultantDialogClose.addEventListener("click", () => els.consultantDialog.close());
els.consultantDialog.addEventListener("click", event => {
  if (event.target === els.consultantDialog) els.consultantDialog.close();
});
els.withoutConsultant.addEventListener("click", clearConsultant);
els.consultantSearchForm.addEventListener("submit", event => event.preventDefault());

let consultantSearchTimer = 0;
els.consultantSearchInput.addEventListener("input", () => {
  window.clearTimeout(consultantSearchTimer);
  consultantSearchTimer = window.setTimeout(
    () => loadConsultantChoices(els.consultantSearchInput.value),
    250,
  );
});

els.consultantResults.addEventListener("click", event => {
  const button = event.target.closest("[data-consultant-ref]");
  if (button) chooseConsultant(button.dataset.consultantRef, button.dataset.consultantName);
});

els.productGrid.addEventListener("click", event => {
  const seriesButton = event.target.closest("[data-product-series]");
  if (seriesButton) {
    chooseSeries(seriesButton.dataset.productSeries);
    return;
  }
  const button = event.target.closest("[data-detail]");
  if (button) openProduct(button.dataset.detail);
});

document.addEventListener("click", event => {
  const link = event.target.closest("a.shop-button[href]");
  if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  if (openOfficialStore(link.href)) event.preventDefault();
});

els.dialogClose.addEventListener("click", () => els.productDialog.close());
els.productDialog.addEventListener("click", event => {
  if (event.target === els.productDialog) els.productDialog.close();
});

els.dialogContent.addEventListener("click", async event => {
  const thumbnail = event.target.closest("[data-image]");
  if (thumbnail) {
    const main = document.querySelector("#detailMainImage");
    if (main) main.src = thumbnail.dataset.image;
    document.querySelectorAll(".thumbnail").forEach(item => item.classList.toggle("active", item === thumbnail));
  }
  const copy = event.target.closest("[data-copy]");
  if (copy) {
    await navigator.clipboard.writeText(copy.dataset.copy);
    showToast("Produktlenken er kopiert.");
  }
});

setupInAppWarning();
init();
