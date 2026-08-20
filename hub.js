const params = new URLSearchParams(window.location.search);

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
  official: new URL(`/?ref=${encodeURIComponent(referenceCode)}`, window.location.origin).toString(),
  digital: new URL(`/digital-katalog?ref=${encodeURIComponent(referenceCode)}`, window.location.origin).toString(),
  own: new URL(`/egne-varer?ref=${encodeURIComponent(referenceCode)}`, window.location.origin).toString(),
  party: new URL(`/party?ref=${encodeURIComponent(referenceCode)}`, window.location.origin).toString(),
};
const shareDetails = {
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
};

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
  return Number(consultant?.link_use_count || 0);
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
  head.innerHTML = `<tr><th>Konsulent</th><th>Referanse</th>${productRegister.map(product => `<th>${product.title}</th>`).join("")}</tr>`;
  body.replaceChildren(...adminState.consultants.map(consultant => {
    const row = document.createElement("tr");
    const accessCells = productRegister.map(product => {
      const active = consultant.product_access.has(product.key);
      return `<td><button type="button" class="admin-access-toggle ${active ? "is-active" : ""}" data-overview-access="${product.key}" data-access-consultant="${consultant.reference_code}" title="${active ? "Fjern tilgang" : "Gi tilgang"}" aria-label="${active ? "Fjern tilgang" : "Gi tilgang"}"><i data-lucide="${active ? "check-circle-2" : "ban"}"></i></button></td>`;
    }).join("");
    row.innerHTML = `<td><button type="button" class="admin-overview-link" data-admin-select="${consultant.reference_code}">${consultant.display_name} (${consultantLinkUseCount(consultant)})</button></td><td><code>${consultant.reference_code}</code></td>${accessCells}`;
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
  const [consultants, productAccess] = await Promise.all([
    jsonRequest(
      `${adminState.config.supabaseUrl}/rest/v1/consultants?select=id,reference_code,display_name,status,public_listing,municipality,county,own_shop_enabled,link_use_count&order=display_name.asc&limit=500`,
      { headers: adminHeaders() },
    ),
    jsonRequest(
      `${adminState.config.supabaseUrl}/rest/v1/consultant_product_access?select=consultant_id,product_key,is_active`,
      { headers: adminHeaders() },
    ),
  ]);
  adminState.productAccess = productAccess;
  adminState.consultants = consultants.map(consultant => ({
    ...consultant,
    product_access: new Set(productAccess
      .filter(item => item.consultant_id === consultant.id && item.is_active)
      .map(item => item.product_key)),
  }));
  renderAdminConsultants();
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

  const qrSize = 760;
  const qrY = titleBottom + 235;
  context.strokeStyle = "#d7dedb";
  context.lineWidth = 5;
  context.strokeRect((canvas.width - qrSize) / 2 - 28, qrY - 28, qrSize + 56, qrSize + 56);
  context.drawImage(qrImage, (canvas.width - qrSize) / 2, qrY, qrSize, qrSize);

  context.fillStyle = "#202825";
  context.font = "700 43px Arial";
  context.fillText("Skann QR-koden med mobilkameraet", centerX, qrY + qrSize + 110);
  context.fillStyle = "#4a5450";
  context.font = "400 29px Arial";
  context.fillText("Trykk på lenken som vises på skjermen for å åpne katalogen.", centerX, qrY + qrSize + 166);

  if (key === "own") {
    context.fillStyle = "#faf1f3";
    context.fillRect(180, qrY + qrSize + 220, canvas.width - 360, 112);
    context.fillStyle = "#802535";
    context.font = "700 27px Arial";
    context.fillText("Varene kommer fra konsulentens eget lager, ikke Tupperwares sentrallager.", centerX, qrY + qrSize + 288);
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
  context.font = "400 24px Arial";
  context.fillText(`Konsulentreferanse: ${referenceCode}`, centerX, 2170);
  const urlLines = wrapCanvasText(context, shareUrls[key], 1300);
  drawCenteredLines(context, urlLines, centerX, 2220, 34);

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
  document.querySelector("#officialCatalogLink").href = shareUrls.official;
  document.querySelector("#digitalCatalogLink").href = shareUrls.digital;
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
  intro.textContent = registered
    ? `Konsulenten ${consultantLabel} er registrert i systemet. Her ser du hvilke løsninger som er åpne.`
    : `Konsulenten ${consultantLabel} er ikke registrert ennå. Her ser du hvilke løsninger som kan åpnes når profilen er aktiv.`;
  list.innerHTML = productRegister.map(product => {
    const active = currentProductAccess(product);
    const badgeClass = active ? "active" : "locked";
    const badgeText = active ? "Tilgang" : "Låst";
    const note = "Tilgang gis eller fjernes av superadministrator etter kjøp.";
    return `
      <article class="registry-card ${active ? "is-active" : "is-locked"}">
        <div class="registry-card-head">
          <div>
            <strong>${product.title}</strong>
            <p>${product.description}</p>
          </div>
          <span class="module-status ${badgeClass}">${badgeText}</span>
        </div>
        <div class="registry-meta">
          <span>${product.accessLabel}</span>
          <span>${note}</span>
        </div>
      </article>
    `;
  }).join("");
}

function updateVisibleModules() {
  const access = consultantProfile?.productAccess || new Set();
  document.querySelector("#officialCatalogLink").hidden = !access.has("norsk-nettkatalog");
  document.querySelector("#digitalCatalogLink").hidden = !access.has("norsk-produktkatalog");
  document.querySelector("#ownCatalogModule").hidden = !access.has("egne-varer");
  document.querySelector("#partyModule").hidden = !access.has("party");
  document.querySelector('[data-share="official"]').hidden = !access.has("norsk-nettkatalog");
  document.querySelector('[data-share="digital"]').hidden = !access.has("norsk-produktkatalog");
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
  if (consultantProfile.productAccess.has("norsk-nettkatalog")) shareTasks.push(renderShareItem("official"));
  if (consultantProfile.productAccess.has("norsk-produktkatalog")) shareTasks.push(renderShareItem("digital"));
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

window.addEventListener("DOMContentLoaded", async () => {
  if (window.lucide) window.lucide.createIcons();
  initializeAdminSwitcher().catch(error => {
    document.querySelector("#adminLoginMessage").textContent = error.message || "Kunne ikke starte administratorverktøyet.";
  });
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
