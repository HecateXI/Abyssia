window.__adminAppLoaded = true;

const state = {
  password: localStorage.getItem("adminPassword") || "",
  active: "overview",
  catalog: null,
  entityPage: 1,
  entityFilter: "",
  balanceFilter: "",
  guildSettings: {},
  patreonMembers: [],
  selected: {
    creatures: null,
    equipment: null,
    materials: null,
    zones: null,
    bosses: null,
    weapons: null,
    passives: null,
    status: null,
    crate: null,
    currency: null,
    crate: null,
    buffs: null,
    rarity: null,
    ui: null,
    consumable: null,
  },
};

const tabDefs = [
  ["overview", "Overview", "O"],
  ["assets", "Assets", "A"],
  ["creatures", "Creatures", "C"],
  ["equipment", "Equipment", "E"],
  ["weapons", "Weapons", "W"],
  ["passives", "Passives", "P"],
  ["status", "Status", "T"],
  ["zones", "Zones", "Z"],
  ["bosses", "Bosses", "B"],
  ["materials", "Materials", "M"],
  ["balance", "Balance", "%"],
  ["server", "Server", "S"],
  ["runtime", "Runtime", "R"],
];

const entityKinds = new Set(["creatures", "equipment", "zones", "bosses", "materials", "weapons", "passives", "status", "crate"]);
const guildSettingKeys = [
  "prefix",
  "modlog_channel_id",
  "welcome_channel_id",
  "booster_base_role_id",
  "patreon_tier_1_role_id",
  "patreon_tier_2_role_id",
  "patreon_tier_3_role_id",
  "patreon_tier_4_role_id",
];

const defaults = {
  creatures: { name: "New Horror", rarity: "Common", attack: 10, defense: 8, hp: 35, speed: 10, ability: "Shadow Cloak" },
  equipment: { name: "New Relic", slot: "weapon", tier: 1, durability: 100, stats: {}, effects: {}, cost: {} },
  zones: { name: "New Zone", required_level: 1, max_rarity: "Rare", gold: [25, 75], gems_chance: 0.08, material_keys: ["bone_fragments"], flavor: "The road ahead is cursed." },
  bosses: { name: "New Boss", hp: 25000, level: 10, material_key: "ancient_relics", title: "Boss Slayer" },
  materials: { name: "New Material" },
  weapons: { name: "New Weapon Type", desc: "A new weapon type." },
  passives: { name: "New Passive" },
  status: { name: "New Status Effect", desc: "A new status effect." },
  crate: { name: "New Crate", desc: "A new crate.", cost: { gold: 500 }, weapon_chance: 1, weapon_rarities: ["Common"], gold: [50, 100], gems: [0, 2], swords: [0, 1], materials: 1 },
};

const $ = (id) => document.getElementById(id);

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttr(value) {
  return escapeHtml(value);
}

function titleFor(key) {
  const tab = tabDefs.find((item) => item[0] === key);
  if (tab) return tab[1];
  const titles = {
    currency: "Currency",
    crate: "Crates",
    buffs: "Buffs",
    rarity: "Rarity",
    ui: "UI Icons",
    consumable: "Consumables",
  };
  return titles[key] || key;
}

function showNotice(message, persistent = false) {
  const notice = $("notice");
  notice.textContent = message;
  notice.classList.remove("hidden");
  if (!persistent) {
    window.setTimeout(() => notice.classList.add("hidden"), 4200);
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Password": state.password,
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { error: text || `Request failed: ${response.status}` };
  }
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

function assetThumb(item) {
  const preview = item.asset && item.asset.preview;
  if (preview) {
    return `<img class="thumb" src="${escapeAttr(preview)}" alt="">`;
  }
  return `<div class="thumb empty">IMG</div>`;
}

function itemLabel(kind, item) {
  if (kind === "creatures") return `${item.rarity || "Common"} | Lv stats`;
  if (kind === "equipment") return `${item.slot || "item"} | tier ${item.tier || 1}`;
  if (kind === "zones") return `level ${item.required_level || 1} | ${item.max_rarity || "Rare"}`;
  if (kind === "bosses") return `level ${item.level || 1} | ${item.hp || 0} HP`;
  if (kind === "weapons") {
    const atk = item.atk_range || [0, 0];
    const def = item.def_range || [0, 0];
    return `ATK ${atk[0]}-${atk[1]} | DEF ${def[0]}-${def[1]}`;
  }
  if (kind === "crate") return `${item.weapon_chance ?? 0} weapon chance | ${inputValue(item, "weapon_rarities")}`;
  return item.key;
}

function renderTabs() {
  $("tabs").innerHTML = tabDefs
    .map(([key, label, icon]) => `<button class="tab ${state.active === key ? "active" : ""}" data-tab="${key}" type="button"><span class="btn-icon">${icon}</span>${label}</button>`)
    .join("");
  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      state.active = button.dataset.tab;
      render();
    });
  });
}

function renderShell() {
  $("login").classList.add("hidden");
  $("login").hidden = true;
  $("shell").hidden = false;
  $("shell").classList.remove("hidden");
  renderTabs();
  render();
}

function render() {
  renderTabs();
  $("pageTitle").textContent = titleFor(state.active);
  $("pageSubtitle").textContent = state.active === "overview" ? "Abyssia content and asset control" : "Edit persistent RPG content and server settings";

  if (!state.catalog) {
    $("content").innerHTML = `<div class="panel">Loading...</div>`;
    return;
  }

  if (state.active === "overview") renderOverview();
  else if (state.active === "assets") renderAssets();
  else if (entityKinds.has(state.active)) renderEntity(state.active);
  else if (state.active === "balance") renderBalance();
  else if (state.active === "server") renderServer();
  else if (state.active === "runtime") renderRuntime();
}

