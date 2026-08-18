const params = new URLSearchParams(location.search);

function cleanRef(value) {
  return String(value || "").trim().replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 80);
}

function storedRef() {
  try {
    return cleanRef(localStorage.getItem("tupperwareConsultantRef"));
  } catch {
    return "";
  }
}

const referenceCode = cleanRef(params.get("ref")) || storedRef();
const state = {
  products: [],
  filtered: [],
  cart: new Map(),
  consultant: null,
  shopStatus: null,
  accessCode: "",
};

const els = {
  sellerStripText: document.querySelector("#sellerStripText"),
  officialHomeLink: document.querySelector("#officialHomeLink"),
  officialCatalogLink: document.querySelector("#officialCatalogLink"),
  pageTitle: document.querySelector("#pageTitle"),
  consultantName: document.querySelector("#consultantName"),
  searchInput: document.querySelector("#searchInput"),
  resultCount: document.querySelector("#resultCount"),
  productGrid: document.querySelector("#productGrid"),
  cartButton: document.querySelector("#cartButton"),
  cartCount: document.querySelector("#cartCount"),
  cartDialog: document.querySelector("#cartDialog"),
  closeCart: document.querySelector("#closeCart"),
  cartItems: document.querySelector("#cartItems"),
  cartTotal: document.querySelector("#cartTotal"),
  orderForm: document.querySelector("#orderForm"),
  sendOrder: document.querySelector("#sendOrder"),
  orderSuccess: document.querySelector("#orderSuccess"),
  successText: document.querySelector("#successText"),
  closeSuccess: document.querySelector("#closeSuccess"),
  toast: document.querySelector("#toast"),
  accessGate: document.querySelector("#accessGate"),
  accessForm: document.querySelector("#accessForm"),
  accessCodeInput: document.querySelector("#accessCodeInput"),
  accessMessage: document.querySelector("#accessMessage"),
  accessBackLink: document.querySelector("#accessBackLink"),
  shopContent: document.querySelector("#shopContent"),
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

function refreshIcons() {
  if (window.lucide) window.lucide.createIcons();
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => els.toast.classList.remove("show"), 2600);
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.error || "Noe gikk galt.");
    error.status = response.status;
    error.accessRequired = Boolean(payload.accessRequired);
    throw error;
  }
  return payload;
}

function officialUrl() {
  return referenceCode ? `/?ref=${encodeURIComponent(referenceCode)}` : "/";
}

function accessStorageKey() {
  return `consultantShopAccess:${referenceCode}`;
}

function storedAccessCode() {
  try {
    return sessionStorage.getItem(accessStorageKey()) || "";
  } catch {
    return "";
  }
}

function rememberAccessCode(value) {
  try {
    if (value) sessionStorage.setItem(accessStorageKey(), value);
    else sessionStorage.removeItem(accessStorageKey());
  } catch {
    // The customer can still use the code while this page remains open.
  }
}

function showAccessGate(message = "") {
  els.shopContent.hidden = true;
  els.cartButton.hidden = true;
  els.accessGate.hidden = false;
  els.accessMessage.textContent = message;
  els.accessBackLink.href = officialUrl();
  window.setTimeout(() => els.accessCodeInput.focus(), 0);
  refreshIcons();
}

function showShopContent() {
  els.accessGate.hidden = true;
  els.shopContent.hidden = false;
  els.cartButton.hidden = false;
}

function productCard(product) {
  const description = String(product.description || "").trim();
  const sourceLabel = product.source_type === "custom"
    ? "Konsulentens egen vare"
    : "Vare fra tidligere eller aktivt Tupperware-sortiment";
  return `
    <article class="own-card">
      <div class="own-image">
        ${product.image_url
          ? `<img src="${escapeHtml(product.image_url)}" alt="${escapeHtml(product.product_name)}" loading="lazy">`
          : `<span class="image-placeholder"><i data-lucide="image"></i></span>`}
      </div>
      <div class="own-meta">
        <span class="source-badge">${escapeHtml(sourceLabel)}</span>
        <h2>${escapeHtml(product.product_name)}</h2>
        <p class="own-description">${escapeHtml(description || "Kontakt konsulenten for mer informasjon om varen.")}</p>
        <span class="article">${product.article_number ? `Art.nr. ${escapeHtml(product.article_number)}` : "Egen vare"}</span>
        <span class="stock">${product.quantity} ${product.quantity === 1 ? "stk. tilgjengelig" : "stk. tilgjengelig"}</span>
        <strong class="own-price">${formatNok(product.sale_price_nok)}</strong>
        <button class="add-button" type="button" data-add="${escapeHtml(product.id)}">
          <i data-lucide="shopping-bag"></i>
          Legg i bestilling
        </button>
      </div>
    </article>`;
}

