(() => {
  const STORAGE_KEY = "worldkitty.v1";
  const TICK_MS = 1000;
  const CHARGE_PER_RECHARGE = 34;
  const DRAIN_PER_TICK = 1.15;
  const CREDIT_PER_TICK_BASE = 2.4;
  const KITTY_SHARE = 0.28;
  const WORLD_SEED = 18432011.42;
  const AIX_PAYLOAD = "AiX++://WORLDKITTY/INFINITE-CHARGE?protocol=aixpp.wk.v1&loop=recharge>mint>kitty>redeem&vault=local";
  const PRODUCTS = [
    { id: "can-midnight", name: "Midnight Volt Can", desc: "Digital twin + claim ticket.", cost: 80, kind: "can", img: "assets/can-hero.jpg" },
    { id: "sixpack", name: "WorldKitty Six Pack", desc: "Mixed physical six.", cost: 420, kind: "can", img: "assets/sixpack.jpg" },
    { id: "hoodie", name: "Circuit Cat Hoodie", desc: "Holographic crest hoodie.", cost: 760, kind: "merch", img: "assets/hoodie.jpg" },
    { id: "sticker", name: "Volt Sticker Pack", desc: "Local-print pack.", cost: 35, kind: "merch", img: "assets/volt-mascot.jpg" },
    { id: "globe-print", name: "Orbital Kitty Print", desc: "Campaign print.", cost: 190, kind: "merch", img: "assets/world-kitty-globe.jpg" },
    { id: "infinite-can", name: "Infinite Charge Twin", desc: "Rare holographic claim.", cost: 1200, kind: "can", img: "assets/can-hero.jpg" },
    { id: "aix-plate", name: "AiX++ Bind Plate", desc: "Printable QR plate.", cost: 48, kind: "merch", img: "assets/aixpp-qr-plate.png" }
  ];
  const defaultState = () => ({ charge: 18, credits: 12, worldKitty: WORLD_SEED, contributed: 0, ticks: 0, looping: false, inventory: [], log: ["System ready. Local vault only."] });
  const $ = (id) => document.getElementById(id);
  function load() {
    try { return { ...defaultState(), ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") }; }
    catch { return defaultState(); }
  }
  function save(state) { localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...state, log: state.log.slice(0, 40) })); }
  function fmt(n, d = 1) { return Number(n).toLocaleString(undefined, { maximumFractionDigits: d, minimumFractionDigits: d }); }
  function ticketId() { return "AIX++/WK-" + Math.random().toString(36).slice(2, 6).toUpperCase() + "-" + Date.now().toString(36).slice(-5).toUpperCase(); }
  const state = load();
  let timer = null;
  function pushLog(msg) { state.log.unshift(new Date().toLocaleTimeString() + "  " + msg); state.log = state.log.slice(0, 48); renderLog(); }
  function renderLog() {
    $("loopLog").innerHTML = state.log.map((line) => {
      let cls = "dim";
      if (line.includes("KITTY")) cls = "mag";
      if (line.includes("REDEEM") || line.includes("CAN")) cls = "gold";
      return `<div class="${cls}">${line}</div>`;
    }).join("");
  }
  function renderShop() {
    $("shopGrid").innerHTML = PRODUCTS.map((p) => `<article class="product"><img src="${p.img}" alt="${p.name}"><div class="body"><h3>${p.name}</h3><p>${p.desc}</p><div class="price"><b>${p.cost} VC</b><button class="btn btn-ghost" data-buy="${p.id}">Redeem</button></div></div></article>`).join("");
  }
  function renderInventory() {
    if (!state.inventory.length) { $("invList").innerHTML = `<div class="inv-item"><span>No claims yet.</span></div>`; return; }
    $("invList").innerHTML = state.inventory.map((item) => `<div class="inv-item"><div><strong>${item.name}</strong><div class="ticket">${item.protocol || "AiX++"} · ${item.ticket} · ${item.kind}</div></div><span>${item.status}</span></div>`).join("");
  }
  function render() {
    $("chargeVal").textContent = `${fmt(state.charge, 0)}%`;
    $("chargeBar").style.width = `${Math.max(0, Math.min(100, state.charge))}%`;
    $("kittyVal").textContent = fmt(state.worldKitty, 1);
    $("kittyBar").style.width = `${Math.min(100, (state.worldKitty % 100000) / 1000)}%`;
    $("statCredits").textContent = fmt(state.credits, 1);
    $("statKitty").textContent = fmt(state.contributed, 1);
    $("statTicks").textContent = String(state.ticks);
    $("loopBtn").textContent = state.looping ? "Pause loop" : "Start generation loop";
    $("statusChip").textContent = state.looping ? "LOOP LIVE" : "IDLE";
    renderLog(); renderInventory(); save(state);
  }
  function toast(msg) { const el = $("toast"); el.textContent = msg; el.classList.add("show"); setTimeout(() => el.classList.remove("show"), 2400); }
  function tick() {
    if (state.charge <= 0) { state.charge = 0; state.looping = false; stopTimer(); pushLog("Charge empty. Recharge the digital can."); render(); return; }
    const yieldAmt = CREDIT_PER_TICK_BASE + state.charge / 80;
    const toKitty = yieldAmt * KITTY_SHARE;
    const toUser = yieldAmt - toKitty;
    state.charge = Math.max(0, state.charge - DRAIN_PER_TICK);
    state.credits += toUser;
    state.contributed += toKitty;
    state.worldKitty += toKitty + Math.random() * 0.2;
    state.ticks += 1;
    if (state.ticks % 4 === 0) pushLog(`LOOP +${fmt(toUser)} VC · KITTY +${fmt(toKitty)}`);
    render();
  }
  function startTimer() { if (!timer) timer = setInterval(tick, TICK_MS); }
  function stopTimer() { if (timer) clearInterval(timer); timer = null; }
  function recharge() { const before = state.charge; state.charge = Math.min(100, state.charge + CHARGE_PER_RECHARGE); pushLog(`RECHARGE ${fmt(before, 0)}% → ${fmt(state.charge, 0)}%`); toast("Digital can topped up."); render(); }
  function toggleLoop() {
    if (!state.looping && state.charge <= 0) { toast("Recharge first."); return; }
    state.looping = !state.looping;
    if (state.looping) { pushLog("Generation loop armed."); startTimer(); } else { pushLog("Loop paused."); stopTimer(); }
    render();
  }
  function buy(id) {
    const product = PRODUCTS.find((p) => p.id === id);
    if (!product) return;
    if (state.credits < product.cost) { toast("Not enough Volt Credits."); return; }
    state.credits -= product.cost;
    const claim = { id: product.id, name: product.name, kind: product.kind, ticket: ticketId(), protocol: "AiX++", status: product.kind === "can" ? "AIX++ CAN CLAIM READY" : "AIX++ MERCH CLAIM READY", at: new Date().toLocaleString() };
    state.inventory.unshift(claim);
    pushLog(`REDEEM ${product.name} · ${claim.ticket}`);
    toast(`${product.name} claimed locally.`);
    render();
  }
  function resetVault() {
    if (!confirm("Wipe local WorldKitty vault on this device?")) return;
    stopTimer();
    Object.assign(state, defaultState());
    localStorage.removeItem(STORAGE_KEY);
    pushLog("Local vault reset.");
    render();
  }
  document.addEventListener("click", (e) => { const buyId = e.target.getAttribute("data-buy"); if (buyId) buy(buyId); });
  $("rechargeBtn").addEventListener("click", recharge);
  $("loopBtn").addEventListener("click", toggleLoop);
  $("resetBtn").addEventListener("click", resetVault);
  const payloadEl = $("aixPayload"); if (payloadEl) payloadEl.textContent = AIX_PAYLOAD;
  const copyBtn = $("copyAixBtn");
  if (copyBtn) copyBtn.addEventListener("click", async () => { try { await navigator.clipboard.writeText(AIX_PAYLOAD); toast("AiX++ payload copied."); } catch { toast("Copy blocked."); } });
  const dlBtn = $("downloadQrBtn");
  if (dlBtn) dlBtn.addEventListener("click", () => { const a = document.createElement("a"); a.href = "assets/aixpp-qr.svg"; a.download = "worldkitty-aixpp.svg"; a.click(); });
  renderShop(); render();
  if (state.looping && state.charge > 0) startTimer();
})();