function renderOverview() {
  const content = $("content");
  const counts = ["creatures", "equipment", "weapons", "passives", "status", "zones", "bosses", "materials", "currency", "crate", "buffs", "rarity", "ui", "consumable"].map((kind) => {
    const items = state.catalog[kind] || [];
    const withAssets = items.filter((item) => item.asset && item.asset.preview).length;
    return { kind, total: items.length, withAssets };
  });
  content.innerHTML = `
    <div class="grid">
      ${counts
        .map(
          (row) => `
          <section class="panel span-4 metric">
            <span class="muted">${titleFor(row.kind)}</span>
            <strong>${row.total}</strong>
            <span>${row.withAssets} PNG or URL assets</span>
          </section>`
        )
        .join("")}
      <section class="panel span-12">
        <h2>Runtime Settings</h2>
        <div class="form-grid">
          <label class="full">Public asset base URL
            <input id="publicBaseUrl" value="${state.catalog.settings.public_asset_base_url || ""}" placeholder="https://your-domain.example">
          </label>
          <label class="inline-check full">
            <input id="autoSyncEmojis" type="checkbox" ${state.catalog.settings.auto_sync_application_emojis === false ? "" : "checked"}>
            Sync uploaded PNGs to application emojis
          </label>
          <div class="button-row full">
            <button id="savePublicUrl" type="button"><span class="btn-icon">S</span> Save</button>
          </div>
        </div>
      </section>
    </div>
  `;
  $("savePublicUrl").addEventListener("click", savePublicUrl);
}

function listHtml(kind, items) {
  return items
    .map((item) => {
      const active = state.selected[kind] === item.key ? "active" : "";
      return `
        <button class="list-item ${active}" data-key="${item.key}" type="button">
          ${assetThumb(item)}
          <span>
            <strong class="row-title">${escapeHtml(item.name || item.key)}</strong>
            <span class="row-subtitle">${escapeHtml(item.deleted ? `Disabled | ${itemLabel(kind, item)}` : itemLabel(kind, item))}</span>
          </span>
          <span class="pill">${escapeHtml(item.key)}</span>
        </button>`;
    })
    .join("");
}

function renderEntity(kind) {
  const allItems = state.catalog[kind] || [];
  const filter = (state.entityFilter || "").toLowerCase();
  const items = filter ? allItems.filter((item) => (item.key + " " + (item.name || "")).toLowerCase().includes(filter)) : allItems;
  const PAGE_SIZE = 20;
  const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  if (state.entityPage > totalPages) state.entityPage = totalPages;
  if (state.entityPage < 1) state.entityPage = 1;
  const pageItems = items.slice((state.entityPage - 1) * PAGE_SIZE, state.entityPage * PAGE_SIZE);
  if (!state.selected[kind] && pageItems[0]) state.selected[kind] = pageItems[0].key;
  const selected = allItems.find((item) => item.key === state.selected[kind]) || pageItems[0];
  $("content").innerHTML = `
    <div class="grid">
      <section class="panel span-5">
        <h2>${titleFor(kind)}</h2>
        <div class="form-grid">
          <label class="full">New key
            <input id="newKey" placeholder="new_content_key">
          </label>
          <div class="button-row full">
            <button id="addEntity" type="button"><span class="btn-icon">+</span> Add</button>
          </div>
        </div>
        <label class="full" style="margin:8px 0 4px">Filter
          <input id="entityFilter" value="${escapeAttr(state.entityFilter)}" placeholder="Search...">
        </label>
        <div class="list">${listHtml(kind, pageItems)}</div>
        <div class="button-row" style="margin-top:8px">
          <button id="prevPage" type="button" class="ghost" ${state.entityPage <= 1 ? "disabled" : ""}>Prev</button>
          <span style="margin:0 8px;color:#888">${state.entityPage}/${totalPages} (${items.length})</span>
          <button id="nextPage" type="button" class="ghost" ${state.entityPage >= totalPages ? "disabled" : ""}>Next</button>
        </div>
      </section>
      <section class="panel span-7">
        ${selected ? editorHtml(kind, selected) : "<p>No entries.</p>"}
      </section>
    </div>
  `;
  document.querySelectorAll(".list-item").forEach((button) => {
    button.addEventListener("click", () => {
      state.selected[kind] = button.dataset.key;
      renderEntity(kind);
    });
  });
  $("addEntity").addEventListener("click", () => addEntity(kind));
  $("prevPage").addEventListener("click", () => { state.entityPage--; renderEntity(kind); });
  $("nextPage").addEventListener("click", () => { state.entityPage++; renderEntity(kind); });
  $("entityFilter").addEventListener("input", (e) => { state.entityFilter = e.target.value; state.entityPage = 1; renderEntity(kind); });
  if (selected) bindEditor(kind, selected);
}

function inputValue(item, key, fallback = "") {
  const value = item[key];
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object" && value !== null) return JSON.stringify(value, null, 2);
  return value ?? fallback;
}

function rarityOptions(value) {
  return state.catalog.rarities
    .map((rarity) => `<option value="${escapeAttr(rarity.name)}" ${rarity.name === value ? "selected" : ""}>${escapeHtml(rarity.name)}</option>`)
    .join("");
}

function materialOptions(value) {
  return state.catalog.materials
    .map((material) => `<option value="${escapeAttr(material.key)}" ${material.key === value ? "selected" : ""}>${escapeHtml(material.name)}</option>`)
    .join("");
}

function patreonTierOptions(value) {
  return (state.catalog.patreon_tiers || [])
    .map((tier) => `<option value="${tier.tier}" ${Number(value) === Number(tier.tier) ? "selected" : ""}>Tier ${tier.tier} - ${escapeHtml(tier.name)}</option>`)
    .join("");
}