function renderProducts() {
  els.resultCount.textContent = `${state.filtered.length} ${state.filtered.length === 1 ? "vare" : "varer"}`;
  if (!state.filtered.length) {
    els.productGrid.innerHTML = `
      <div class="empty-state">
        <i data-lucide="package-search"></i>
        <h2>Ingen egne varer tilgjengelig nå</h2>
        <p>Konsulenten kan legge ut varer her etter hvert.</p>
      </div>`;
  } else {
    els.productGrid.innerHTML = state.filtered.map(productCard).join("");
  }
  refreshIcons();
}

function applySearch() {
  const words = els.searchInput.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
  state.filtered = words.length
    ? state.products.filter(product => {
      const haystack = [
        product.product_name,
        product.article_number,
        product.description,
        product.category,
      ].join(" ").toLowerCase();
      return words.every(word => haystack.includes(word));
    })
    : [...state.products];
  renderProducts();
}

function cartRows() {
  return [...state.cart.entries()].map(([id, quantity]) => {
    const product = state.products.find(item => item.id === id);
    return product ? { product, quantity } : null;
  }).filter(Boolean);
}

function renderCart() {
  const rows = cartRows();
  const count = rows.reduce((sum, row) => sum + row.quantity, 0);
  const total = rows.reduce((sum, row) => sum + Number(row.product.sale_price_nok) * row.quantity, 0);
  els.cartCount.textContent = String(count);
  els.cartTotal.textContent = formatNok(total);
  els.cartItems.innerHTML = rows.length
    ? rows.map(({ product, quantity }) => `
      <div class="cart-line">
        ${product.image_url
          ? `<img src="${escapeHtml(product.image_url)}" alt="">`
          : `<span></span>`}
        <div>
          <strong>${escapeHtml(product.product_name)}</strong>
          <small>${formatNok(product.sale_price_nok)} per stk.</small>
        </div>
        <div class="quantity" aria-label="Antall">
          <button type="button" data-quantity="${escapeHtml(product.id)}" data-change="-1" aria-label="Reduser antall">−</button>
          <span>${quantity}</span>
          <button type="button" data-quantity="${escapeHtml(product.id)}" data-change="1" aria-label="Øk antall">+</button>
        </div>
        <button class="remove-line" type="button" data-remove="${escapeHtml(product.id)}" aria-label="Fjern ${escapeHtml(product.product_name)}">
          <i data-lucide="trash-2"></i>
        </button>
      </div>`).join("")
    : `<div class="cart-empty">Du har ikke lagt til noen varer ennå.</div>`;
  els.orderForm.hidden = !rows.length;
  refreshIcons();
}

function addToCart(id) {
  const product = state.products.find(item => item.id === id);
  if (!product) return;
  const next = Math.min(product.quantity, (state.cart.get(id) || 0) + 1);
  state.cart.set(id, next);
  renderCart();
  showToast(`${product.product_name} er lagt i bestillingen.`);
}

function changeQuantity(id, change) {
  const product = state.products.find(item => item.id === id);
  if (!product) return;
  const next = Math.min(product.quantity, Math.max(0, (state.cart.get(id) || 0) + change));
  if (next) state.cart.set(id, next);
  else state.cart.delete(id);
  renderCart();
}

async function requestProducts() {
  return fetchJson("/api/own-products", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      referenceCode,
      accessCode: state.accessCode || null,
    }),
  });
}

async function loadInventory() {
  const payload = await requestProducts();
  state.products = payload.products || [];
  state.filtered = [...state.products];
  state.consultant = payload.consultant;
  const name = payload.consultant?.display_name || state.products[0]?.consultant_name || referenceCode;
  els.consultantName.textContent = name;
  els.pageTitle.textContent = `${name}s egne varer`;
  els.sellerStripText.textContent = `Egne varer fra ${name} - ikke fra Tupperwares lager`;
  showShopContent();
  renderProducts();
}

async function loadProducts() {
  els.officialHomeLink.href = officialUrl();
  els.officialCatalogLink.href = officialUrl();
  if (!referenceCode) {
    els.consultantName.textContent = "Ingen konsulent valgt";
    els.resultCount.textContent = "Velg konsulent først";
    els.productGrid.innerHTML = `
      <div class="empty-state">
        <i data-lucide="user-round-search"></i>
        <h2>Velg en konsulent</h2>
        <p>Gå tilbake til Tupperware-katalogen og velg konsulenten du handler med.</p>
      </div>`;
    return refreshIcons();
  }
  try {
    state.shopStatus = await fetchJson(
      `/api/shop-status?ref=${encodeURIComponent(referenceCode)}`,
    );
    if (!state.shopStatus.enabled || !state.shopStatus.hasProducts) {
      window.location.replace(`/?ref=${encodeURIComponent(referenceCode)}`);
      return;
    }
    if (state.shopStatus.accessMode === "code") {
      state.accessCode = storedAccessCode();
      if (!state.accessCode) {
        showAccessGate();
        return;
      }
    }
    await loadInventory();
  } catch (error) {
    if (error.accessRequired) {
      state.accessCode = "";
      rememberAccessCode("");
      showAccessGate(error.message);
      return;
    }
    els.resultCount.textContent = "Varene er utilgjengelige";
    els.productGrid.innerHTML = `
      <div class="error-state">
        <i data-lucide="wifi-off"></i>
        <h2>Kunne ikke hente varene</h2>
        <p>${escapeHtml(error.message)}</p>
      </div>`;
    refreshIcons();
  }
}

els.accessForm.addEventListener("submit", async event => {
  event.preventDefault();
  const code = els.accessCodeInput.value.trim();
  if (!code) return;
  const button = els.accessForm.querySelector("button");
  button.disabled = true;
  els.accessMessage.textContent = "Kontrollerer kundekoden ...";
  state.accessCode = code;
  try {
    await loadInventory();
    rememberAccessCode(code);
    els.accessCodeInput.value = "";
  } catch (error) {
    state.accessCode = "";
    rememberAccessCode("");
    els.accessMessage.textContent = error.accessRequired
      ? "Kundekoden er ikke riktig. Prøv igjen."
      : error.message;
    els.accessCodeInput.select();
  } finally {
    button.disabled = false;
  }
});

els.searchInput.addEventListener("input", applySearch);
els.productGrid.addEventListener("click", event => {
  const button = event.target.closest("[data-add]");
  if (button) addToCart(button.dataset.add);
});
els.cartButton.addEventListener("click", () => {
  els.orderSuccess.hidden = true;
  renderCart();
  els.cartDialog.showModal();
});
els.closeCart.addEventListener("click", () => els.cartDialog.close());
els.closeSuccess.addEventListener("click", () => els.cartDialog.close());
els.cartDialog.addEventListener("click", event => {
  if (event.target === els.cartDialog) els.cartDialog.close();
});
els.cartItems.addEventListener("click", event => {
  const quantityButton = event.target.closest("[data-quantity]");
  if (quantityButton) {
    changeQuantity(quantityButton.dataset.quantity, Number(quantityButton.dataset.change));
    return;
  }
  const removeButton = event.target.closest("[data-remove]");
  if (removeButton) {
    state.cart.delete(removeButton.dataset.remove);
    renderCart();
  }
});
els.orderForm.addEventListener("submit", async event => {
  event.preventDefault();
  const rows = cartRows();
  if (!rows.length) return;
  const form = new FormData(els.orderForm);
  const customer = {
    name: String(form.get("name") || "").trim(),
    email: String(form.get("email") || "").trim(),
    phone: String(form.get("phone") || "").trim(),
    message: String(form.get("message") || "").trim(),
  };
  if (!customer.email && !customer.phone) {
    return showToast("Oppgi e-post eller telefonnummer.");
  }
  els.sendOrder.disabled = true;
  els.sendOrder.textContent = "Sender bestillingen ...";
  try {
    await fetchJson("/api/own-orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        referenceCode,
        accessCode: state.accessCode || null,
        customer,
        items: rows.map(row => ({
          inventory_id: row.product.id,
          quantity: row.quantity,
        })),
      }),
    });
    state.cart.clear();
    renderCart();
    els.orderForm.reset();
    els.orderForm.hidden = true;
    els.orderSuccess.hidden = false;
    els.successText.textContent = `${state.consultant?.display_name || "Konsulenten"} kontakter deg for å bekrefte varene og leveringen.`;
  } catch (error) {
    showToast(error.message);
  } finally {
    els.sendOrder.disabled = false;
    els.sendOrder.innerHTML = `<i data-lucide="send"></i> Send bestillingsforespørsel`;
    refreshIcons();
  }
});

refreshIcons();
loadProducts();