function patreonMembersHtml() {
  if (!state.patreonMembers.length) {
    return `<p class="muted">No manual Patreon members loaded for this guild.</p>`;
  }
  return `
    <div class="list compact-list">
      ${state.patreonMembers
        .map((member) => {
          const tier = (state.catalog.patreon_tiers || []).find((item) => Number(item.tier) === Number(member.tier));
          return `
            <div class="list-item static">
              <span>
                <strong class="row-title">${escapeHtml(member.member_id)}</strong>
                <span class="row-subtitle">Tier ${escapeHtml(member.tier)}${tier ? ` | ${escapeHtml(tier.name)}` : ""}${member.note ? ` | ${escapeHtml(member.note)}` : ""}</span>
              </span>
              <button class="ghost patreon-delete" data-member-id="${escapeAttr(member.member_id)}" type="button">Remove</button>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function editorHtml(kind, item) {
  const header = `
    <div class="button-row">
      <h2 style="margin-right:auto">${escapeHtml(item.name || item.key)}</h2>
      <button id="saveEntity" type="button"><span class="btn-icon">S</span> Save</button>
      <button id="disableEntity" class="ghost" type="button"><span class="btn-icon">D</span> Disable</button>
      <button id="clearEntity" class="ghost" type="button"><span class="btn-icon">C</span> Clear override</button>
    </div>
    <p class="muted">Key: ${escapeHtml(item.key)}${item.deleted ? " | Disabled" : ""}</p>
  `;
  if (kind === "creatures") {
    return `${header}<div class="form-grid">
      <label>Name<input data-field="name" value="${escapeAttr(inputValue(item, "name"))}"></label>
      <label>Rarity<select data-field="rarity">${rarityOptions(item.rarity)}</select></label>
      <label>Attack<input data-field="attack" type="number" value="${escapeAttr(inputValue(item, "attack"))}"></label>
      <label>Defense<input data-field="defense" type="number" value="${escapeAttr(inputValue(item, "defense"))}"></label>
      <label>HP<input data-field="hp" type="number" value="${escapeAttr(inputValue(item, "hp"))}"></label>
      <label>Speed<input data-field="speed" type="number" value="${escapeAttr(inputValue(item, "speed"))}"></label>
      <label>MANA<input data-field="wp_stat" type="number" value="${escapeAttr(inputValue(item, "wp_stat", 1))}"></label>
      <label>MAG<input data-field="mag_stat" type="number" value="${escapeAttr(inputValue(item, "mag_stat", 1))}"></label>
      <label>RES<input data-field="mr_stat" type="number" value="${escapeAttr(inputValue(item, "mr_stat", 1))}"></label>
      <label>Crit<input data-field="crit" type="number" value="${escapeAttr(inputValue(item, "crit", 5))}"></label>
      <label class="full">Ability<input data-field="ability" value="${escapeAttr(inputValue(item, "ability"))}"></label>
    </div>`;
  }
  if (kind === "equipment") {
    return `${header}<div class="form-grid">
      <label>Name<input data-field="name" value="${escapeAttr(inputValue(item, "name"))}"></label>
      <label>Slot<select data-field="slot"><option value="weapon" ${item.slot === "weapon" ? "selected" : ""}>weapon</option><option value="charm" ${item.slot === "charm" ? "selected" : ""}>charm</option></select></label>
      <label>Tier<input data-field="tier" type="number" value="${escapeAttr(inputValue(item, "tier"))}"></label>
      <label>Durability<input data-field="durability" type="number" value="${escapeAttr(inputValue(item, "durability", ""))}"></label>
      <label class="full">Stats JSON<textarea data-field="stats" data-json="1">${escapeHtml(inputValue(item, "stats", "{}"))}</textarea></label>
      <label class="full">Effects JSON<textarea data-field="effects" data-json="1">${escapeHtml(inputValue(item, "effects", "{}"))}</textarea></label>
      <label class="full">Cost JSON<textarea data-field="cost" data-json="1">${escapeHtml(inputValue(item, "cost", "{}"))}</textarea></label>
    </div>`;
  }
  if (kind === "zones") {
    const gold = item.gold || [25, 75];
    return `${header}<div class="form-grid">
      <label>Name<input data-field="name" value="${escapeAttr(inputValue(item, "name"))}"></label>
      <label>Required level<input data-field="required_level" type="number" value="${escapeAttr(inputValue(item, "required_level"))}"></label>
      <label>Max rarity<select data-field="max_rarity">${rarityOptions(item.max_rarity)}</select></label>
      <label>Gems chance<input data-field="gems_chance" type="number" step="0.01" value="${escapeAttr(inputValue(item, "gems_chance"))}"></label>
      <label>Souls minimum<input data-field="gold_min" type="number" value="${escapeAttr(gold[0])}"></label>
      <label>Souls maximum<input data-field="gold_max" type="number" value="${escapeAttr(gold[1])}"></label>
      <label class="full">Materials CSV<input data-field="material_keys" value="${escapeAttr(inputValue(item, "material_keys"))}"></label>
      <label class="full">Flavor<textarea data-field="flavor">${escapeHtml(inputValue(item, "flavor"))}</textarea></label>
    </div>`;
  }
  if (kind === "bosses") {
    return `${header}<div class="form-grid">
      <label>Name<input data-field="name" value="${escapeAttr(inputValue(item, "name"))}"></label>
      <label>HP<input data-field="hp" type="number" value="${escapeAttr(inputValue(item, "hp"))}"></label>
      <label>Level<input data-field="level" type="number" value="${escapeAttr(inputValue(item, "level"))}"></label>
      <label>Reward material<select data-field="material_key">${materialOptions(item.material_key)}</select></label>
      <label class="full">Title<input data-field="title" value="${escapeAttr(inputValue(item, "title"))}"></label>
    </div>`;
  }
  if (kind === "weapons") {
    return `${header}<div class="form-grid">
      <label>Name<input data-field="name" value="${escapeAttr(inputValue(item, "name"))}"></label>
      <label>Description<input data-field="desc" value="${escapeAttr(inputValue(item, "desc"))}"></label>
      <label>ATK Min<input data-field="atk_min" type="number" value="${escapeAttr(inputValue(item, "atk_range", [0,0])[0])}"></label>
      <label>ATK Max<input data-field="atk_max" type="number" value="${escapeAttr(inputValue(item, "atk_range", [0,0])[1])}"></label>
      <label>DEF Min<input data-field="def_min" type="number" value="${escapeAttr(inputValue(item, "def_range", [0,0])[0])}"></label>
      <label>DEF Max<input data-field="def_max" type="number" value="${escapeAttr(inputValue(item, "def_range", [0,0])[1])}"></label>
      <label class="full">Passive Pool<input data-field="passive_pool" value="${escapeAttr(inputValue(item, "passive_pool"))}"></label>
    </div>`;
  }
  if (kind === "passives") {
    return `${header}<div class="form-grid">
      <label>Name<input data-field="name" value="${escapeAttr(inputValue(item, "name"))}"></label>
      <label>Icon fallback<input data-field="icon" value="${escapeAttr(inputValue(item, "icon"))}"></label>
      <label class="full">Description<textarea data-field="desc">${escapeHtml(inputValue(item, "desc"))}</textarea></label>
    </div>`;
  }
  if (kind === "status") {
    return `${header}<div class="form-grid">
      <label>Name<input data-field="name" value="${escapeAttr(inputValue(item, "name"))}"></label>
      <label>Color<input data-field="color" type="number" value="${escapeAttr(inputValue(item, "color", ""))}"></label>
      <label>Icon fallback<input data-field="emoji" value="${escapeAttr(inputValue(item, "emoji"))}"></label>
      <label class="full">Description<textarea data-field="desc">${escapeHtml(inputValue(item, "desc"))}</textarea></label>
    </div>`;
  }
  if (kind === "crate") {
    const gold = item.gold || [0, 0];
    const gems = item.gems || [0, 0];
    const swords = item.swords || [0, 0];
    return `${header}<div class="form-grid">
      <label>Name<input data-field="name" value="${escapeAttr(inputValue(item, "name"))}"></label>
      <label>Weapon chance<input data-field="weapon_chance" type="number" step="0.01" value="${escapeAttr(inputValue(item, "weapon_chance", 0))}"></label>
      <label>Souls min<input data-field="gold_min" type="number" value="${escapeAttr(gold[0])}"></label>
      <label>Souls max<input data-field="gold_max" type="number" value="${escapeAttr(gold[1])}"></label>
      <label>Gems min<input data-field="gems_min" type="number" value="${escapeAttr(gems[0])}"></label>
      <label>Gems max<input data-field="gems_max" type="number" value="${escapeAttr(gems[1])}"></label>
      <label>Swords min<input data-field="swords_min" type="number" value="${escapeAttr(swords[0])}"></label>
      <label>Swords max<input data-field="swords_max" type="number" value="${escapeAttr(swords[1])}"></label>
      <label>Materials<input data-field="materials" type="number" value="${escapeAttr(inputValue(item, "materials", 0))}"></label>
      <label class="full">Weapon rarities CSV<input data-field="weapon_rarities" value="${escapeAttr(inputValue(item, "weapon_rarities"))}"></label>
      <label class="full">Cost JSON<textarea data-field="cost" data-json="1">${escapeHtml(inputValue(item, "cost", "{}"))}</textarea></label>
      <label class="full">Description<textarea data-field="desc">${escapeHtml(inputValue(item, "desc"))}</textarea></label>
    </div>`;
  }
  return `${header}<div class="form-grid">
    <label class="full">Name<input data-field="name" value="${escapeAttr(inputValue(item, "name"))}"></label>
  </div>`;
}

function bindEditor(kind, item) {
  $("saveEntity").addEventListener("click", () => saveEntity(kind, item.key));
  $("disableEntity").addEventListener("click", () => saveEntity(kind, item.key, { deleted: true }));
  $("clearEntity").addEventListener("click", () => clearEntity(kind, item.key));
}

function collectPatch(kind) {
  const patch = {};
  document.querySelectorAll("[data-field]").forEach((field) => {
    const name = field.dataset.field;
    if (field.dataset.json) {
      patch[name] = JSON.parse(field.value || "{}");
    } else if (field.type === "number") {
      patch[name] = field.value === "" ? null : Number(field.value);
    } else if (["material_keys", "weapon_rarities"].includes(name)) {
      patch[name] = field.value.split(",").map((item) => item.trim()).filter(Boolean);
    } else {
      patch[name] = field.value;
    }
  });
  if (kind === "zones") {
    patch.gold = [Number(patch.gold_min || 0), Number(patch.gold_max || 0)];
    delete patch.gold_min;
    delete patch.gold_max;
  }
  if (kind === "weapons") {
    patch.atk_range = [Number(patch.atk_min || 0), Number(patch.atk_max || 0)];
    patch.def_range = [Number(patch.def_min || 0), Number(patch.def_max || 0)];
    delete patch.atk_min;
    delete patch.atk_max;
    delete patch.def_min;
    delete patch.def_max;
    if (typeof patch.passive_pool === "string") {
      patch.passive_pool = patch.passive_pool.split(",").map((s) => s.trim()).filter(Boolean);
    }
  }
  if (kind === "crate") {
    patch.gold = [Number(patch.gold_min || 0), Number(patch.gold_max || 0)];
    patch.gems = [Number(patch.gems_min || 0), Number(patch.gems_max || 0)];
    patch.swords = [Number(patch.swords_min || 0), Number(patch.swords_max || 0)];
    delete patch.gold_min;
    delete patch.gold_max;
    delete patch.gems_min;
    delete patch.gems_max;
    delete patch.swords_min;
    delete patch.swords_max;
  }
  return patch;
}

async function saveEntity(kind, key, forcedPatch = null) {
  const patch = forcedPatch || collectPatch(kind);
  await api("/api/content", {
    method: "POST",
    body: JSON.stringify({ kind, key, patch }),
  });
  showNotice("Saved. Restart the bot to apply gameplay stat changes.");
  await loadCatalog();
}

async function clearEntity(kind, key) {
  await api("/api/content/clear", {
    method: "POST",
    body: JSON.stringify({ kind, key }),
  });
  showNotice("Override cleared. Restart the bot if it is running.");
  await loadCatalog();
}

async function addEntity(kind) {
  const input = $("newKey");
  const key = (input.value || "").trim();
  if (!key) {
    showNotice("Enter a key first.");
    return;
  }
  const patch = { ...defaults[kind], name: defaults[kind].name.replace("New", key.replace(/_/g, " ")) };
  await api("/api/content", {
    method: "POST",
    body: JSON.stringify({ kind, key, patch }),
  });
  state.selected[kind] = key.toLowerCase().replace(/[^a-z0-9]+/g, "_");
  showNotice("Custom entry saved. Restart the bot to activate it.");
  await loadCatalog();
}

function renderAssets() {
  const kind = state.assetKind || "creatures";
  state.assetKind = kind;
  const items = state.catalog[kind] || [];
  if (!state.selected[kind] && items[0]) state.selected[kind] = items[0].key;
  const selected = items.find((item) => item.key === state.selected[kind]) || items[0];
  $("content").innerHTML = `
    <div class="grid">
      <section class="panel span-5">
        <h2>Asset Target</h2>
        <label>Kind
          <select id="assetKind">
            ${["creatures", "equipment", "weapons", "passives", "status", "materials", "zones", "bosses", "currency", "crate", "buffs", "rarity", "ui", "consumable"].map((value) => `<option value="${value}" ${value === kind ? "selected" : ""}>${titleFor(value)}</option>`).join("")}
          </select>
        </label>
        <div class="list">${listHtml(kind, items)}</div>
      </section>
      <section class="panel span-7">
        ${selected ? assetEditorHtml(kind, selected) : "<p>No entries.</p>"}
      </section>
    </div>
  `;
  $("assetKind").addEventListener("change", (event) => {
    state.assetKind = event.target.value;
    renderAssets();
  });
  document.querySelectorAll(".list-item").forEach((button) => {
    button.addEventListener("click", () => {
      state.selected[kind] = button.dataset.key;
      renderAssets();
    });
  });
  if (selected) bindAssetEditor(kind, selected);
}

function assetEditorHtml(kind, item) {
  const preview = item.asset && item.asset.preview;
  return `
    <h2>${escapeHtml(item.name || item.key)}</h2>
    <p class="muted">Key: ${escapeHtml(item.key)}</p>
    ${preview ? `<img class="asset-preview" src="${escapeAttr(preview)}" alt="">` : `<div class="asset-preview thumb empty" style="height:220px">No Image</div>`}
    <div class="form-grid" style="margin-top:14px">
      <label class="full">Image upload
        <input id="assetFile" type="file" accept="image/png,image/jpeg">
      </label>
      <label class="full">External URL
        <input id="assetUrl" placeholder="https://cdn.example/item.png">
      </label>
      <div class="button-row full">
        <button id="uploadAsset" type="button"><span class="btn-icon">U</span> Upload Image</button>
        <button id="saveAssetUrl" type="button"><span class="btn-icon">L</span> Save URL</button>
        <button id="clearAsset" class="ghost" type="button"><span class="btn-icon">C</span> Clear</button>
      </div>
    </div>
  `;
}

function bindAssetEditor(kind, item) {
  $("uploadAsset").addEventListener("click", () => uploadAsset(kind, item.key));
  $("saveAssetUrl").addEventListener("click", () => saveAssetUrl(kind, item.key));
  $("clearAsset").addEventListener("click", () => clearAsset(kind, item.key));
}

async function uploadAsset(kind, key) {
  const file = $("assetFile").files[0];
  if (!file) {
    showNotice("Choose an image file.");
    return;
  }
  const looksImage = file.type === "image/png" || file.type === "image/jpeg"
    || file.name.toLowerCase().endsWith(".png")
    || file.name.toLowerCase().endsWith(".jpg")
    || file.name.toLowerCase().endsWith(".jpeg");
  if (!looksImage) {
    showNotice("Only PNG and JPEG files are accepted.");
    return;
  }
  try {
    const dataUrl = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
    const result = await api("/api/asset", {
      method: "POST",
      body: JSON.stringify({ kind, key, data_url: dataUrl }),
    });
    const sync = result.emoji_sync || {};
    showNotice(sync.message ? `Image uploaded. ${sync.message}` : "Image uploaded.");
    await loadCatalog();
  } catch (err) {
    showNotice("Upload failed: " + err.message, true);
  }
}

async function saveAssetUrl(kind, key) {
  const url = $("assetUrl").value.trim();
  await api("/api/asset", {
    method: "POST",
    body: JSON.stringify({ kind, key, url }),
  });
  showNotice("Asset URL saved.");
  await loadCatalog();
}

async function clearAsset(kind, key) {
  await api("/api/asset", {
    method: "POST",
    body: JSON.stringify({ kind, key, clear: true }),
  });
  showNotice("Asset cleared.");
  await loadCatalog();
}

function balanceValue(path, fallback = "") {
  let current = state.catalog.balancing || {};
  for (const part of path.split(".")) {
    if (!current || typeof current !== "object" || !(part in current)) return fallback;
    current = current[part];
  }
  return current ?? fallback;
}

function setDeep(target, path, value) {
  const parts = path.split(".");
  let current = target;
  parts.slice(0, -1).forEach((part) => {
    if (!current[part] || typeof current[part] !== "object" || Array.isArray(current[part])) current[part] = {};
    current = current[part];
  });
  current[parts[parts.length - 1]] = value;
}

function mergeDeep(target, source) {
  for (const [key, value] of Object.entries(source || {})) {
    if (value && typeof value === "object" && !Array.isArray(value) && target[key] && typeof target[key] === "object" && !Array.isArray(target[key])) {
      mergeDeep(target[key], value);
    } else {
      target[key] = value;
    }
  }
  return target;
}

function balanceInput(path, label, fallback, step = "1", extra = "") {
  return `<label>${escapeHtml(label)}<input data-balance="${escapeAttr(path)}" type="number" step="${escapeAttr(step)}" value="${escapeAttr(balanceValue(path, fallback))}" ${extra}></label>`;
}

function renderBalance() {
  const balancing = state.catalog.balancing || {};
  const huntFields = [
    ["hunt.base_catch_rate", "Base catch rate", 0.60, "0.001"],
    ["hunt.luck_catch_bonus", "Luck catch bonus", 0.015, "0.001"],
    ["hunt.max_catch_rate", "Max catch rate", 0.95, "0.001"],
    ["hunt.base_cooldown_seconds", "Base cooldown sec", 15, "0.1"],
    ["hunt.level_cooldown_reduction", "Level cooldown reduction", 0.10, "0.01"],
    ["hunt.min_cooldown_seconds", "Min cooldown sec", 10, "0.1"],
    ["hunt.base_crate_chance", "Base crate chance", 0.04, "0.001"],
    ["hunt.zone_level_crate_bonus", "Zone crate bonus", 0.003, "0.001"],
    ["hunt.luck_crate_bonus", "Luck crate bonus", 0.002, "0.001"],
    ["hunt.max_crate_chance", "Max crate chance", 0.20, "0.001"],
    ["hunt.autohunt_rolls_per_hour", "Autohunt rolls/hour", 3, "1"],
    ["hunt.autohunt_max_rolls", "Autohunt max rolls", 48, "1"],
    ["hunt.hunt_sword_duration_seconds", "Hunt sword duration", 1200, "1"],
    ["hunt.hunt_sword_extra_rolls", "Hunt sword rolls", 1, "1"],
    ["hunt.checklist_hunt_lootbox_chance", "Hunt lootbox chance", 0.05, "0.001"],
    ["hunt.checklist_battle_crate_chance", "Battle crate chance", 0.05, "0.001"],
    ["hunt.checklist_hunt_lootbox_target", "Hunt lootbox target", 3, "1"],
    ["hunt.checklist_battle_crate_target", "Battle crate target", 3, "1"],
  ];

  const rarityRows = (state.catalog.rarities || []).map((rarity) => `
    <tr>
      <td>${escapeHtml(rarity.name)}</td>
      <td><input data-balance="rarity.catch_rates.${escapeAttr(rarity.name)}" type="number" step="0.00001" value="${escapeAttr(balanceValue(`rarity.catch_rates.${rarity.name}`, rarity.catch_rate || 0))}"></td>
      <td><input data-balance="rarity.weights.${escapeAttr(rarity.name)}" type="number" step="0.01" value="${escapeAttr(balanceValue(`rarity.weights.${rarity.name}`, rarity.weight))}"></td>
      <td><input data-balance="rarity.stat_multipliers.${escapeAttr(rarity.name)}" type="number" step="0.01" value="${escapeAttr(balanceValue(`rarity.stat_multipliers.${rarity.name}`, rarity.stat_multiplier))}"></td>
    </tr>
  `).join("");

  const sigilRows = (state.catalog.sigils || []).map((sigil) => `
    <tr>
      <td>${escapeHtml(sigil.name)}</td>
      <td><input data-balance="buffs.sigils.${escapeAttr(sigil.key)}.extra_monsters" type="number" value="${escapeAttr(balanceValue(`buffs.sigils.${sigil.key}.extra_monsters`, sigil.extra_monsters))}"></td>
      <td><input data-balance="buffs.sigils.${escapeAttr(sigil.key)}.charges" type="number" value="${escapeAttr(balanceValue(`buffs.sigils.${sigil.key}.charges`, sigil.charges))}"></td>
      <td><input data-balance="buffs.sigils.${escapeAttr(sigil.key)}.cost_souls" type="number" value="${escapeAttr(balanceValue(`buffs.sigils.${sigil.key}.cost_souls`, sigil.cost_souls))}"></td>
      <td><input data-balance="buffs.sigils.${escapeAttr(sigil.key)}.cost_gems" type="number" value="${escapeAttr(balanceValue(`buffs.sigils.${sigil.key}.cost_gems`, sigil.cost_gems || 0))}"></td>
    </tr>
  `).join("");

  const charmRows = (state.catalog.charms || []).map((charm) => `
    <tr>
      <td>${escapeHtml(charm.name)}</td>
      <td><input data-balance="buffs.charms.${escapeAttr(charm.key)}.rarity_bonus" type="number" step="0.001" value="${escapeAttr(balanceValue(`buffs.charms.${charm.key}.rarity_bonus`, charm.rarity_bonus))}"></td>
      <td><input data-balance="buffs.charms.${escapeAttr(charm.key)}.extra_monsters" type="number" value="${escapeAttr(balanceValue(`buffs.charms.${charm.key}.extra_monsters`, charm.extra_monsters || 0))}"></td>
      <td><input data-balance="buffs.charms.${escapeAttr(charm.key)}.charges" type="number" value="${escapeAttr(balanceValue(`buffs.charms.${charm.key}.charges`, charm.charges))}"></td>
      <td><input data-balance="buffs.charms.${escapeAttr(charm.key)}.cost_souls" type="number" value="${escapeAttr(balanceValue(`buffs.charms.${charm.key}.cost_souls`, charm.cost_souls))}"></td>
      <td><input data-balance="buffs.charms.${escapeAttr(charm.key)}.cost_gems" type="number" value="${escapeAttr(balanceValue(`buffs.charms.${charm.key}.cost_gems`, charm.cost_gems || 0))}"></td>
    </tr>
  `).join("");

  const tierRows = (state.catalog.patreon_tiers || []).map((tier) => {
    const pets = balanceValue(`patreon.tier_pets.${tier.tier}`, []);
    return `
      <tr data-tier-row="${tier.tier}">
        <td>Tier ${tier.tier}</td>
        <td><input data-tier-field="name" value="${escapeAttr(tier.name)}"></td>
        <td><input data-tier-field="description" value="${escapeAttr(tier.description || "")}"></td>
        <td><input data-balance="patreon.tier_pets.${tier.tier}" data-list="1" value="${escapeAttr(Array.isArray(pets) ? pets.join(", ") : pets)}" placeholder="creature_key, another_key"></td>
      </tr>
    `;
  }).join("");

  $("content").innerHTML = `
    <div class="grid">
      <section class="panel span-12">
        <div class="button-row">
          <h2 style="margin-right:auto">Hunt Balance</h2>
          <button id="saveBalance" type="button"><span class="btn-icon">S</span> Save Balance</button>
        </div>
        <div class="form-grid">${huntFields.map((field) => balanceInput(...field)).join("")}</div>
      </section>
      <section class="panel span-12">
        <h2>Catch Rates</h2>
        <div class="table-wrap"><table class="data-table"><thead><tr><th>Rarity</th><th>Catch rate</th><th>Spawn weight</th><th>Stat multiplier</th></tr></thead><tbody>${rarityRows}</tbody></table></div>
      </section>
      <section class="panel span-12">
        <h2>Buff Strength</h2>
        <div class="table-wrap"><table class="data-table"><thead><tr><th>Sigil</th><th>Extra monsters</th><th>Charges</th><th>Souls</th><th>Gems</th></tr></thead><tbody>${sigilRows}</tbody></table></div>
      </section>
      <section class="panel span-12">
        <h2>Charm Strength</h2>
        <div class="table-wrap"><table class="data-table"><thead><tr><th>Charm</th><th>Rarity bonus</th><th>Extra monsters</th><th>Charges</th><th>Souls</th><th>Gems</th></tr></thead><tbody>${charmRows}</tbody></table></div>
      </section>
      <section class="panel span-12">
        <h2>Patreon Tiers</h2>
        <div class="table-wrap"><table class="data-table"><thead><tr><th>Tier</th><th>Name</th><th>Description</th><th>Tier pets</th></tr></thead><tbody>${tierRows}</tbody></table></div>
      </section>
      <section class="panel span-12">
        <h2>Advanced Balancing JSON</h2>
        <textarea id="balanceJson" class="json-editor">${escapeHtml(JSON.stringify(balancing, null, 2))}</textarea>
      </section>
    </div>
  `;
  $("saveBalance").addEventListener("click", saveBalance);
}

function collectBalancePatch() {
  const patch = {};
  document.querySelectorAll("[data-balance]").forEach((field) => {
    let value;
    if (field.dataset.list) {
      value = field.value.split(",").map((item) => item.trim()).filter(Boolean);
    } else if (field.dataset.json) {
      value = JSON.parse(field.value || "{}");
    } else if (field.type === "checkbox") {
      value = field.checked;
    } else if (field.type === "number") {
      value = field.value === "" ? null : Number(field.value);
    } else {
      value = field.value;
    }
    setDeep(patch, field.dataset.balance, value);
  });

  const tiers = [];
  document.querySelectorAll("[data-tier-row]").forEach((row) => {
    const tier = Number(row.dataset.tierRow);
    const name = row.querySelector("[data-tier-field='name']").value.trim() || `Patron ${tier}`;
    const description = row.querySelector("[data-tier-field='description']").value.trim();
    tiers.push({ tier, name, description });
  });
  if (tiers.length) setDeep(patch, "patreon.tiers", tiers);
  return patch;
}

async function saveBalance() {
  let advanced = {};
  try {
    advanced = JSON.parse($("balanceJson").value || "{}");
  } catch (error) {
    showNotice("Advanced balancing JSON is invalid: " + error.message, true);
    return;
  }
  const patch = mergeDeep(advanced, collectBalancePatch());
  await api("/api/balancing", {
    method: "POST",
    body: JSON.stringify({ balancing: patch }),
  });
  showNotice("Balancing saved. Restart the bot to apply gameplay changes.");
  await loadCatalog();
}

function renderServer() {
  const guildId = localStorage.getItem("guildId") || "";
  $("content").innerHTML = `
    <div class="grid">
      <section class="panel span-12">
        <h2>Guild Settings</h2>
        <div class="form-grid">
          <label class="full">Guild ID<input id="guildId" value="${guildId}" placeholder="123456789012345678"></label>
          <label>Prefix<input id="prefix" value="${escapeAttr(state.guildSettings.prefix || "")}" placeholder="!"></label>
          <label>Modlog channel ID<input id="modlog_channel_id" value="${escapeAttr(state.guildSettings.modlog_channel_id || "")}"></label>
          <label>Welcome channel ID<input id="welcome_channel_id" value="${escapeAttr(state.guildSettings.welcome_channel_id || "")}"></label>
          <label>Booster base role ID<input id="booster_base_role_id" value="${escapeAttr(state.guildSettings.booster_base_role_id || "")}"></label>
          <label>Patreon tier 1 role ID<input id="patreon_tier_1_role_id" value="${escapeAttr(state.guildSettings.patreon_tier_1_role_id || "")}"></label>
          <label>Patreon tier 2 role ID<input id="patreon_tier_2_role_id" value="${escapeAttr(state.guildSettings.patreon_tier_2_role_id || "")}"></label>
          <label>Patreon tier 3 role ID<input id="patreon_tier_3_role_id" value="${escapeAttr(state.guildSettings.patreon_tier_3_role_id || "")}"></label>
          <label>Patreon tier 4 role ID<input id="patreon_tier_4_role_id" value="${escapeAttr(state.guildSettings.patreon_tier_4_role_id || "")}"></label>
          <div class="button-row full">
            <button id="loadGuild" type="button"><span class="btn-icon">L</span> Load</button>
            <button id="saveGuild" type="button"><span class="btn-icon">S</span> Save</button>
          </div>
        </div>
      </section>
      <section class="panel span-12">
        <h2>Manual Patreon Members</h2>
        <div class="form-grid">
          <label>Discord user ID<input id="patreon_member_id" placeholder="123456789012345678"></label>
          <label>Tier<select id="patreon_tier">${patreonTierOptions(4)}</select></label>
          <label class="full">Note<input id="patreon_note" placeholder="Patreon username or reason"></label>
          <div class="button-row full">
            <button id="savePatreonMember" type="button"><span class="btn-icon">+</span> Add or Update</button>
          </div>
        </div>
        ${patreonMembersHtml()}
      </section>
    </div>
  `;
  $("loadGuild").addEventListener("click", loadGuildSettings);
  $("saveGuild").addEventListener("click", saveGuildSettings);
  $("savePatreonMember").addEventListener("click", savePatreonMember);
  document.querySelectorAll(".patreon-delete").forEach((button) => {
    button.addEventListener("click", () => deletePatreonMember(button.dataset.memberId));
  });
}

async function loadGuildSettings() {
  const guildId = $("guildId").value.trim();
  if (!guildId) return showNotice("Enter a guild ID.");
  localStorage.setItem("guildId", guildId);
  const data = await api(`/api/guild-settings?guild_id=${encodeURIComponent(guildId)}`);
  const patreon = await api(`/api/patreon-members?guild_id=${encodeURIComponent(guildId)}`);
  state.guildSettings = data.settings || {};
  state.patreonMembers = patreon.members || [];
  renderServer();
  showNotice("Guild settings loaded.");
}

async function saveGuildSettings() {
  const guildId = $("guildId").value.trim();
  if (!guildId) return showNotice("Enter a guild ID.");
  const settings = {};
  for (const key of guildSettingKeys) {
    settings[key] = $(key).value.trim();
  }
  const data = await api("/api/guild-settings", {
    method: "POST",
    body: JSON.stringify({ guild_id: guildId, settings }),
  });
  state.guildSettings = data.settings || {};
  localStorage.setItem("guildId", guildId);
  renderServer();
  showNotice("Guild settings saved.");
}

async function savePatreonMember() {
  const guildId = $("guildId").value.trim();
  const memberId = $("patreon_member_id").value.trim();
  if (!guildId) return showNotice("Enter a guild ID.");
  if (!memberId) return showNotice("Enter a Discord user ID.");
  const data = await api("/api/patreon-members", {
    method: "POST",
    body: JSON.stringify({
      guild_id: guildId,
      member_id: memberId,
      tier: Number($("patreon_tier").value || 1),
      note: $("patreon_note").value.trim(),
    }),
  });
  state.patreonMembers = data.members || [];
  localStorage.setItem("guildId", guildId);
  renderServer();
  showNotice("Patreon member saved.");
}

async function deletePatreonMember(memberId) {
  const guildId = $("guildId").value.trim();
  if (!guildId || !memberId) return;
  const data = await api("/api/patreon-members", {
    method: "POST",
    body: JSON.stringify({ guild_id: guildId, member_id: memberId, delete: true }),
  });
  state.patreonMembers = data.members || [];
  renderServer();
  showNotice("Patreon member removed.");
}

function renderRuntime() {
  $("content").innerHTML = `
    <div class="grid">
      <section class="panel span-12">
        <h2>Paths</h2>
        <span class="muted">Content config</span>
        <code class="code-path">${state.catalog.paths.config}</code>
        <span class="muted">Assets</span>
        <code class="code-path">${state.catalog.paths.assets}</code>
        <span class="muted">SQLite database</span>
        <code class="code-path">${state.catalog.paths.database}</code>
      </section>
      <section class="panel span-12">
        <h2>Commands</h2>
        <code class="code-path">.\\.venv\\Scripts\\python.exe bot.py</code>
        <code class="code-path">.\\.venv\\Scripts\\python.exe web_admin.py</code>
      </section>
      <section class="panel span-12">
        <h2>Application Emoji Bank</h2>
        <div class="form-grid">
          <label>Scope
            <select id="emojiSyncScope">
              <option value="uploaded" selected>Uploaded Images</option>
              <option value="all">All local image assets</option>
            </select>
          </label>
          <label class="inline-check">
            <input id="emojiReplaceExisting" type="checkbox" checked>
            Replace existing application emojis
          </label>
          <div class="button-row full">
            <button id="syncApplicationEmojis" type="button"><span class="btn-icon">S</span> Sync Emojis</button>
          </div>
          <code id="emojiSyncResult" class="code-path full"></code>
        </div>
      </section>
    </div>
  `;
  $("syncApplicationEmojis").addEventListener("click", syncApplicationEmojis);
}

async function savePublicUrl() {
  await api("/api/settings", {
    method: "POST",
    body: JSON.stringify({
      public_asset_base_url: $("publicBaseUrl").value.trim(),
      auto_sync_application_emojis: $("autoSyncEmojis").checked,
    }),
  });
  showNotice("Public asset base URL saved.");
  await loadCatalog();
}

async function syncApplicationEmojis() {
  const resultBox = $("emojiSyncResult");
  resultBox.textContent = "Syncing...";
  try {
    const result = await api("/api/emojis/sync", {
      method: "POST",
      body: JSON.stringify({
        scope: $("emojiSyncScope").value,
        replace_existing: $("emojiReplaceExisting").checked,
      }),
    });
    const failed = (result.failed || []).slice(0, 8);
    const skipped = (result.skipped || []).slice(0, 8);
    const lines = [
      result.message || "Emoji sync complete.",
      `Total ${result.total || 0} | Uploaded ${result.uploaded || 0} | Created ${result.created || 0} | Replaced ${result.replaced || 0} | Existing ${result.existing || 0}`,
    ];
    if (failed.length) lines.push(`Failed: ${failed.join("; ")}`);
    if (skipped.length) lines.push(`Skipped: ${skipped.join("; ")}`);
    resultBox.textContent = lines.join("\n");
    showNotice(result.message || "Emoji sync complete.", (result.failed || []).length > 0);
  } catch (error) {
    resultBox.textContent = error.message;
    showNotice("Emoji sync failed: " + error.message, true);
  }
}

async function loadCatalog() {
  state.catalog = await api("/api/catalog");
  renderShell();
}

async function checkSession() {
  try {
    const session = await api("/api/session");
    if (session.ok) {
      await loadCatalog();
      if (session.default_password) {
        showNotice("ADMIN_PASSWORD is using the default value: admin.", true);
      }
  } else {
      $("login").hidden = false;
      $("login").classList.remove("hidden");
    }
  } catch {
    $("login").hidden = false;
    $("login").classList.remove("hidden");
  }
}

$("loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  state.password = $("password").value || "admin";
  localStorage.setItem("adminPassword", state.password);
  try {
    await loadCatalog();
  } catch (error) {
    $("loginMessage").textContent = error.message;
  }
});

$("reloadBtn").addEventListener("click", loadCatalog);
$("logoutBtn").addEventListener("click", () => {
  localStorage.removeItem("adminPassword");
  state.password = "";
  $("shell").classList.add("hidden");
  $("shell").hidden = true;
  $("login").hidden = false;
  $("login").classList.remove("hidden");
});

checkSession();
