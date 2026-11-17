/* Universal de Repuestos WG — SPA sin dependencias.
   Tienda pública (inicio, productos, detalle/compra, nosotros, contacto), login/registro,
   checkout con pago, "Mis pedidos" y panel administrativo por rol. */
'use strict';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const cop = n => new Intl.NumberFormat('es-CO', {style: 'currency', currency: 'COP', maximumFractionDigits: 0}).format(Number(n) || 0);
const IVA = 0.19;
const withIva = n => Math.round(Number(n) * (1 + IVA));
const I = ART.icon;
const store = {get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* almacenamiento no disponible */ } },
  del: k => { try { localStorage.removeItem(k); } catch (e) { /* */ } }};
const STAFF = ['administrador', 'empacador', 'repartidor'];
const COMPANY = {phone1: '(+57) 310-477-2730', phone2: '(+57) 321-204-7803', tel: '+573104772730',
  address: 'Calle 63F #25-49, barrio 7 de Agosto, Bogotá', email: 'ventas@universalrepuestoswg.co'};

// La sesión vive en una cookie HttpOnly (el JS nunca ve el JWT); aquí solo se guarda el perfil y el token CSRF.
const S = {
  tok: '', role: '', name: '', csrf: '', booted: false,
  cart: JSON.parse(store.get('cart') || '[]'), note: '', lang: store.get('lang') || 'es',
  theme: store.get('theme') || 'light', cache: {}, timers: [], wh: null,
};
const saveCart = () => { store.set('cart', JSON.stringify(S.cart)); $$('[data-cartn]').forEach(e => { const n = cartCount(); e.textContent = n; e.hidden = !n; }); };
const cartCount = () => S.cart.reduce((a, i) => a + i.qty, 0);
const cartSubtotal = () => S.cart.reduce((a, i) => a + i.price * i.qty, 0);

/* ---------------- i18n (cabecera y tienda) ---------------- */
const TXT = {
  es: {home: 'Inicio', products: 'Productos', about: 'Sobre nosotros', contact: 'Contáctenos', categories: 'Categorías',
    search: 'Buscar repuesto, referencia o vehículo…', lang: 'Idioma', theme: 'Tema', light: 'Claro', dark: 'Oscuro',
    pickCar: 'Seleccione su vehículo', brand: 'Seleccione la marca…', model: 'Seleccione el modelo…', year: 'Seleccione el año…',
    meet: 'Conócenos', more: 'Más información relacionada', all: 'Ver todos', add: 'Agregar', out: 'Agotado',
    login: 'Ingresar', orders: 'Mis pedidos', panel: 'Panel', logout: 'Salir', cart: 'Carrito', ivaInc: 'IVA incluido',
    request: 'Solicitar', myRequest: 'Tu solicitud', reqDesc: 'Descripción de cotización o compra', total: 'Total'},
  en: {home: 'Home', products: 'Products', about: 'About us', contact: 'Contact', categories: 'Categories',
    search: 'Search part, reference or vehicle…', lang: 'Language', theme: 'Theme', light: 'Light', dark: 'Dark',
    pickCar: 'Select your vehicle', brand: 'Select brand…', model: 'Select model…', year: 'Select year…',
    meet: 'About us', more: 'More related information', all: 'See all', add: 'Add', out: 'Sold out',
    login: 'Sign in', orders: 'My orders', panel: 'Dashboard', logout: 'Sign out', cart: 'Cart', ivaInc: 'VAT included',
    request: 'Request', myRequest: 'Your request', reqDesc: 'Quote or purchase description', total: 'Total'},
};
const t = k => (TXT[S.lang] || TXT.es)[k] || TXT.es[k] || k;

/* ---------------- utilidades ---------------- */
function toast(msg, type = '') {
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.innerHTML = `${I(type === 'bad' ? 'alert' : type === 'ok' ? 'check' : 'tag', 18)}<span>${esc(msg)}</span>`;
  $('#toasts').append(el);
  setTimeout(() => el.remove(), type === 'bad' ? 6000 : 3500);
}
async function api(path, method = 'GET', body) {
  let r;
  try {
    r = await fetch('/api' + path, {method, credentials: 'same-origin',
      headers: {'Content-Type': 'application/json', ...(method !== 'GET' && S.csrf && {'X-CSRF-Token': S.csrf})},
      body: body ? JSON.stringify(body) : undefined});
  } catch (e) { throw new Error('No hay conexión con el servidor. Verifica que la API esté en ejecución.'); }
  if (r.status === 204) return null;
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    if (r.status === 401 && S.tok && !path.startsWith('/auth/')) { setSession(null); throw new Error('Tu sesión expiró. Inicia sesión de nuevo.'); }
    throw new Error(d.error || d.msg || 'Error ' + r.status);
  }
  return d;
}
const cached = (k, fn) => S.cache[k] || (S.cache[k] = fn().catch(e => { delete S.cache[k]; throw e; }));
const loadCats = () => cached('cats', () => api('/spare-part-types?state=true'));
const loadCars = () => cached('cars', () => api('/cars?state=true'));
const loadBrands = () => cached('brands', () => api('/car-brands?state=true'));
// El stock que ve el cliente es el de la bodega que atiende la venta (antes se sumaban todas las bodegas
// y un pedido que "cabía" en el stock mostrado podía rechazarse por stock insuficiente).
const bodega = () => cached('wh', async () => { const w = await api('/warehouses?state=true'); S.wh = (w[0] || {}).company_warehouse_id || 1; return S.wh; });
const conBodega = async ruta => ruta + (ruta.includes('?') ? '&' : '?') + 'warehouse_id=' + await bodega();
const loadAll = () => cached('allProducts', async () => api(await conBodega('/products')));
const carLabel = c => c ? (c.model && !String(c.name).includes(c.model) ? `${c.name} ${c.model}` : c.name) : '';
const run = fn => async (...a) => { try { return await fn(...a); } catch (e) { toast(e.message, 'bad'); } };
const formData = f => Object.fromEntries(new FormData(f));
const fmtDate = s => s ? new Date(s).toLocaleDateString('es-CO', {day: '2-digit', month: 'short', year: 'numeric'}) : '—';
const fmtDateTime = s => s ? new Date(s).toLocaleString('es-CO', {day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'}) : '—';
const STATE_CLS = {Pendiente: 'warn', Pagada: 'info', Despachada: 'info', Entregada: 'ok', Cancelada: 'bad',
  pendiente: 'warn', empacado: 'info', en_camino: 'info', entregado: 'ok', cancelado: 'bad', aprobado: 'ok'};
const DLV = {pendiente: 'Pendiente', empacado: 'Empacado', en_camino: 'En camino', entregado: 'Entregado', cancelado: 'Cancelado'};
const badge = s => `<span class="badge ${STATE_CLS[s] || ''}">${esc(DLV[s] || s)}</span>`;
const METHOD_LABEL = {tarjeta_credito: 'Tarjeta de crédito', tarjeta_debito: 'Tarjeta débito', pse: 'PSE', transferencia: 'Transferencia', nequi: 'Nequi', efectivo: 'Efectivo contra entrega'};

function setSession(p) {
  Object.assign(S, p ? {tok: '1', role: p.role, name: p.username, csrf: p.csrf_token || ''} : {tok: '', role: '', name: '', csrf: ''});
}
async function boot() {
  try { const p = await api('/auth/yo?opcional=1'); setSession(p.autenticado ? p : null); } catch (e) { setSession(null); }
  S.booted = true;
}
async function logout(silent, todas = false) {
  if (!silent) { try { await api(todas ? '/auth/logout-todas' : '/auth/logout', 'POST'); } catch (e) { /* la sesión ya no existía */ } }
  setSession(null); S.cache = {};
  if (!silent) { toast(todas ? 'Se cerraron todas tus sesiones' : 'Sesión cerrada'); go('/'); }
}
function go(path) { if (location.hash === '#' + path) render(); else location.hash = path; }
function route() {
  const h = location.hash.replace(/^#\/?/, '');
  const [p, qs] = h.split('?');
  return {parts: (p || '').split('/').filter(Boolean), q: new URLSearchParams(qs || '')};
}
window.addEventListener('hashchange', () => render());

/* ---------------- modal ---------------- */
const modal = $('#modal');
function openModal(html, {wide = false} = {}) {
  modal.className = 'modal' + (wide ? ' wide' : '');
  modal.innerHTML = html;
  if (!modal.open) modal.showModal();
  const f = modal.querySelector('[autofocus], input, select, textarea, button.btn');
  f && f.focus();
}
function closeModal() { if (modal.open) modal.close(); }
modal.addEventListener('click', e => { if (e.target === modal) closeModal(); });
const mhead = title => `<div class="mhead"><h2 id="modal-title">${title}</h2><button class="btn ghost icon" type="button" onclick="closeModal()" aria-label="Cerrar">${I('x', 18)}</button></div>`;
function confirmBox(title, text, okLabel = 'Confirmar', danger = false) {
  return new Promise(res => {
    openModal(`${mhead(esc(title))}<div class="mbody"><p>${esc(text)}</p></div>
      <div class="mfoot"><button class="btn ghost" id="cf-no">Volver</button><button class="btn ${danger ? 'danger' : ''}" id="cf-ok">${esc(okLabel)}</button></div>`);
    const done = v => { modal.removeEventListener('close', onClose); closeModal(); res(v); };
    const onClose = () => res(false);
    modal.addEventListener('close', onClose, {once: true});
    $('#cf-no').onclick = () => done(false); $('#cf-ok').onclick = () => done(true);
  });
}
async function busy(btn, fn) {
  const html = btn.innerHTML; btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Procesando…';
  try { return await fn(); } finally { if (btn.isConnected) { btn.disabled = false; btn.innerHTML = html; } }
}

/* ================================================================ RENDER */
async function render() {
  if (!S.booted) await boot();
  S.timers.forEach(clearInterval); S.timers = [];
  document.documentElement.dataset.theme = S.theme;
  document.documentElement.lang = S.lang;
  const {parts, q} = route();
  const root = $('#root');
  try {
    if (parts[0] === 'admin') {
      if (!S.tok) return go('/login?next=' + encodeURIComponent(parts.join('/')));
      if (!STAFF.includes(S.role)) return go('/');
      return await adminShell(parts[1], q);
    }
    if (parts[0] === 'login' || parts[0] === 'registro') return await authView(parts[0], q);
    if (parts[0] === 'pedidos' && !S.tok) return go('/login?next=pedidos');
    root.innerHTML = storeShell(parts[0] || '');
    bindShell();
    const view = {'': home, inicio: home, productos: productos, producto: producto, compra: compra, nosotros: nosotros,
      contacto: contacto, pedidos: pedidos}[parts[0] || ''] || notFound;
    await view(parts, q);
    window.scrollTo({top: 0});
  } catch (e) { toast(e.message, 'bad'); }
}

/* ---------------- shell de la tienda ---------------- */
function storeShell(cur) {
  const n = cartCount();
  const userMenu = S.tok ? `<div class="dd" id="userdd"><button class="btn ghost sm" aria-haspopup="true" aria-expanded="false">${I('user', 16)} ${esc(S.name)}</button>
      <div class="dd-menu" style="left:auto;right:0;min-width:200px">
        ${STAFF.includes(S.role) ? `<a href="#/admin">${I('chart', 18)} ${t('panel')}</a>` : ''}
        ${S.role === 'cliente' || S.role === 'administrador' ? `<a href="#/pedidos">${I('receipt', 18)} ${t('orders')}</a>` : ''}
        <button onclick="logout()">${I('logout', 18)} ${t('logout')}</button>
        <button onclick="logout(false, true)">${I('lock', 18)} Cerrar en todos los dispositivos</button></div></div>`
    : `<a class="btn ghost sm" href="#/login">${I('user', 16)} ${t('login')}</a>`;
  return `
  <div class="topbar"><div class="wrap">
    <span>${I('phone', 13).replace('<svg', '<svg style="display:inline;vertical-align:-2px"')} Teléfonos <a href="tel:+573104772730">${COMPANY.phone1}</a> o <a href="tel:+573212047803">${COMPANY.phone2}</a></span>
    <span class="opts">
      <label>${t('lang')} <select id="lang" aria-label="${t('lang')}"><option value="es" ${S.lang === 'es' ? 'selected' : ''}>Español</option><option value="en" ${S.lang === 'en' ? 'selected' : ''}>English</option></select></label>
      <label>${t('theme')} <select id="theme" aria-label="${t('theme')}"><option value="light" ${S.theme === 'light' ? 'selected' : ''}>${t('light')}</option><option value="dark" ${S.theme === 'dark' ? 'selected' : ''}>${t('dark')}</option></select></label>
    </span></div></div>
  <header class="mainhead"><div class="wrap">
    <a href="#/" class="logo" aria-label="Universal de Repuestos WG — inicio">${ART.logo(46)}<span><b>Universal de</b><b>Repuestos <small>WG</small></b></span></a>
    <nav class="mainnav" id="mainnav" aria-label="Principal">
      <a href="#/" class="${!cur || cur === 'inicio' ? 'on' : ''}">${t('home')}</a>
      <div class="dd" id="proddd"><button aria-haspopup="true" aria-expanded="false" class="${cur === 'productos' || cur === 'producto' ? 'on' : ''}">${t('products')} ▾</button>
        <div class="dd-menu" id="prodmenu"><a href="#/productos"><b>${t('all')}</b></a></div></div>
      <a href="#/nosotros" class="${cur === 'nosotros' ? 'on' : ''}">${t('about')}</a>
      <a href="#/contacto" class="${cur === 'contacto' ? 'on' : ''}">${t('contact')}</a>
    </nav>
    <div class="headact">${userMenu}
      <a href="#/compra" class="cartbtn" aria-label="${t('cart')}: ${n} productos">${I('cart', 28)}<span class="n" data-cartn ${n ? '' : 'hidden'}>${n}</span></a>
      <button class="btn ghost icon menubtn" id="menubtn" aria-label="Menú" aria-controls="mainnav">${I('menu')}</button></div>
  </div></header>
  <div class="greenbar"><div class="wrap">
    <button class="fbtn" id="fbtn" title="Filtrar por vehículo" aria-label="Filtrar por vehículo">${I('filter', 22)}</button>
    <div class="dd" id="catdd"><button class="catbtn" aria-haspopup="true" aria-expanded="false">${I('menu', 20)} <span>${t('categories')}</span> <i class="car">${I('down', 18)}</i></button>
      <div class="dd-menu" id="catmenu"></div></div>
    <form class="search" id="searchf" role="search"><label class="sr" for="sq">${t('search')}</label>
      <input id="sq" name="q" placeholder="${t('search')}" value="${esc(route().q.get('q') || '')}" autocomplete="off">
      <button aria-label="Buscar">${I('search', 22)}</button></form>
  </div></div>
  <main id="main"></main>
  <footer class="footer"><div class="wrap"><div class="cols">
    <div><div class="logo" style="margin-bottom:12px">${ART.logo(40)}<span style="color:#fff"><b>Universal de</b><b>Repuestos WG</b></span></div>
      <p>Repuestos automotrices con garantía, asesoría por referencia y despacho a domicilio en Bogotá y todo el país.</p></div>
    <div><h4>Tienda</h4><a href="#/productos">Productos</a><a href="#/compra">Carrito</a><a href="#/pedidos">Mis pedidos</a><a href="#/login">Ingresar</a></div>
    <div><h4>Contacto</h4><a href="tel:${COMPANY.tel}">${COMPANY.phone1}</a><a href="mailto:${COMPANY.email}">${COMPANY.email}</a><a href="#/contacto">${COMPANY.address}</a></div>
  </div><div class="copy">© ${new Date().getFullYear()} Universal de Repuestos WG · Precios en pesos colombianos con IVA incluido.</div></div></footer>`;
}
function bindShell() {
  $('#lang').onchange = e => { S.lang = e.target.value; store.set('lang', S.lang); render(); };
  $('#theme').onchange = e => { S.theme = e.target.value; store.set('theme', S.theme); document.documentElement.dataset.theme = S.theme; };
  $('#searchf').onsubmit = e => { e.preventDefault(); const v = $('#sq').value.trim(); go('/productos' + (v ? '?q=' + encodeURIComponent(v) : '')); };
  $('#menubtn').onclick = () => $('#mainnav').classList.toggle('open');
  $('#fbtn').onclick = () => { const v = $('#vsel'); if (v) { v.scrollIntoView({block: 'center'}); $('#vs-brand').focus(); } else go('/?filtro=1'); };
  $$('.dd').forEach(dd => {
    const b = dd.querySelector('button');
    b.onclick = e => { e.stopPropagation(); const o = !dd.classList.contains('open'); $$('.dd.open').forEach(x => x.classList.remove('open')); dd.classList.toggle('open', o); b.setAttribute('aria-expanded', o); };
  });
  loadCats().then(cats => {
    const items = cats.map(c => `<a href="#/productos?cat=${c.spare_part_type_id}"><span class="ico">${ART.part(c.name, 28)}</span>${esc(c.name)}</a>`).join('');
    $('#catmenu') && ($('#catmenu').innerHTML = items);
    $('#prodmenu') && ($('#prodmenu').innerHTML = `<a href="#/productos"><b>${t('all')}</b></a>` + items);
  }).catch(() => {});
}
document.addEventListener('click', () => $$('.dd.open').forEach(x => x.classList.remove('open')));
document.addEventListener('keydown', e => { if (e.key === 'Escape') $$('.dd.open').forEach(x => x.classList.remove('open')); });

/* ---------------- tarjetas de producto ---------------- */
function pcard(p) {
  const out = p.stock_total < 1;
  return `<article class="pcard"><a class="art" href="#/producto/${p.product_id}" aria-label="${esc(p.name)}">
      ${p.category ? `<span class="badge">${esc(p.category)}</span>` : ''}${ART.part(p.category, 120)}</a>
    <div class="body"><h3><a href="#/producto/${p.product_id}">${esc(p.name)}</a></h3><p class="desc">${esc(p.description || '')}</p>
      <div class="foot"><span class="price">${cop(withIva(p.unit_price))}<small>${t('ivaInc')}</small></span>
        <button class="btn sm" ${out ? 'disabled' : ''} onclick="A.add(${p.product_id})" aria-label="${t('add')} ${esc(p.name)}">${out ? t('out') : I('plus', 16) + ' ' + t('add')}</button></div></div></article>`;
}
const skeleton = n => Array.from({length: n}, () => '<div class="skel"></div>').join('');
const A = window.A = {};
A.add = run(async (id, qty = 1) => {
  const p = (await loadAll()).find(x => x.product_id === id) || await api(await conBodega('/products/' + id));
  const it = S.cart.find(x => x.id === id);
  const max = p.stock_total;
  if (max < 1) return toast('Producto agotado', 'bad');
  if (it) { if (it.qty >= max) return toast(`Solo hay ${max} unidades disponibles`, 'bad'); it.qty = Math.min(it.qty + qty, max); it.max = max; }
  else S.cart.push({id, name: p.name, price: Number(p.unit_price), qty: Math.min(qty, max), max, cat: p.category, cars: p.fk_car_product || []});
  saveCart();
  toast(`${p.name} agregado al carrito`, 'ok');
  if ($('#orderpanel')) refreshOrder();
});
A.qty = (id, d) => {
  const it = S.cart.find(x => x.id === id); if (!it) return;
  it.qty += d;
  if (it.qty > it.max) { it.qty = it.max; toast(`Solo hay ${it.max} unidades disponibles`, 'bad'); }
  if (it.qty < 1) S.cart = S.cart.filter(x => x.id !== id);
  saveCart(); refreshOrder();
  if (route().parts[0] === 'compra') compraList();
};

/* ---------------- inicio ---------------- */
const SLIDES = [
  {t: 'Repuestos que te mueven', p: 'Más de 20 categorías de repuestos para las marcas más vendidas en Colombia, con garantía y asesoría experta por referencia.', c: '#e9edf0'},
  {t: 'Radiadores con garantía', p: 'Radiadores con tanques plásticos y núcleo de aluminio: 6 meses de garantía para carro particular y 3 meses para taxi.', c: '#c9302c', cat: 'Radiadores'},
  {t: 'Despacho el mismo día', p: 'Haz tu pedido antes de las 2:00 p. m. y recíbelo hoy en Bogotá. Seguimiento con número de guía.', c: '#2d3a45'},
];
async function home(parts, q) {
  const m = $('#main');
  m.innerHTML = `<section class="hero" aria-roledescription="carrusel" aria-label="Destacados">
    ${SLIDES.map((s, i) => `<div class="slide ${i ? '' : 'on'}" role="group" aria-roledescription="diapositiva" aria-label="${i + 1} de ${SLIDES.length}" ${i ? 'aria-hidden="true"' : ''}>
      <div class="bg">${ART.forest(i + 1)}</div>
      <div class="wrap"><div><h1>${esc(s.t)}</h1><p>“${esc(s.p)}”</p>
        <a class="btn lg" href="${s.cat ? '#/productos?catname=' + encodeURIComponent(s.cat) : '#/nosotros'}">${s.cat ? 'Ver radiadores' : t('meet')}</a></div>
        <div class="carimg">${ART.car(s.c)}</div></div></div>`).join('')}
    <button class="arrow prev" aria-label="Anterior">${I('left')}</button><button class="arrow next" aria-label="Siguiente">${I('right')}</button>
    <div class="dots">${SLIDES.map((_, i) => `<button class="${i ? '' : 'on'}" aria-label="Ir a la diapositiva ${i + 1}"></button>`).join('')}</div>
  </section>
  <div class="wrap"><form class="vsel" id="vsel" aria-label="${t('pickCar')}"><strong>${t('pickCar')}</strong>
    <label class="sr" for="vs-brand">Marca</label><select id="vs-brand"><option value="">${t('brand')}</option></select>
    <label class="sr" for="vs-model">Modelo</label><select id="vs-model" disabled><option value="">${t('model')}</option></select>
    <label class="sr" for="vs-year">Año</label><select id="vs-year" disabled><option value="">${t('year')}</option></select>
    <button class="go" aria-label="Buscar repuestos para el vehículo">${I('search', 22)}</button></form></div>
  <section class="section wrap"><h2 class="stitle">${t('categories')}</h2><p class="ssub">Encuentra el repuesto por tipo de sistema</p><div class="cats" id="cats">${skeleton(4)}</div>
    <p class="center" style="margin-top:18px"><button class="btn ghost" id="morecats" hidden>Ver todas las categorías</button></p></section>
  <section class="section wrap"><h2 class="stitle g">Radiadores</h2><p class="ssub">Los más pedidos esta semana</p><div class="products" id="feat">${skeleton(4)}</div>
    <p class="center" style="margin-top:22px"><a class="btn" href="#/productos?catname=Radiadores">Ver todos los radiadores</a></p></section>`;
  carousel();
  vehicleSelector();
  if (q.get('filtro')) setTimeout(() => { $('#vsel').scrollIntoView({block: 'center'}); $('#vs-brand').focus(); }, 50);
  const [cats, prods] = await Promise.all([loadCats(), loadAll()]);
  const count = {};
  prods.forEach(p => { if (p.category_id) count[p.category_id] = (count[p.category_id] || 0) + 1; });
  const sorted = [...cats].sort((a, b) => (count[b.spare_part_type_id] || 0) - (count[a.spare_part_type_id] || 0));
  const card = c => `<a class="cat" href="#/productos?cat=${c.spare_part_type_id}"><span class="lbl">${esc(c.name)}</span>
    <div class="art">${ART.part(c.name, 110)}</div><div class="more"><span>${count[c.spare_part_type_id] || 0} productos · ${t('more')}</span>${I('right', 16)}</div></a>`;
  $('#cats').innerHTML = sorted.slice(0, 8).map(card).join('');
  if (sorted.length > 8) { const b = $('#morecats'); b.hidden = false; b.onclick = () => { $('#cats').innerHTML = sorted.map(card).join(''); b.hidden = true; }; }
  const rad = prods.filter(p => (p.category || '').toLowerCase().includes('radiador'));
  $('#feat').innerHTML = (rad.length ? rad : prods).slice(0, 4).map(pcard).join('') || '<p class="empty">Aún no hay productos</p>';
}
function carousel() {
  const slides = $$('.slide'), dots = $$('.dots button'); let i = 0, paused = false;
  const show = n => { i = (n + slides.length) % slides.length;
    slides.forEach((s, k) => { s.classList.toggle('on', k === i); s.setAttribute('aria-hidden', k !== i); });
    dots.forEach((d, k) => d.classList.toggle('on', k === i)); };
  $('.hero .prev').onclick = () => show(i - 1); $('.hero .next').onclick = () => show(i + 1);
  dots.forEach((d, k) => d.onclick = () => show(k));
  const hero = $('.hero'); hero.onmouseenter = () => paused = true; hero.onmouseleave = () => paused = false;
  hero.addEventListener('focusin', () => paused = true); hero.addEventListener('focusout', () => paused = false);
  if (!matchMedia('(prefers-reduced-motion: reduce)').matches) S.timers.push(setInterval(() => !paused && show(i + 1), 6500));
}
async function vehicleSelector() {
  const [cars, brands] = await Promise.all([loadCars(), loadBrands()]);
  const b = $('#vs-brand'), mo = $('#vs-model'), y = $('#vs-year');
  if (!b) return;
  const used = brands.filter(br => cars.some(c => c.car_brand_id === br.car_brand_id));
  b.innerHTML += used.map(br => `<option value="${br.car_brand_id}">${esc(br.name)}</option>`).join('');
  b.onchange = () => {
    const names = [...new Set(cars.filter(c => c.car_brand_id == b.value).map(c => c.name))].sort();
    mo.innerHTML = `<option value="">${t('model')}</option>` + names.map(n => `<option>${esc(n)}</option>`).join('');
    mo.disabled = !b.value; y.innerHTML = `<option value="">${t('year')}</option>`; y.disabled = true;
  };
  mo.onchange = () => {
    const list = cars.filter(c => c.car_brand_id == b.value && c.name === mo.value).sort((a, c) => String(c.model).localeCompare(a.model));
    y.innerHTML = `<option value="">${t('year')}</option>` + list.map(c => `<option value="${c.car_id}">${esc(c.model || c.name)}</option>`).join('');
    y.disabled = !mo.value;
    if (list.length === 1) y.value = list[0].car_id;
  };
  $('#vsel').onsubmit = e => {
    e.preventDefault();
    if (y.value) return go('/productos?car=' + y.value);
    if (mo.value) { const ids = cars.filter(c => c.car_brand_id == b.value && c.name === mo.value); return go('/productos?car=' + ids[0].car_id); }
    if (b.value) return go('/productos?brand=' + b.value);
    toast('Selecciona al menos la marca de tu vehículo', 'bad'); b.focus();
  };
}

/* ---------------- listado de productos ---------------- */
async function productos(parts, q) {
  const [cats, cars, brands] = await Promise.all([loadCats(), loadCars(), loadBrands()]);
  if (q.get('catname')) { const c = cats.find(x => x.name.toLowerCase() === q.get('catname').toLowerCase()); if (c) { q.delete('catname'); q.set('cat', c.spare_part_type_id); } }
  const cat = cats.find(c => c.spare_part_type_id == q.get('cat'));
  const car = cars.find(c => c.car_id == q.get('car'));
  const brand = brands.find(b => b.car_brand_id == q.get('brand'));
  const params = new URLSearchParams();
  if (cat) params.set('type_id', cat.spare_part_type_id);
  if (car) params.set('car_id', car.car_id);
  if (brand) params.set('car_brand_id', brand.car_brand_id);
  if (q.get('q')) params.set('q', q.get('q'));
  const link = (k, v) => { const n = new URLSearchParams(q); v == null ? n.delete(k) : n.set(k, v); const s = n.toString(); return '#/productos' + (s ? '?' + s : ''); };
  const chips = [cat && ['cat', 'Categoría: ' + cat.name], car && ['car', 'Vehículo: ' + carLabel(car)], brand && ['brand', 'Marca: ' + brand.name], q.get('q') && ['q', `“${q.get('q')}”`]].filter(Boolean);
  const m = $('#main');
  m.innerHTML = `<div class="wrap"><nav class="crumbs" aria-label="Ruta"><a href="#/">${t('home')}</a>›<a href="#/productos">${t('products')}</a>${cat ? '›<span>' + esc(cat.name) + '</span>' : ''}</nav>
    <h1 class="stitle" style="text-align:left">${esc(cat ? cat.name : car ? 'Repuestos para ' + carLabel(car) : t('products'))}</h1>
    <div class="chips" style="margin:14px 0 4px" role="list" aria-label="Categorías">
      <a class="chip out ${cat ? '' : 'on'}" href="${link('cat', null)}">Todas</a>
      ${cats.map(c => `<a role="listitem" class="chip out ${cat && c.spare_part_type_id === cat.spare_part_type_id ? 'on' : ''}" href="${link('cat', c.spare_part_type_id)}">${esc(c.name)}</a>`).join('')}</div>
    <div class="listhead"><div class="chips">${chips.map(([k, l]) => `<a class="chip" href="${link(k, null)}" aria-label="Quitar filtro ${esc(l)}">${esc(l)} ${I('x', 14)}</a>`).join('')}
      <span class="mut small" id="count" aria-live="polite"></span></div>
      <label class="small mut">Ordenar por <select class="input" id="sort" style="width:auto;min-height:36px;display:inline-block">
        <option value="rel">Relevancia</option><option value="pa">Precio: menor a mayor</option><option value="pd">Precio: mayor a menor</option><option value="n">Nombre</option></select></label></div>
    <div class="products" id="plist">${skeleton(8)}</div></div>`;
  const list = await api(await conBodega('/products?' + params));
  const draw = () => {
    const s = $('#sort').value, l = [...list];
    if (s === 'pa') l.sort((a, b) => a.unit_price - b.unit_price);
    if (s === 'pd') l.sort((a, b) => b.unit_price - a.unit_price);
    if (s === 'n') l.sort((a, b) => a.name.localeCompare(b.name));
    $('#count').textContent = `${l.length} resultado${l.length === 1 ? '' : 's'}`;
    $('#plist').innerHTML = l.map(pcard).join('') || `<div class="empty" style="grid-column:1/-1">${ART.part('', 90)}<h3>No encontramos repuestos con esos filtros</h3>
      <p>Prueba quitando un filtro o <a href="#/contacto">contáctanos</a> y te ayudamos a conseguirlo.</p><a class="btn" href="#/productos">Ver todos los productos</a></div>`;
  };
  $('#sort').onchange = draw; draw();
}

/* ---------------- detalle de producto (página de compra) ---------------- */
async function producto(parts) {
  const id = +parts[1];
  const [p, cars] = await Promise.all([api(await conBodega('/products/' + id)), loadCars()]);
  const comp = cars.filter(c => (p.fk_car_product || []).includes(c.car_id));
  const views = [{bg: '', s: 260}, {bg: 'background:radial-gradient(circle,#2a3b31,#0d1711)', s: 230}, {bg: 'background:radial-gradient(circle,#f8fbf9,#d6e4da)', s: 300}];
  const out = p.stock_total < 1;
  let qty = 1;
  $('#main').innerHTML = `<div class="wrap"><nav class="crumbs" aria-label="Ruta"><a href="#/">${t('home')}</a>›<a href="#/productos">${t('products')}</a>
      ${p.category ? `›<a href="#/productos?cat=${p.category_id}">${esc(p.category)}</a>` : ''}›<span>${esc(p.name)}</span></nav>
    <div class="buy"><div>
      <div class="gallery" aria-roledescription="carrusel" aria-label="Imágenes del producto">
        <div class="stage" id="stage" style="${views[0].bg}">${ART.part(p.category, views[0].s)}</div>
        <button class="arrow prev" aria-label="Imagen anterior">${I('left')}</button><button class="arrow next" aria-label="Imagen siguiente">${I('right')}</button>
        <div class="thumbs">${views.map((v, i) => `<button class="${i ? '' : 'on'}" style="${v.bg}" aria-label="Imagen ${i + 1}">${ART.part(p.category, 40)}</button>`).join('')}</div>
      </div>
      <section class="pinfo" aria-labelledby="pname"><h1 id="pname">${esc(p.name)}</h1><p>${esc(p.description || '')}</p>
        <div class="row"><div class="big">${cop(withIva(p.unit_price))}<small>${t('ivaInc')} · ${cop(p.unit_price)} + IVA</small></div>
          <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
            <div class="stepper" aria-label="Cantidad"><button type="button" id="qm" aria-label="Disminuir">−</button><span id="qv" aria-live="polite">1</span><button type="button" id="qp" aria-label="Aumentar">+</button></div>
            <button class="btn" style="background:#fff;color:var(--g)" id="addb" ${out ? 'disabled' : ''}>${out ? t('out') : I('cart', 18) + ' Agregar al carrito'}</button></div></div></section>
      <div class="meta">
        <div><h4>Disponibilidad</h4>${out ? '<span class="badge bad">Agotado</span>' : p.stock_total <= 5 ? `<span class="badge warn">Últimas ${p.stock_total} unidades</span>` : `<span class="badge ok">${p.stock_total} unidades disponibles</span>`}
          ${p.part_brand ? ` <span class="badge">Marca ${esc(p.part_brand)}</span>` : ''}</div>
        <div><h4>Vehículos compatibles</h4><div class="chips">${comp.map(c => `<a class="chip out" href="#/productos?car=${c.car_id}">${esc(carLabel(c))}</a>`).join('') || '<span class="mut">Consulta compatibilidad con un asesor.</span>'}</div></div>
        <div class="mut small">${I('shield', 16).replace('<svg', '<svg style="display:inline;vertical-align:-3px"')} Garantía por defectos de fábrica · Factura electrónica · Cambios dentro de los 5 días hábiles</div>
      </div></div>
      <aside id="orderpanel" aria-label="${t('myRequest')}"></aside></div>
    <section class="section" style="padding-top:10px"><h2 class="stitle g">Productos relacionados</h2><div class="products" id="rel"></div></section></div>`;
  let v = 0;
  const show = n => { v = (n + views.length) % views.length; $('#stage').style.cssText = views[v].bg; $('#stage').innerHTML = ART.part(p.category, views[v].s);
    $$('.thumbs button').forEach((b, k) => b.classList.toggle('on', k === v)); };
  $('.gallery .prev').onclick = () => show(v - 1); $('.gallery .next').onclick = () => show(v + 1);
  $$('.thumbs button').forEach((b, k) => b.onclick = () => show(k));
  $('#qm').onclick = () => { qty = Math.max(1, qty - 1); $('#qv').textContent = qty; };
  $('#qp').onclick = () => { qty = Math.min(Math.max(1, p.stock_total), qty + 1); $('#qv').textContent = qty; };
  $('#addb').onclick = () => A.add(p.product_id, qty);
  refreshOrder();
  const all = await loadAll();
  $('#rel').innerHTML = all.filter(x => x.category_id === p.category_id && x.product_id !== p.product_id).slice(0, 4).map(pcard).join('')
    || all.filter(x => x.product_id !== p.product_id).slice(0, 4).map(pcard).join('');
}

/* ---------------- panel de solicitud (carrito lateral) ---------------- */
function refreshOrder() {
  const box = $('#orderpanel'); if (!box) return;
  const sub = cartSubtotal(), tax = Math.round(sub * IVA);
  box.className = 'order';
  box.innerHTML = `<h2>${t('myRequest')} <span class="badge">${cartCount()} ítems</span></h2>
    <div class="lines">${S.cart.map((i, k) => `<div class="line"><span class="num">${k + 1}</span>
        <span class="nm" title="${esc(i.name)}">${esc(i.name)}<small>${esc(i.cat || '')} · ${cop(withIva(i.price))} c/u</small></span>
        <span class="act"><span>${cop(withIva(i.price * i.qty))}</span>
          <button onclick="A.qty(${i.id},-1)" aria-label="Quitar una unidad de ${esc(i.name)}">−</button><span aria-label="cantidad">${i.qty}</span>
          <button onclick="A.qty(${i.id},1)" aria-label="Agregar una unidad de ${esc(i.name)}">+</button></span></div>`).join('')
      || `<div class="empty" style="padding:20px">${I('cart', 34).replace('<svg', '<svg style="margin:0 auto 8px"')}Tu solicitud está vacía.<br><a href="#/productos" style="color:var(--g);font-weight:600">Explorar productos</a></div>`}</div>
    <label class="field"><span>${t('reqDesc')}</span><textarea class="input" id="note" maxlength="250" placeholder="Ej.: referencia, placa del vehículo o indicaciones">${esc(S.note)}</textarea></label>
    <div class="totals"><div><span class="mut">Subtotal</span><span>${cop(sub)}</span></div><div><span class="mut">IVA 19 %</span><span>${cop(tax)}</span></div>
      <div class="t"><span>${t('total')}</span><span>${cop(sub + tax)}</span></div></div>
    <button class="btn lg block" id="solicitar" ${S.cart.length ? '' : 'disabled'}>${t('request').toUpperCase()}</button>
    <div class="paylogos" aria-label="Medios de pago"><span>PSE</span><span>VISA</span><span>Mastercard</span><span>Nequi</span><span>Efectivo</span></div>
    <div class="secure">${I('lock', 14)} Pago seguro · nunca guardamos los datos de tu tarjeta</div>`;
  $('#note').oninput = e => S.note = e.target.value;
  $('#solicitar').onclick = startCheckout;
}

/* ---------------- carrito completo ---------------- */
async function compra() {
  $('#main').innerHTML = `<div class="wrap"><nav class="crumbs"><a href="#/">${t('home')}</a>›<span>${t('cart')}</span></nav>
    <div class="buy"><div><h1 class="stitle" style="text-align:left">Carrito de compras</h1><div id="clist" class="olist"></div></div><aside id="orderpanel"></aside></div></div>`;
  compraList(); refreshOrder();
  // refresca stock disponible
  try {
    const all = await api(await conBodega('/products')); S.cache.allProducts = Promise.resolve(all);
    let changed = false;
    S.cart.forEach(i => { const p = all.find(x => x.product_id === i.id); if (!p) return; i.max = p.stock_total; i.price = Number(p.unit_price);
      if (i.qty > i.max) { i.qty = i.max; changed = true; } });
    S.cart = S.cart.filter(i => i.qty > 0); saveCart(); compraList(); refreshOrder();
    if (changed) toast('Ajustamos cantidades según el stock disponible', 'bad');
  } catch (e) { /* sin conexión: se usa la copia local */ }
}
function compraList() {
  const box = $('#clist'); if (!box) return;
  box.innerHTML = S.cart.map(i => `<div class="card ocard"><div style="display:flex;gap:16px;align-items:center">
      <a href="#/producto/${i.id}" style="width:84px;height:84px;border-radius:12px;background:var(--line-2);display:grid;place-items:center;flex-shrink:0">${ART.part(i.cat, 64)}</a>
      <div><a href="#/producto/${i.id}" style="text-decoration:none"><b>${esc(i.name)}</b></a><div class="mut small">${esc(i.cat || '')} · ${cop(withIva(i.price))} c/u · ${i.max} disponibles</div>
      <div class="stepper" style="background:var(--g-soft);color:var(--g);margin-top:8px"><button onclick="A.qty(${i.id},-1)" aria-label="Disminuir">−</button><span>${i.qty}</span><button onclick="A.qty(${i.id},1)" aria-label="Aumentar">+</button></div></div></div>
    <div class="acts"><span class="price">${cop(withIva(i.price * i.qty))}</span><button class="btn danger sm" onclick="A.qty(${i.id},-${i.qty})">Eliminar</button></div></div>`).join('')
    || `<div class="card empty">${ART.part('', 90)}<h3>Tu carrito está vacío</h3><p>Busca por categoría o por tu vehículo para encontrar el repuesto correcto.</p><a class="btn" href="#/productos">Ir a la tienda</a></div>`;
}

/* ================================================================ CHECKOUT Y PAGO */
const CK = {};
function startCheckout() {
  if (!S.cart.length) return;
  if (!S.tok) { toast('Inicia sesión o crea una cuenta para enviar tu solicitud'); return go('/login?next=compra'); }
  if (!['cliente', 'administrador'].includes(S.role)) return toast('Tu rol no permite realizar compras. Ingresa con una cuenta de cliente.', 'bad');
  Object.assign(CK, {step: 1, sale: null, address: store.get('addr') || '', note: S.note, method: 'tarjeta_credito', error: ''});
  drawCheckout();
}
function openPay(sale) { Object.assign(CK, {step: 2, sale, address: '', note: '', method: 'tarjeta_credito', error: ''}); drawCheckout(); }
function ckTotals() {
  if (CK.sale) return {sub: CK.sale.subtotal, tax: CK.sale.tax, total: CK.sale.total};
  const sub = cartSubtotal(), tax = Math.round(sub * IVA); return {sub, tax, total: sub + tax};
}
const METHODS = [['tarjeta_credito', 'Tarjeta de crédito', 'card'], ['tarjeta_debito', 'Tarjeta débito', 'card'], ['pse', 'PSE', 'bank'],
  ['transferencia', 'Transferencia', 'wallet'], ['nequi', 'Nequi', 'phone'], ['efectivo', 'Efectivo contra entrega', 'cash']];
function drawCheckout() {
  const tt = ckTotals();
  const steps = `<div class="steps" aria-hidden="true"><div class="on"></div><div class="${CK.step >= 2 ? 'on' : ''}"></div><div class="${CK.step >= 3 ? 'on' : ''}"></div></div>`;
  const summary = `<div class="summary">${CK.sale ? `<div><span>Pedido</span><b>#${CK.sale.sale_id}</b></div>` : `<div><span>${cartCount()} productos</span><span></span></div>`}
    <div><span class="mut">Subtotal</span><span>${cop(tt.sub)}</span></div><div><span class="mut">IVA 19 %</span><span>${cop(tt.tax)}</span></div>
    <div style="font-weight:800;font-size:17px"><span>Total a pagar</span><span>${cop(tt.total)}</span></div></div>`;
  const err = CK.error ? `<div class="notice bad" role="alert">${I('alert', 18)}<span>${esc(CK.error)}</span></div>` : '';
  if (CK.step === 1) {
    openModal(`${mhead('Datos de entrega')}<form id="ck1"><div class="mbody form">${steps}
      <label class="field"><span>Dirección de entrega *</span><input class="input" name="address" required minlength="6" maxlength="200" autocomplete="street-address" value="${esc(CK.address)}" placeholder="Ej.: Calle 63F #25-49, Bogotá" autofocus></label>
      <label class="field"><span>Descripción de la cotización o compra</span><textarea class="input" name="note" maxlength="250" placeholder="Referencia, placa, horario de recepción…">${esc(CK.note)}</textarea></label>
      ${summary}</div>
      <div class="mfoot"><button type="button" class="btn ghost" onclick="closeModal()">Cancelar</button><button class="btn">Continuar al pago ${I('right', 16)}</button></div></form>`);
    $('#ck1').onsubmit = e => { e.preventDefault(); const d = formData(e.target); CK.address = d.address.trim(); CK.note = d.note.trim(); store.set('addr', CK.address); CK.step = 2; drawCheckout(); };
    return;
  }
  if (CK.step === 2) {
    openModal(`${mhead(CK.sale ? `Pagar pedido #${CK.sale.sale_id}` : 'Método de pago')}<form id="ck2" novalidate><div class="mbody form">${steps}${err}
      <fieldset style="border:0;padding:0;margin:0"><legend class="small mut" style="margin-bottom:8px;font-weight:600">Elige cómo pagar</legend>
      <div class="methods">${METHODS.map(([k, l, ic]) => `<label class="method"><input type="radio" name="method" value="${k}" ${CK.method === k ? 'checked' : ''}>${I(ic, 26)}${l}</label>`).join('')}</div></fieldset>
      <div id="mfields"></div>${summary}</div>
      <div class="mfoot">${CK.sale ? '' : '<button type="button" class="btn ghost" id="back">Atrás</button><button type="button" class="btn ghost" id="later">Enviar solicitud y pagar después</button>'}
        <button class="btn" id="paybtn">${I('lock', 16)} Pagar ${cop(tt.total)}</button></div></form>`);
    const fields = () => {
      const m = CK.method;
      $('#mfields').innerHTML = m.startsWith('tarjeta') ? `<div class="form">
          <label class="field"><span>Número de tarjeta</span><input class="input" id="cn" inputmode="numeric" autocomplete="cc-number" placeholder="4111 1111 1111 1111" maxlength="23"></label>
          <label class="field"><span>Nombre del titular</span><input class="input" id="ch" autocomplete="cc-name" placeholder="Como aparece en la tarjeta"></label>
          <div class="grid2"><label class="field"><span>Vencimiento (MM/AA)</span><input class="input" id="ce" inputmode="numeric" autocomplete="cc-exp" placeholder="08/29" maxlength="5"></label>
          <label class="field"><span>CVV</span><input class="input" id="cv" inputmode="numeric" autocomplete="cc-csc" placeholder="123" maxlength="4"></label></div>
          <p class="err" id="cerr" role="alert"></p><p class="small mut">Pasarela de pago simulada con fines académicos: solo se registran los últimos 4 dígitos.</p></div>`
        : m === 'pse' ? `<div class="grid2"><label class="field"><span>Banco</span><select class="input" id="bank">${['Bancolombia', 'Banco de Bogotá', 'Davivienda', 'BBVA', 'Banco de Occidente', 'Banco Popular', 'Scotiabank Colpatria', 'Nequi', 'Daviplata'].map(b => `<option>${b}</option>`).join('')}</select></label>
          <label class="field"><span>Tipo de persona</span><select class="input"><option>Natural</option><option>Jurídica</option></select></label></div><p class="small mut">Serás redirigido a tu banco (simulado) para aprobar el pago.</p>`
        : m === 'efectivo' ? '<div class="notice">Pagas al recibir. El pedido se registra como pagado al confirmar y el repartidor recauda el valor exacto.</div>'
        : m === 'nequi' ? '<label class="field"><span>Celular Nequi</span><input class="input" id="nq" inputmode="numeric" maxlength="10" placeholder="3001234567"></label><p class="err" id="cerr" role="alert"></p>'
        : `<div class="notice">Transfiere a la cuenta de ahorros Bancolombia 123-456789-00 a nombre de Universal de Repuestos WG (NIT 900123456-1) y conserva el comprobante.</div>`;
      const cn = $('#cn'); if (cn) cn.oninput = () => { cn.value = cn.value.replace(/\D/g, '').slice(0, 19).replace(/(\d{4})(?=\d)/g, '$1 '); };
      const ce = $('#ce'); if (ce) ce.oninput = () => { let v = ce.value.replace(/\D/g, '').slice(0, 4); if (v.length > 2) v = v.slice(0, 2) + '/' + v.slice(2); ce.value = v; };
    };
    fields();
    $$('input[name=method]').forEach(r => r.onchange = () => { CK.method = r.value; fields(); });
    if ($('#back')) $('#back').onclick = () => { CK.step = 1; CK.error = ''; drawCheckout(); };
    if ($('#later')) $('#later').onclick = e => busy(e.currentTarget, () => submitCheckout(false));
    $('#ck2').onsubmit = e => { e.preventDefault(); const extra = validatePay(); if (extra) busy($('#paybtn'), () => submitCheckout(true, extra)); };
    return;
  }
  // paso 3: resultado
  const paid = CK.sale && CK.sale.state === 'Pagada';
  openModal(`${mhead(paid ? 'Pago aprobado' : 'Solicitud enviada')}<div class="mbody">${steps}<div class="done">
      <div class="ok">${I('check', 38)}</div><h2>${paid ? '¡Gracias por tu compra!' : '¡Recibimos tu solicitud!'}</h2>
      <p class="mut">Pedido <b>#${CK.sale.sale_id}</b> por <b>${cop(CK.sale.total)}</b>. ${paid ? `Pago con ${esc(METHOD_LABEL[CK.payMethod] || '')} aprobado. Te avisaremos cuando sea despachado.` : 'Quedó pendiente de pago: puedes pagarlo cuando quieras desde “Mis pedidos”.'}</p>
      ${paid && CK.reference ? `<p class="small mut">Referencia de pago: ${esc(CK.reference)}</p>` : ''}</div></div>
    <div class="mfoot"><button class="btn ghost" onclick="closeModal();go('/productos')">Seguir comprando</button><button class="btn" onclick="closeModal();go('/pedidos')">Ver mis pedidos</button></div>`);
}
function luhn(n) { let s = 0, alt = false; for (let i = n.length - 1; i >= 0; i--) { let d = +n[i]; if (alt) { d *= 2; if (d > 9) d -= 9; } s += d; alt = !alt; } return s % 10 === 0; }
function validatePay() {
  const m = CK.method, err = msg => { const e = $('#cerr'); if (e) e.textContent = msg; return null; };
  if (m.startsWith('tarjeta')) {
    const n = $('#cn').value.replace(/\D/g, ''), [mm, yy] = $('#ce').value.split('/').map(Number), now = new Date();
    $$('#mfields .input').forEach(i => i.removeAttribute('aria-invalid'));
    if (n.length < 13 || !luhn(n)) { $('#cn').setAttribute('aria-invalid', true); $('#cn').focus(); return err('Número de tarjeta inválido. Prueba con 4111 1111 1111 1111.'); }
    if (!$('#ch').value.trim()) { $('#ch').setAttribute('aria-invalid', true); $('#ch').focus(); return err('Escribe el nombre del titular.'); }
    if (!mm || mm > 12 || !yy || new Date(2000 + yy, mm) <= now) { $('#ce').setAttribute('aria-invalid', true); $('#ce').focus(); return err('Fecha de vencimiento inválida o vencida.'); }
    if (!/^\d{3,4}$/.test($('#cv').value)) { $('#cv').setAttribute('aria-invalid', true); $('#cv').focus(); return err('CVV inválido.'); }
    return {card_last4: n.slice(-4)};
  }
  if (m === 'nequi' && !/^3\d{9}$/.test($('#nq').value)) { $('#nq').setAttribute('aria-invalid', true); $('#nq').focus(); return err('Escribe un celular válido de 10 dígitos.'); }
  return {};
}
async function submitCheckout(pay, extra = {}) {
  CK.error = '';
  // 1) crear el pedido una sola vez (si el pago falla, se reintenta sobre el mismo pedido)
  if (!CK.sale) {
    try {
      await bodega();
      CK.sale = await api('/sales', 'POST', {company_warehouse_id: S.wh, address: CK.address, description: CK.note || undefined,
        items: S.cart.map(i => ({product_id: i.id, quantity: i.qty}))});
      S.cart = []; S.note = ''; saveCart(); delete S.cache.allProducts; refreshOrder(); compraList();
    } catch (e) { CK.error = 'No se pudo crear el pedido: ' + e.message; return drawCheckout(); }
  }
  if (!pay) { CK.step = 3; return drawCheckout(); }
  // 2) registrar el pago por el total exacto del pedido
  try {
    const r = await api(`/sales/${CK.sale.sale_id}/payments`, 'POST', {method: CK.method, amount: CK.sale.total, ...extra});
    CK.sale = r; CK.payMethod = CK.method; CK.reference = (r.payments || []).slice(-1)[0]?.reference;
    CK.step = 3; drawCheckout();
    if (route().parts[0] === 'pedidos' || route().parts[1] === 'pedidos') render();
  } catch (e) {
    CK.error = `El pedido #${CK.sale.sale_id} quedó registrado, pero el pago no se completó: ${e.message}. Puedes reintentar o pagarlo luego desde “Mis pedidos”.`;
    CK.step = 2; drawCheckout();
  }
}
A.pay = run(async id => openPay(await api('/sales/' + id)));
A.cancel = run(async id => {
  if (!await confirmBox('Cancelar pedido', `¿Seguro que deseas cancelar el pedido #${id}? Los productos vuelven al inventario.`, 'Sí, cancelar', true)) return;
  await api(`/sales/${id}/cancel`, 'POST'); toast(`Pedido #${id} cancelado`, 'ok'); delete S.cache.allProducts; render();
});
A.invoice = run(async (id, btn) => {
  const doit = async () => {
    if (S.role === 'administrador') await api(`/sales/${id}/invoice`, 'POST').catch(e => { if (!/ya tiene/i.test(e.message)) throw e; });
    let inv;
    try { inv = await api(`/sales/${id}/invoice`); } catch (e) { throw new Error('La factura de este pedido aún no ha sido emitida.'); }
    const r = await fetch(`/api/invoices/${inv.invoice_id}/pdf`, {credentials: 'same-origin'});
    if (!r.ok) throw new Error('No se pudo descargar la factura');
    const a = document.createElement('a'); a.href = URL.createObjectURL(await r.blob()); a.download = inv.invoice_number + '.pdf'; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  };
  btn ? await busy(btn, doit) : await doit();
});
A.detail = run(async id => {
  const [s, prods] = await Promise.all([api('/sales/' + id), loadAll()]);
  const names = Object.fromEntries(prods.map(p => [p.product_id, p]));
  const order = ['Pendiente', 'Pagada', 'Despachada', 'Entregada'], idx = order.indexOf(s.state);
  openModal(`${mhead(`Pedido #${s.sale_id} ${badge(s.state)}`)}<div class="mbody">
    ${s.state === 'Cancelada' ? '<div class="notice bad">Este pedido fue cancelado.</div>' : `<div class="timeline">${order.map((o, k) => `<div class="${k <= idx ? 'on' : ''}">${o}</div>`).join('')}</div>`}
    <p class="small mut">${fmtDateTime(s.sale_date)} · ${esc(s.customer_name)}</p>
    <div class="tscroll"><table class="tbl"><thead><tr><th>Producto</th><th class="num">Cant.</th><th class="num">Subtotal</th></tr></thead><tbody>
      ${s.items.map(i => `<tr><td>${esc(names[i.product_id]?.name || 'Producto ' + i.product_id)}</td><td class="num">${i.quantity}</td><td class="num">${cop(i.subtotal)}</td></tr>`).join('')}</tbody></table></div>
    <div class="summary" style="margin-top:14px"><div><span class="mut">Subtotal</span><span>${cop(s.subtotal)}</span></div><div><span class="mut">IVA</span><span>${cop(s.tax)}</span></div>
      <div style="font-weight:800"><span>Total</span><span>${cop(s.total)}</span></div></div>
    ${s.description ? `<p style="margin-top:12px"><b>Descripción:</b> ${esc(s.description)}</p>` : ''}
    ${s.delivery ? `<p style="margin-top:12px">${I('truck', 16).replace('<svg', '<svg style="display:inline;vertical-align:-3px"')} <b>Entrega:</b> ${badge(s.delivery.status)} ${esc(s.delivery.address)}<br>
      <span class="mut small">Guía: ${esc(s.delivery.tracking_number || 'pendiente de asignación')}</span></p>` : ''}
    ${(s.payments || []).map(p => `<p class="small mut">Pago ${esc(METHOD_LABEL[p.method] || p.method)} · ${cop(p.amount)} · ${fmtDateTime(p.payment_date)} · ref. ${esc(p.reference)}</p>`).join('')}
    </div><div class="mfoot">${s.state === 'Pendiente' ? `<button class="btn" onclick="A.pay(${s.sale_id})">${I('lock', 16)} Pagar ${cop(s.total)}</button>` : ''}<button class="btn ghost" onclick="closeModal()">Cerrar</button></div>`, {wide: true});
});

/* ---------------- mis pedidos ---------------- */
async function pedidos() {
  $('#main').innerHTML = `<div class="wrap"><nav class="crumbs"><a href="#/">${t('home')}</a>›<span>${t('orders')}</span></nav>
    <h1 class="stitle" style="text-align:left">${S.role === 'administrador' ? 'Pedidos' : t('orders')}</h1><div class="olist" id="olist">${skeleton(2)}</div></div>`;
  const sales = await api('/sales');
  $('#olist').innerHTML = sales.map(s => `<article class="card ocard"><div>
      <div class="top"><b style="font-size:17px">Pedido #${s.sale_id}</b>${badge(s.state)}</div>
      <div class="mut small">${fmtDateTime(s.sale_date)}${S.role === 'administrador' ? ' · ' + esc(s.customer_name) : ''}</div>
      <div class="price" style="margin-top:4px">${cop(s.total)}</div></div>
    <div class="acts"><button class="btn ghost sm" onclick="A.detail(${s.sale_id})">Ver detalle</button>
      ${s.state === 'Pendiente' ? `<button class="btn sm" onclick="A.pay(${s.sale_id})">${I('lock', 14)} Pagar</button><button class="btn danger sm" onclick="A.cancel(${s.sale_id})">Cancelar</button>` : ''}
      ${s.invoice_id || (S.role === 'administrador' && ['Pagada', 'Despachada', 'Entregada'].includes(s.state)) ? `<button class="btn soft sm" onclick="A.invoice(${s.sale_id}, this)">${I('receipt', 14)} Factura PDF</button>`
        : ['Pagada', 'Despachada', 'Entregada'].includes(s.state) ? '<span class="mut small">Factura en proceso</span>' : ''}</div></article>`).join('')
    || `<div class="card empty">${I('receipt', 48)}<h3>Aún no tienes pedidos</h3><p>Cuando hagas una solicitud aparecerá aquí con su estado.</p><a class="btn" href="#/productos">Ir a la tienda</a></div>`;
}

/* ---------------- nosotros / contacto / 404 ---------------- */
async function nosotros() {
  $('#main').innerHTML = `<div class="wrap"><div class="about"><div><h1 class="stitle" style="text-align:left">Sobre nosotros</h1>
      <p style="font-size:17px">En <b>Universal de Repuestos WG</b> llevamos más de 15 años en el barrio 7 de Agosto de Bogotá ayudando a conductores, talleres y flotas a encontrar el repuesto exacto para su vehículo.</p>
      <p class="mut">Trabajamos con marcas reconocidas y proveedores aliados en todo el país, verificamos la compatibilidad por referencia y despachamos con número de guía y factura electrónica.</p>
      <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:16px"><a class="btn" href="#/productos">Ver productos</a><a class="btn ghost" href="#/contacto">Visítanos</a></div></div>
    <div class="card" style="overflow:hidden;background:var(--forest)"><div style="position:relative;height:300px">${ART.forest(2)}<div style="position:absolute;inset:auto 0 10px;display:flex;justify-content:center">${ART.car('#e9edf0', 420)}</div></div></div></div>
    <div class="values">${[['shield', 'Garantía real', 'Respaldamos cada repuesto: hasta 6 meses según el producto y el uso.'], ['wrench', 'Asesoría experta', 'Te ayudamos a identificar la referencia correcta con la placa o el VIN.'],
      ['truck', 'Despacho rápido', 'Entregas el mismo día en Bogotá y envíos nacionales con guía.'], ['receipt', 'Factura electrónica', 'Todas las compras incluyen factura con código QR.']]
      .map(([i, h, p]) => `<div class="card pad"><div class="kpi" style="padding:0"><div class="ic">${I(i, 22)}</div><b>${h}</b></div><p class="mut" style="margin-top:10px">${p}</p></div>`).join('')}</div></div>`;
}
async function contacto() {
  $('#main').innerHTML = `<div class="wrap"><h1 class="here">${I('pin', 34)} Aquí estamos</h1>
    <div class="map"><iframe title="Mapa: ${esc(COMPANY.address)}" loading="lazy" referrerpolicy="no-referrer-when-downgrade"
      src="https://maps.google.com/maps?q=${encodeURIComponent('Calle 63F #25-49, Bogotá, Colombia')}&z=16&output=embed"></iframe></div>
    <div class="info3">
      <div class="card"><div class="ic">${I('pin', 22)}</div><div><b>Dirección</b><p class="mut">${COMPANY.address}</p></div></div>
      <div class="card"><div class="ic">${I('phone', 22)}</div><div><b>Teléfonos</b><p class="mut"><a href="tel:+573104772730">${COMPANY.phone1}</a><br><a href="tel:+573212047803">${COMPANY.phone2}</a></p></div></div>
      <div class="card"><div class="ic">${I('clock', 22)}</div><div><b>Horario</b><p class="mut">Lunes a viernes 7:30 a. m. – 6:00 p. m.<br>Sábados 8:00 a. m. – 2:00 p. m.</p></div></div></div>
    <div class="card pad" style="max-width:720px;margin:0 auto"><h2>Escríbenos</h2><p class="mut">Te respondemos en horario laboral. El mensaje se abrirá en tu aplicación de correo.</p>
      <form class="form" id="cform"><div class="grid2"><label class="field"><span>Nombre</span><input class="input" name="n" required></label>
        <label class="field"><span>Teléfono</span><input class="input" name="p" inputmode="tel"></label></div>
        <label class="field"><span>Mensaje</span><textarea class="input" name="m" required placeholder="Vehículo, año y repuesto que buscas"></textarea></label>
        <button class="btn">${I('mail', 18)} Enviar mensaje</button></form></div></div>`;
  $('#cform').onsubmit = e => { e.preventDefault(); const d = formData(e.target);
    location.href = `mailto:${COMPANY.email}?subject=${encodeURIComponent('Consulta de ' + d.n)}&body=${encodeURIComponent(d.m + '\n\nTeléfono: ' + d.p)}`; };
}
async function notFound() { $('#main').innerHTML = `<div class="wrap empty"><h1>Página no encontrada</h1><a class="btn" href="#/">Volver al inicio</a></div>`; }

/* ================================================================ LOGIN / REGISTRO */
async function authView(mode, q) {
  const next = q.get('next') || '';
  const HOT = [[17, 68, 'Frenos'], [74, 68, 'Suspensión'], [88, 50, 'Iluminación'], [64, 36, 'Radiadores'], [8, 52, 'Escape']];
  $('#root').innerHTML = `<div class="auth"><a href="#/" class="logo" aria-label="Volver a la tienda">${ART.logo(40)}<span><b>Universal de</b><b>Repuestos <small>WG</small></b></span></a>
    <div class="panes"><section class="carpane" aria-label="Explora por sistema del vehículo">
      <span class="deco" style="width:120px;height:120px;top:-40px;right:-30px;opacity:.85"></span><span class="deco" style="width:46px;height:46px;bottom:36px;left:-14px"></span>
      <div><h2>Todo lo que tu carro necesita, en un solo lugar.</h2><p>Toca un punto rojo para explorar los repuestos de ese sistema.</p></div>
      <div class="stagecar">${ART.car('#e9edf0', 600)}
        ${HOT.map(([x, y, c]) => `<a class="hot" href="#/productos?catname=${encodeURIComponent(c)}" style="left:${x}%;top:${y}%" aria-label="Ver ${c}"><span>${c}</span></a>`).join('')}</div>
      <p class="small" style="margin:0">${I('shield', 16).replace('<svg', '<svg style="display:inline;vertical-align:-3px"')} Garantía y factura electrónica en todas las compras</p></section>
    <section class="loginpane" id="lp"></section></div></div>`;
  const lp = $('#lp');
  if (mode === 'login') {
    lp.innerHTML = `<h1>Iniciar sesión</h1><p class="mut">Ingresa para enviar solicitudes, pagar y seguir tus pedidos.</p>
      <form class="form" id="lf" novalidate><label class="field"><span>Usuario</span><input class="input" name="usuario" autocomplete="username" required autofocus autocapitalize="none"></label>
        <label class="field"><span>Contraseña</span><span class="pw"><input class="input" name="password" type="password" autocomplete="current-password" required>
          <button type="button" aria-label="Mostrar contraseña" id="eye">${I('eye', 18)}</button></span></label>
        <div class="field"><span>Código de verificación</span><div class="captcha"><span id="capimg" aria-live="polite"></span>
          <button type="button" class="btn ghost icon" id="capnew" aria-label="Generar otro código" title="Otro código">${I('sun', 18)}</button></div>
          <input class="input" name="captcha" autocomplete="off" required maxlength="5" placeholder="Código" aria-label="Escribe los 5 caracteres de la imagen" autocapitalize="characters">
          <input type="hidden" name="captcha_token"></div>
        <p class="err" id="lerr" role="alert"></p><button class="btn lg block">Entrar</button></form>
      <p class="alt">¿No tienes cuenta? <a href="#/registro${next ? '?next=' + encodeURIComponent(next) : ''}">Crea una cuenta de cliente</a></p>
      <p class="alt"><a href="#/" style="color:var(--mut);font-weight:500">← Volver a la tienda</a></p>
      <div class="demo"><b>Usuarios de prueba</b> (datos de ejemplo): <button data-u="admin">admin</button>,
        <button data-u="lhernandez">cliente</button>, <button data-u="pmartinez">empacador</button>,
        <button data-u="dmoreno">repartidor</button> · contraseña <code>Repuestos#2026</code></div>`;
    const captcha = async () => { try { const c = await api('/auth/captcha'); $('#capimg').innerHTML = c.svg; $('[name=captcha_token]').value = c.token; $('[name=captcha]').value = ''; } catch (e) { $('#lerr').textContent = e.message; } };
    $('#capnew').onclick = captcha; captcha();
    $('#eye').onclick = () => { const i = $('[name=password]'); i.type = i.type === 'password' ? 'text' : 'password'; };
    $$('.demo button').forEach(b => b.onclick = () => { $('[name=usuario]').value = b.dataset.u; $('[name=password]').value = 'Repuestos#2026'; $('[name=captcha]').focus(); });
    $('#lf').onsubmit = async e => {
      e.preventDefault(); const d = formData(e.target), btn = e.target.querySelector('.btn');
      if (!d.usuario || !d.password) return $('#lerr').textContent = 'Escribe tu usuario y contraseña.';
      if (!d.captcha) { $('[name=captcha]').focus(); return $('#lerr').textContent = 'Escribe el código de verificación.'; }
      await busy(btn, async () => {
        try {
          const r = await api('/auth/sesion', 'POST', d);
          setSession(r); S.cache = {};
          toast(`Bienvenido, ${r.username}`, 'ok');
          go(next ? '/' + next : STAFF.includes(r.role) ? '/admin' : '/');
        } catch (err) { $('#lerr').textContent = err.message; captcha(); }
      });
    };
  } else {
    lp.innerHTML = `<h1>Crear cuenta</h1><p class="mut">Regístrate como cliente para comprar y hacer seguimiento.</p><p class="mut small">Cargando…</p>`;
    const [dt, ct] = await Promise.all([api('/document-types?state=true'), api('/cities?state=true')]);
    lp.innerHTML = `<h1>Crear cuenta</h1><p class="mut">Regístrate como cliente para comprar y hacer seguimiento.</p>
      <form class="form" id="rf"><div class="grid2"><label class="field"><span>Nombre *</span><input class="input" name="first_name" required autocomplete="given-name"></label>
        <label class="field"><span>Apellido *</span><input class="input" name="last_name" required autocomplete="family-name"></label></div>
        <div class="grid2"><label class="field"><span>Tipo de documento *</span><select class="input" name="document_type_id">${dt.map(d => `<option value="${d.document_type_id}">${esc(d.acronym)} — ${esc(d.name)}</option>`).join('')}</select></label>
        <label class="field"><span>Número de documento *</span><input class="input" name="identification" required inputmode="numeric"></label></div>
        <div class="grid2"><label class="field"><span>Correo *</span><input class="input" name="email" type="email" required autocomplete="email"></label>
        <label class="field"><span>Teléfono</span><input class="input" name="phone_number" inputmode="tel" autocomplete="tel"></label></div>
        <div class="grid2"><label class="field"><span>Ciudad *</span><select class="input" name="city_id">${ct.map(c => `<option value="${c.city_id}">${esc(c.name)}</option>`).join('')}</select></label>
        <label class="field"><span>Usuario *</span><input class="input" name="username" required autocomplete="username" pattern="[a-z0-9._-]{3,40}" title="3 a 40 caracteres en minúscula: letras, números, punto, guion o guion bajo" autocapitalize="none"></label></div>
        <label class="field"><span>Contraseña *</span><input class="input" name="password" type="password" minlength="10" required autocomplete="new-password">
          <small class="mut">Mínimo 10 caracteres con mayúscula, minúscula, número y símbolo; no debe contener tu usuario.</small></label>
        <p class="err" id="rerr" role="alert"></p><button class="btn lg block">Registrarme</button></form>
      <p class="alt">¿Ya tienes cuenta? <a href="#/login${next ? '?next=' + encodeURIComponent(next) : ''}">Inicia sesión</a></p>`;
    $('#rf').onsubmit = async e => {
      e.preventDefault(); const d = formData(e.target);
      await busy(e.target.querySelector('.btn'), async () => {
        try { d.username = (d.username || '').trim().toLowerCase(); await api('/clientes', 'POST', d); toast('Cuenta creada. Ya puedes iniciar sesión.', 'ok'); go('/login' + (next ? '?next=' + encodeURIComponent(next) : '')); }
        catch (err) { $('#rerr').textContent = err.message; }
      });
    };
  }
}

/* ================================================================ PANEL ADMINISTRATIVO */
const ADM = {
  administrador: [['resumen', 'Resumen', 'chart'], ['pedidos', 'Pedidos', 'receipt'], ['entregas', 'Entregas', 'truck'], ['inventario', 'Inventario', 'layers'], ['productos', 'Productos', 'tag'], ['reportes', 'Reportes', 'receipt'], ['usuarios', 'Usuarios', 'users'], ['auditoria', 'Auditoría', 'shield']],
  empacador: [['entregas', 'Despachos', 'box'], ['inventario', 'Inventario', 'layers']],
  repartidor: [['entregas', 'Mis entregas', 'truck']],
};
async function adminShell(section, q) {
  const items = ADM[S.role]; const cur = items.find(i => i[0] === section) ? section : items[0][0];
  const title = items.find(i => i[0] === cur)[1];
  $('#root').innerHTML = `<div class="adm"><aside class="side" id="side"><a href="#/" class="logo">${ART.logo(36)}<span><b>Universal de</b><b>Repuestos <small>WG</small></b></span></a>
    <nav aria-label="Panel"><div class="grp">${S.role === 'administrador' ? 'Administración' : 'Operación'}</div>
      ${items.map(([k, l, ic]) => `<a href="#/admin/${k}" class="${k === cur ? 'on' : ''}" ${k === cur ? 'aria-current="page"' : ''}>${I(ic)} ${l}<span class="cnt" data-cnt="${k}" hidden></span></a>`).join('')}
      <div class="grp">Tienda</div><a href="#/">${I('store')} Ver tienda</a>${S.role === 'administrador' ? `<a href="#/pedidos">${I('receipt')} Vista de pedidos</a>` : ''}</nav>
    <div class="me"><span class="avatar">${esc(S.name.slice(0, 1).toUpperCase())}</span><div style="flex:1;min-width:0"><b>${esc(S.name)}</b><div style="color:#86a990;text-transform:capitalize">${esc(S.role)}</div></div>
      <button class="btn icon" style="background:rgba(255,255,255,.08)" onclick="logout()" aria-label="Cerrar sesión" title="Cerrar sesión">${I('logout', 18)}</button></div></aside>
    <div class="amain"><header class="atop"><button class="btn ghost icon sidebtn" onclick="$('#side').classList.toggle('open')" aria-label="Menú">${I('menu')}</button>
      <h1>${title}</h1><select class="input" style="width:auto;min-height:36px" aria-label="Tema" onchange="S.theme=this.value;store.set('theme',S.theme);document.documentElement.dataset.theme=S.theme">
        <option value="light" ${S.theme === 'light' ? 'selected' : ''}>Tema claro</option><option value="dark" ${S.theme === 'dark' ? 'selected' : ''}>Tema oscuro</option></select></header>
    <main class="acontent" id="main" tabindex="-1"><div class="skel" style="height:120px"></div><div class="skel"></div></main></div></div>`;
  await ({resumen: aResumen, pedidos: aPedidos, entregas: aEntregas, inventario: aInventario, productos: aProductos, reportes: aReportes, usuarios: aUsuarios, auditoria: aAuditoria}[cur])(q);
  badgeCounts();
}
async function badgeCounts() {
  try {
    if (S.role === 'administrador') { const s = await api('/sales?state=Pendiente'); setCnt('pedidos', s.length); }
    if (S.role !== 'repartidor') { const d = await api('/deliveries?status=pendiente'); setCnt('entregas', d.length); }
    else { const d = await api('/deliveries/assigned'); setCnt('entregas', d.filter(x => x.status !== 'entregado').length); }
  } catch (e) { /* opcional */ }
}
function setCnt(k, n) { const e = $(`[data-cnt="${k}"]`); if (e) { e.textContent = n; e.hidden = !n; } }

/* tabla genérica con búsqueda, filtros y paginación */
function dataTable({el, rows, cols, search, filters = '', empty = 'Sin registros', size = 10, onDraw}) {
  let page = 0, term = '';
  el.innerHTML = `<div class="chead"><div class="toolbar">${search ? `<label class="tsearch"><span class="sr">Buscar</span>${I('search', 16)}<input class="input" placeholder="${esc(search)}" data-s></label>` : ''}${filters}</div>
    <span class="mut small" data-c aria-live="polite"></span></div><div class="tscroll"><table class="tbl"><thead><tr>${cols.map(c => `<th class="${c.cls || ''}">${c.h}</th>`).join('')}</tr></thead><tbody data-b></tbody></table></div>
    <div class="pager"><span data-p></span><div><button class="btn ghost sm" data-prev>Anterior</button><button class="btn ghost sm" data-next>Siguiente</button></div></div>`;
  const draw = () => {
    const list = (typeof rows === 'function' ? rows() : rows).filter(r => !term || JSON.stringify(Object.values(r)).toLowerCase().includes(term));
    const pages = Math.max(1, Math.ceil(list.length / size)); page = Math.min(page, pages - 1);
    const view = list.slice(page * size, page * size + size);
    $('[data-b]', el).innerHTML = view.map(r => `<tr>${cols.map(c => `<td class="${c.cls || ''}">${c.v(r)}</td>`).join('')}</tr>`).join('')
      || `<tr><td colspan="${cols.length}"><div class="empty">${esc(empty)}</div></td></tr>`;
    $('[data-c]', el).textContent = `${list.length} registro${list.length === 1 ? '' : 's'}`;
    $('[data-p]', el).textContent = `Página ${page + 1} de ${pages}`;
    $('[data-prev]', el).disabled = page === 0; $('[data-next]', el).disabled = page >= pages - 1;
    onDraw && onDraw();
  };
  if (search) $('[data-s]', el).oninput = e => { term = e.target.value.toLowerCase().trim(); page = 0; draw(); };
  $('[data-prev]', el).onclick = () => { page--; draw(); }; $('[data-next]', el).onclick = () => { page++; draw(); };
  draw();
  return {draw: () => { draw(); }};
}

/* ---- resumen ---- */
async function aResumen() {
  const [r, low, prods, sales] = await Promise.all([api('/reports/summary'), api('/inventory?low=1'), api('/products'), api('/sales')]);
  const names = Object.fromEntries(prods.map(p => [p.product_id, p.name]));
  const months = r.monthly || [], max = Math.max(1, ...months.map(m => m.total));
  const nice = (() => { const p = Math.pow(10, Math.floor(Math.log10(max))); return Math.ceil(max / p) * p; })();
  const mname = s => new Date(s + '-15').toLocaleDateString('es-CO', {month: 'short', year: '2-digit'});
  const short = n => n >= 1e6 ? (n / 1e6).toFixed(1).replace('.0', '') + ' M' : n >= 1e3 ? Math.round(n / 1e3) + ' mil' : n;
  const st = Object.fromEntries((r.by_state || []).map(x => [x.state, x]));
  $('#main').innerHTML = `<div class="kpis">
      ${[['receipt', 'Ventas registradas', r.sales_count, ''], ['chart', 'Total vendido (con IVA)', cop(r.sales_total), ''], ['check', 'Facturas emitidas', r.invoices_issued, ''], ['alert', 'Productos por reponer', r.low_stock_items, 'warn']]
        .map(([ic, k, v, c]) => `<div class="card kpi"><div class="ic ${c}">${I(ic, 22)}</div><div><div class="v">${v}</div><div class="k">${k}</div></div></div>`).join('')}</div>
    <div class="cols2"><section class="card" aria-labelledby="ch1"><div class="chead"><h2 id="ch1">Ventas por mes (últimos 6 meses)</h2><span class="mut small">Excluye canceladas</span></div>
        ${months.length ? `<div class="chart" role="list">${[1, .5].map(f => `<div class="gl" style="bottom:${f * 200}px"><span>${short(nice * f)}</span></div>`).join('')}
          ${months.map(m => `<div class="col" role="listitem" tabindex="0" aria-label="${mname(m.month)}: ${cop(m.total)} en ${m.count} ventas">
            <div class="tip">${mname(m.month)} · ${cop(m.total)} · ${m.count} ventas</div><div class="bar" style="height:${Math.max(2, m.total / nice * 200)}px"></div></div>`).join('')}</div>
          <div class="chart-x">${months.map(m => `<span>${mname(m.month)}</span>`).join('')}</div>` : '<div class="empty">Sin ventas aún</div>'}</section>
      <section class="card"><div class="chead"><h2>Pedidos por estado</h2><a class="btn ghost sm" href="#/admin/pedidos">Ver pedidos</a></div><div class="slist">
        ${['Pendiente', 'Pagada', 'Despachada', 'Entregada', 'Cancelada'].map(n => `<div>${badge(n)}<span><b>${st[n]?.count || 0}</b> <span class="mut small">· ${cop(st[n]?.total || 0)}</span></span></div>`).join('')}</div></section></div>
    <div class="cols2"><section class="card"><div class="chead"><h2>Pedidos recientes</h2></div><div class="tscroll"><table class="tbl"><thead><tr><th>#</th><th>Cliente</th><th>Fecha</th><th>Estado</th><th class="num">Total</th></tr></thead><tbody>
        ${sales.slice(0, 6).map(s => `<tr><td><a href="#" onclick="event.preventDefault();A.detail(${s.sale_id})"><b>#${s.sale_id}</b></a></td><td>${esc(s.customer_name)}</td><td>${fmtDate(s.sale_date)}</td><td>${badge(s.state)}</td><td class="num">${cop(s.total)}</td></tr>`).join('')}</tbody></table></div></section>
      <section class="card"><div class="chead"><h2>Más vendidos</h2></div><div class="slist">${(r.top_products || []).map((p, i) => `<div><span><b>${i + 1}.</b> ${esc(p.name)}</span><span class="mut small">${p.quantity} und.</span></div>`).join('') || '<p class="empty">—</p>'}</div>
        <div class="chead" style="border-top:1px solid var(--line-2)"><h2>Stock bajo</h2><a class="btn ghost sm" href="#/admin/inventario?low=1">Gestionar</a></div>
        <div class="slist">${low.slice(0, 5).map(i => `<div><span>${esc(names[i.product_id] || i.product_id)}</span><span class="badge ${i.quantity_available ? 'warn' : 'bad'}">${i.quantity_available} und.</span></div>`).join('') || '<p class="mut" style="padding:10px">Todo el inventario está sobre el punto de reorden.</p>'}</div></section></div>`;
}

/* ---- pedidos ---- */
async function aPedidos(q) {
  const sales = await api('/sales');
  $('#main').innerHTML = '<section class="card" id="tb"></section>';
  let st = q.get('estado') || '';
  const filters = `<select class="input" data-f aria-label="Filtrar por estado"><option value="">Todos los estados</option>${['Pendiente', 'Pagada', 'Despachada', 'Entregada', 'Cancelada'].map(s => `<option ${s === st ? 'selected' : ''}>${s}</option>`).join('')}</select>`;
  const tb = dataTable({el: $('#tb'), search: 'Buscar por # o cliente', filters, empty: 'No hay pedidos con ese filtro',
    rows: () => sales.filter(s => !st || s.state === st).map(s => ({...s, _k: `#${s.sale_id} ${s.customer_name}`})),
    cols: [{h: 'Pedido', v: s => `<b>#${s.sale_id}</b>`}, {h: 'Fecha', v: s => fmtDate(s.sale_date)}, {h: 'Cliente', v: s => esc(s.customer_name)},
      {h: 'Estado', v: s => badge(s.state)}, {h: 'Total', cls: 'num', v: s => cop(s.total)},
      {h: '<span class="sr">Acciones</span>', cls: 'num', v: s => `<div class="acts"><button class="btn ghost sm" onclick="A.detail(${s.sale_id})">Detalle</button>
        ${s.state === 'Pendiente' ? `<button class="btn sm" onclick="A.pay(${s.sale_id})">Registrar pago</button><button class="btn danger sm" onclick="A.cancel(${s.sale_id})">Cancelar</button>` : ''}
        ${['Pagada', 'Despachada', 'Entregada'].includes(s.state) ? `<button class="btn soft sm" onclick="A.invoice(${s.sale_id}, this)">${s.invoice_id ? 'Factura' : 'Emitir factura'}</button>` : ''}</div>`}]});
  $('[data-f]').onchange = e => { st = e.target.value; tb.draw(); };
}

/* ---- entregas ---- */
async function aEntregas() {
  const r = S.role, list = await api(r === 'repartidor' ? '/deliveries/assigned' : '/deliveries');
  const PRI = {pendiente: 0, empacado: 1, en_camino: 2, entregado: 3, cancelado: 4};
  list.sort((a, b) => (PRI[a.status] ?? 9) - (PRI[b.status] ?? 9) || b.delivery_id - a.delivery_id);
  const reps = r === 'administrador' ? (await api('/usuarios?role=repartidor')).filter(u => u.status) : [];
  const repName = Object.fromEntries(reps.map(u => [u.user_id, u.username]));
  let st = r === 'empacador' ? 'pendiente' : '';
  const act = d => {
    if (r !== 'repartidor' && d.status === 'pendiente') return `<button class="btn sm" onclick="A.prepare(${d.delivery_id}, this)">${I('box', 14)} Preparar despacho</button>`;
    if (r === 'administrador' && ['empacado', 'en_camino'].includes(d.status)) return `<label class="sr" for="r${d.delivery_id}">Repartidor</label><select class="input" id="r${d.delivery_id}" style="width:auto;min-height:32px">
        <option value="">Repartidor…</option>${reps.map(u => `<option value="${u.user_id}" ${u.user_id === d.assigned_user_id ? 'selected' : ''}>${esc(u.username)}</option>`).join('')}</select>
      <button class="btn ghost sm" onclick="A.assign(${d.delivery_id})">Asignar</button>`;
    if (r === 'repartidor' && d.status === 'empacado') return `<button class="btn sm" onclick="A.status(${d.delivery_id},'en_camino')">${I('truck', 14)} Salir a entregar</button>`;
    if (r === 'repartidor' && d.status === 'en_camino') return `<button class="btn sm" onclick="A.status(${d.delivery_id},'entregado')">${I('check', 14)} Marcar entregado</button>`;
    return '<span class="mut small">—</span>';
  };
  const opts = ['pendiente', 'empacado', 'en_camino', 'entregado', 'cancelado'];
  $('#main').innerHTML = `<div class="chips" role="group" aria-label="Filtrar por estado">${['', ...opts].map(o => `<button class="chip out ${o === st ? 'on' : ''}" data-st="${o}">${o ? DLV[o] + ' (' + list.filter(d => d.status === o).length + ')' : 'Todas (' + list.length + ')'}</button>`).join('')}</div>
    <section class="card" id="tb"></section>`;
  const tb = dataTable({el: $('#tb'), search: 'Buscar dirección, guía o venta', empty: r === 'repartidor' ? 'No tienes entregas asignadas' : 'No hay entregas en este estado',
    rows: () => list.filter(d => !st || d.status === st),
    cols: [{h: '#', v: d => d.delivery_id}, {h: 'Venta', v: d => `<a href="#" onclick="event.preventDefault();A.detail(${d.sale_id})">#${d.sale_id}</a>`},
      {h: 'Dirección', v: d => esc(d.address)}, {h: 'Estado', v: d => badge(d.status)}, {h: 'Guía', v: d => `<code>${esc(d.tracking_number || '—')}</code>`},
      ...(r === 'administrador' ? [{h: 'Repartidor', v: d => esc(repName[d.assigned_user_id] || '—')}] : []),
      {h: '<span class="sr">Acciones</span>', cls: 'num', v: d => `<div class="acts">${act(d)}</div>`}]});
  $$('[data-st]').forEach(b => b.onclick = () => { st = b.dataset.st; $$('[data-st]').forEach(x => x.classList.toggle('on', x === b)); tb.draw(); });
}
A.prepare = run(async (id, btn) => busy(btn, async () => { const d = await api(`/deliveries/${id}/prepare`, 'POST'); toast(`Despacho preparado · guía ${d.tracking_number}`, 'ok'); render(); }));
A.assign = run(async id => { const v = $('#r' + id).value; if (!v) return toast('Selecciona un repartidor', 'bad'); await api(`/deliveries/${id}/assign`, 'POST', {user_id: +v}); toast('Repartidor asignado', 'ok'); render(); });
A.status = run(async (id, status) => {
  if (status === 'entregado' && !await confirmBox('Confirmar entrega', `¿El cliente recibió la entrega #${id}?`, 'Sí, entregado')) return;
  await api(`/deliveries/${id}/status`, 'PATCH', {status}); toast('Estado actualizado', 'ok'); render();
});

/* ---- inventario ---- */
async function aInventario(q) {
  const [inv, prods, whs] = await Promise.all([api('/inventory'), api('/products'), api('/warehouses')]);
  const pn = Object.fromEntries(prods.map(p => [p.product_id, p])), wn = Object.fromEntries(whs.map(w => [w.company_warehouse_id, w.name]));
  const edit = S.role === 'administrador';
  let low = q.get('low') === '1';
  $('#main').innerHTML = '<section class="card" id="tb"></section>';
  const tb = dataTable({el: $('#tb'), search: 'Buscar producto o bodega', filters: `<label class="chip out ${low ? 'on' : ''}" style="cursor:pointer"><input type="checkbox" data-low ${low ? 'checked' : ''} style="accent-color:var(--g)"> Solo stock bajo</label>`,
    rows: () => inv.filter(i => !low || i.needs_reorder).map(i => ({...i, _n: pn[i.product_id]?.name, _w: wn[i.company_warehouse_id]})),
    cols: [{h: 'Producto', v: i => `<b>${esc(i._n || i.product_id)}</b><div class="mut small">${esc(pn[i.product_id]?.category || '')}</div>`},
      {h: 'Bodega', v: i => esc(i._w || i.company_warehouse_id)},
      {h: 'Nivel', v: i => `<div class="stockbar" title="${i.quantity_available} de ${i.maximum_stock || '—'}"><i class="${i.needs_reorder ? 'low' : ''}" style="width:${Math.min(100, i.quantity_available / Math.max(1, i.maximum_stock || 100) * 100)}%"></i></div>`},
      {h: 'Disponible', v: i => edit ? `<label class="sr" for="q${i.inventory_id}">Cantidad</label><input class="input" id="q${i.inventory_id}" type="number" min="0" value="${i.quantity_available}" style="width:96px;min-height:34px">` : `<b>${i.quantity_available}</b>`},
      {h: 'Reorden', v: i => `${i.reorder_stock} ${i.needs_reorder ? `<span class="badge ${i.quantity_available ? 'warn' : 'bad'}">${i.quantity_available ? 'Reponer' : 'Agotado'}</span>` : ''}`},
      ...(edit ? [{h: '<span class="sr">Acciones</span>', cls: 'num', v: i => `<button class="btn ghost sm" onclick="A.saveInv(${i.inventory_id}, this)">Guardar</button>`}] : [])]});
  $('[data-low]').onchange = e => { low = e.target.checked; e.target.parentElement.classList.toggle('on', low); tb.draw(); };
  A._inv = inv;
}
A.saveInv = run(async (id, btn) => busy(btn, async () => {
  const v = +$('#q' + id).value; if (!(v >= 0)) throw new Error('La cantidad debe ser 0 o mayor');
  const r = await api('/inventory/' + id, 'PUT', {quantity_available: v});
  const it = (A._inv || []).find(i => i.inventory_id === id); if (it) Object.assign(it, r, {needs_reorder: r.quantity_available <= r.reorder_stock});
  delete S.cache.allProducts; toast('Inventario actualizado', 'ok');
}));

/* ---- productos ---- */
async function aProductos() {
  const [prods, cats, cars] = await Promise.all([api('/products'), loadCats(), loadCars()]);
  $('#main').innerHTML = '<section class="card" id="tb"></section>';
  dataTable({el: $('#tb'), search: 'Buscar producto o categoría', filters: `<button class="btn sm" onclick="A.prodForm()">${I('plus', 16)} Nuevo producto</button>`,
    rows: prods.map(p => ({...p, _c: p.category})),
    cols: [{h: 'Producto', v: p => `<div style="display:flex;gap:12px;align-items:center"><span style="width:44px;height:44px;border-radius:10px;background:var(--line-2);display:grid;place-items:center;flex-shrink:0">${ART.part(p.category, 34)}</span>
        <div><b>${esc(p.name)}</b><div class="mut small">${(p.fk_car_product || []).length} vehículos compatibles</div></div></div>`},
      {h: 'Categoría', v: p => p.category ? `<span class="badge">${esc(p.category)}</span>` : '<span class="mut">Sin categoría</span>'},
      {h: 'Precio (sin IVA)', cls: 'num', v: p => cop(p.unit_price)},
      {h: 'Stock', cls: 'num', v: p => p.stock_total < 1 ? '<span class="badge bad">0</span>' : p.stock_total <= 8 ? `<span class="badge warn">${p.stock_total}</span>` : p.stock_total},
      {h: '<span class="sr">Acciones</span>', cls: 'num', v: p => `<div class="acts"><button class="btn ghost sm" onclick="A.prodForm(${p.product_id})">Editar</button><button class="btn danger sm" onclick="A.delProd(${p.product_id})">Desactivar</button></div>`}]});
  A._prods = prods; A._cats = cats; A._cars = cars;
}
A.prodForm = run(async id => {
  const p = id ? A._prods.find(x => x.product_id === id) : null;
  const pbrands = await cached('pbrands', () => api('/spare-part-brands?state=true'));
  const sel = new Set(p ? p.fk_car_product : []);
  openModal(`${mhead(p ? 'Editar producto' : 'Nuevo producto')}<form id="pf"><div class="mbody form">
    <label class="field"><span>Nombre *</span><input class="input" name="name" required maxlength="150" value="${esc(p?.name || '')}"></label>
    <label class="field"><span>Descripción</span><textarea class="input" name="description" maxlength="255">${esc(p?.description || '')}</textarea></label>
    <div class="grid2"><label class="field"><span>Precio sin IVA (COP) *</span><input class="input" name="unit_price" type="number" min="0" step="100" required value="${p ? p.unit_price : ''}"></label>
      ${p ? '' : '<label class="field"><span>Stock inicial (bodega principal)</span><input class="input" name="stock" type="number" min="0" value="10"></label>'}</div>
    <div class="grid2"><label class="field"><span>Categoría *</span><select class="input" name="cat" required><option value="">Selecciona…</option>${A._cats.map(c => `<option value="${c.spare_part_type_id}" ${p?.category_id === c.spare_part_type_id ? 'selected' : ''}>${esc(c.name)}</option>`).join('')}</select></label>
      <label class="field"><span>Marca del repuesto</span><select class="input" name="pbrand">${pbrands.map(b => `<option value="${b.spare_part_brand_id}" ${p?.part_brand === b.name ? 'selected' : ''}>${esc(b.name)}</option>`).join('')}</select></label></div>
    <div class="field"><span>Vehículos compatibles</span><input class="input" placeholder="Filtrar vehículos…" id="cf" style="min-height:36px">
      <div class="checks" id="cl">${A._cars.map(c => `<label data-n="${esc(carLabel(c).toLowerCase())}"><input type="checkbox" name="cars" value="${c.car_id}" ${sel.has(c.car_id) ? 'checked' : ''}>${esc(carLabel(c))}</label>`).join('')}</div></div>
    <p class="err" id="perr" role="alert"></p></div>
    <div class="mfoot"><button type="button" class="btn ghost" onclick="closeModal()">Cancelar</button><button class="btn">${p ? 'Guardar cambios' : 'Crear producto'}</button></div></form>`, {wide: true});
  $('#cf').oninput = e => { const v = e.target.value.toLowerCase(); $$('#cl label').forEach(l => l.hidden = !l.dataset.n.includes(v)); };
  $('#pf').onsubmit = async e => {
    e.preventDefault(); const f = e.target, d = formData(f);
    const cars = $$('input[name=cars]:checked', f).map(i => +i.value);
    await busy(f.querySelector('.mfoot .btn:last-child'), async () => {
      try {
        const body = {name: d.name.trim(), description: d.description.trim(), unit_price: +d.unit_price, fk_car_product: cars};
        let prod = p ? await api('/products/' + p.product_id, 'PUT', body) : await api('/products', 'POST', body);
        const part = {product_id: prod.product_id, name: body.name, spare_part_type_id: +d.cat, spare_part_brand_id: +d.pbrand};
        if (prod.fk_spare_part) await api('/spare-parts/' + prod.fk_spare_part, 'PUT', part);
        else { const sp = await api('/spare-parts', 'POST', part); prod = await api('/products/' + prod.product_id, 'PUT', {fk_spare_part: sp.spare_part_id}); }
        if (!p && +d.stock > 0) {
          await bodega();
          await api('/inventory', 'POST', {product_id: prod.product_id, company_warehouse_id: S.wh, quantity_available: +d.stock, minimum_stock: 3, maximum_stock: 120, reorder_stock: 5});
        }
        delete S.cache.allProducts; closeModal(); toast(p ? 'Producto actualizado' : 'Producto creado', 'ok'); render();
      } catch (err) { $('#perr').textContent = err.message; }
    });
  };
});
A.delProd = run(async id => {
  const p = A._prods.find(x => x.product_id === id);
  if (!await confirmBox('Desactivar producto', `“${p.name}” dejará de mostrarse en la tienda. El historial de ventas se conserva.`, 'Desactivar', true)) return;
  await api('/products/' + id, 'DELETE'); delete S.cache.allProducts; toast('Producto desactivado', 'ok'); render();
});

/* ---- usuarios ---- */
async function aUsuarios() {
  const us = await api('/usuarios');
  let role = '';
  const filters = `<select class="input" data-f aria-label="Filtrar por rol"><option value="">Todos los roles</option>${['cliente', 'administrador', 'empacador', 'repartidor'].map(r => `<option value="${r}">${r[0].toUpperCase() + r.slice(1)}</option>`).join('')}</select>
    <button class="btn sm" onclick="A.userForm()">${I('plus', 16)} Nuevo usuario interno</button>`;
  $('#main').innerHTML = '<section class="card" id="tb"></section>';
  const RC = {administrador: 'info', empacador: 'warn', repartidor: 'ok', cliente: ''};
  const tb = dataTable({el: $('#tb'), search: 'Buscar usuario, nombre o correo', filters,
    rows: () => us.filter(u => !role || u.role === role),
    cols: [{h: 'Usuario', v: u => `<div style="display:flex;gap:10px;align-items:center"><span class="avatar" style="width:32px;height:32px;font-size:13px">${esc(u.username[0].toUpperCase())}</span><div><b>${esc(u.username)}</b><div class="mut small">${esc(u.nombre_completo || '')}</div></div></div>`},
      {h: 'Correo', v: u => esc(u.email)}, {h: 'Rol', v: u => `<span class="badge ${RC[u.role]}">${esc(u.role)}</span>`},
      {h: 'Estado', v: u => u.status ? '<span class="badge ok">Activo</span>' : '<span class="badge bad">Inactivo</span>'},
      {h: 'Último acceso', v: u => u.ultimo_acceso ? fmtDateTime(u.ultimo_acceso) : '<span class="mut">Nunca</span>'},
      {h: 'Sesiones', cls: 'num', v: u => u.sesiones_activas},
      {h: '<span class="sr">Acciones</span>', cls: 'num', v: u => `<div class="acts"><button class="btn ghost sm" onclick="A.userEdit(${u.user_id})">Editar</button>
        ${u.sesiones_activas ? `<button class="btn danger sm" onclick="A.userKill(${u.user_id})">Cerrar sesiones</button>` : ''}</div>`}]});
  $('[data-f]').onchange = e => { role = e.target.value; tb.draw(); };
  A._users = us;
}
A.userEdit = run(async id => {
  const u = A._users.find(x => x.user_id === id);
  openModal(`${mhead('Editar usuario ' + esc(u.username))}<form id="ue"><div class="mbody form">
    <div class="grid2"><label class="field"><span>Rol</span><select class="input" name="role">${['cliente', 'administrador', 'empacador', 'repartidor'].map(r => `<option ${r === u.role ? 'selected' : ''}>${r}</option>`).join('')}</select></label>
      <label class="field"><span>Estado</span><select class="input" name="status"><option value="1" ${u.status ? 'selected' : ''}>Activo</option><option value="" ${u.status ? '' : 'selected'}>Inactivo</option></select></label></div>
    <label class="field"><span>Nueva contraseña (opcional)</span><input class="input" name="password" type="password" autocomplete="new-password" placeholder="Déjala vacía para no cambiarla"></label>
    <div class="notice">Cambiar el rol, desactivar la cuenta o cambiar la contraseña cierra todas las sesiones abiertas del usuario.</div>
    <p class="err" id="ueerr" role="alert"></p></div>
    <div class="mfoot"><button type="button" class="btn ghost" onclick="closeModal()">Cancelar</button><button class="btn">Guardar</button></div></form>`);
  $('#ue').onsubmit = async e => {
    e.preventDefault(); const d = formData(e.target);
    await busy(e.target.querySelector('.mfoot .btn:last-child'), async () => {
      try { await api('/usuarios/' + id, 'PUT', {role: d.role, status: !!d.status, ...(d.password && {password: d.password})}); closeModal(); toast('Usuario actualizado', 'ok'); render(); }
      catch (err) { $('#ueerr').textContent = err.message; }
    });
  };
});
A.userKill = run(async id => {
  const u = A._users.find(x => x.user_id === id);
  if (!await confirmBox('Cerrar sesiones', `Se cerrarán las ${u.sesiones_activas} sesión(es) activa(s) de ${u.username}.`, 'Cerrar sesiones', true)) return;
  const r = await api(`/usuarios/${id}/cerrar-sesiones`, 'POST'); toast(`Se cerraron ${r.sesiones} sesión(es)`, 'ok'); render();
});
A.userForm = run(async () => {
  const [dt, ct] = await Promise.all([api('/document-types?state=true'), api('/cities?state=true')]);
  openModal(`${mhead('Nuevo usuario interno')}<form id="uf"><div class="mbody form">
    <div class="grid2"><label class="field"><span>Nombre *</span><input class="input" name="first_name" required></label><label class="field"><span>Apellido *</span><input class="input" name="last_name" required></label></div>
    <div class="grid2"><label class="field"><span>Tipo de documento</span><select class="input" name="document_type_id">${dt.map(d => `<option value="${d.document_type_id}">${esc(d.acronym)} — ${esc(d.name)}</option>`).join('')}</select></label>
      <label class="field"><span>Documento *</span><input class="input" name="identification" required></label></div>
    <div class="grid2"><label class="field"><span>Correo *</span><input class="input" name="email" type="email" required></label>
      <label class="field"><span>Ciudad</span><select class="input" name="city_id">${ct.map(c => `<option value="${c.city_id}">${esc(c.name)}</option>`).join('')}</select></label></div>
    <div class="grid2"><label class="field"><span>Usuario *</span><input class="input" name="username" required pattern="[a-z0-9._-]{3,40}" autocapitalize="none"></label>
      <label class="field"><span>Rol *</span><select class="input" name="role"><option value="empacador">Empacador</option><option value="repartidor">Repartidor</option><option value="administrador">Administrador</option></select></label></div>
    <label class="field"><span>Contraseña *</span><input class="input" name="password" type="password" minlength="10" required autocomplete="new-password">
      <small class="mut">Mínimo 10 caracteres con mayúscula, minúscula, número y símbolo; no debe contener el usuario.</small></label>
    <p class="err" id="uerr" role="alert"></p></div>
    <div class="mfoot"><button type="button" class="btn ghost" onclick="closeModal()">Cancelar</button><button class="btn">Crear usuario</button></div></form>`, {wide: true});
  $('#uf').onsubmit = async e => {
    e.preventDefault();
    await busy(e.target.querySelector('.mfoot .btn:last-child'), async () => {
      try { await api('/usuarios', 'POST', formData(e.target)); closeModal(); toast('Usuario creado', 'ok'); render(); }
      catch (err) { $('#uerr').textContent = err.message; }
    });
  };
});

/* ---- reportes (Informe -> JSON / PDF) ---- */
async function aReportes(q) {
  const lista = await api('/reportes');
  const cur = lista.find(r => r.slug === q.get('r')) || lista[0];
  const campo = p => {
    const v = q.get(p.nombre) ?? p.por_defecto ?? '';
    if (p.tipo === 'select') return `<label class="field"><span>${esc(p.etiqueta)}</span><select class="input" name="${p.nombre}">${p.opciones.map(([k, l]) => `<option value="${esc(k)}" ${String(k) === String(v) ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select></label>`;
    const tipo = p.tipo === 'fecha' ? 'date' : p.tipo === 'entero' ? 'number' : 'text';
    return `<label class="field"><span>${esc(p.etiqueta)}</span><input class="input" type="${tipo}" name="${p.nombre}" value="${esc(v)}" ${p.minimo != null ? `min="${p.minimo}"` : ''} ${p.maximo != null ? `max="${p.maximo}"` : ''}></label>`;
  };
  $('#main').innerHTML = `<div class="chips" role="tablist" aria-label="Reportes">${lista.map(r => `<a role="tab" class="chip out ${r.slug === cur.slug ? 'on' : ''}" href="#/admin/reportes?r=${r.slug}" aria-selected="${r.slug === cur.slug}">${esc(r.titulo.replace('Reporte de ', ''))}</a>`).join('')}</div>
    <section class="card pad"><h2 style="font-size:18px">${esc(cur.titulo)}</h2><p class="mut">${esc(cur.descripcion)}</p>
      <form id="rp" class="form"><div class="grid2">${cur.parametros.map(campo).join('')}</div>
        <p class="err" id="rperr" role="alert"></p>
        <div class="toolbar"><button class="btn">${I('chart', 16)} Generar</button><button type="button" class="btn ghost" id="vpdf">Ver PDF</button><button type="button" class="btn ghost" id="dpdf">Descargar PDF</button></div></form></section>
    <div id="rout"></div>`;
  const qs = () => new URLSearchParams(formData($('#rp'))).toString();
  $('#vpdf').onclick = () => window.open(`/api/reportes/${cur.slug}/pdf?${qs()}`, '_blank', 'noopener');
  $('#dpdf').onclick = () => { location.href = `/api/reportes/${cur.slug}/pdf?${qs()}&descargar=1`; };
  $('#rp').onsubmit = async e => {
    e.preventDefault(); $('#rperr').textContent = '';
    await busy(e.target.querySelector('.btn'), async () => {
      try { pintarInforme(await api(`/reportes/${cur.slug}?${qs()}`)); } catch (err) { $('#rperr').textContent = err.message; }
    });
  };
  $('#rp').requestSubmit();
}
function pintarInforme(inf) {
  const celda = v => typeof v === 'string' && /^\d{4}-\d\d-\d\dT/.test(v) ? fmtDateTime(v) : typeof v === 'string' && /^\d{4}-\d\d-\d\d$/.test(v) ? fmtDate(v) : esc(v ?? '');
  $('#rout').innerHTML = `<p class="mut" style="margin:4px 2px 12px">${esc(inf.subtitulo || '')}</p>` + inf.bloques.map(b => {
    if (b.clase === 'grafico') {
      const vals = b.series[0]?.valores || [], max = Math.max(1, ...vals);
      return `<section class="card" style="margin-bottom:16px"><div class="chead"><h2>${esc(b.titulo)}</h2></div><div class="slist">
        ${b.etiquetas.map((l, k) => `<div style="display:grid;grid-template-columns:minmax(120px,220px) 1fr auto;gap:12px"><span>${esc(l)}</span>
          <span style="background:var(--line-2);border-radius:4px;height:14px;align-self:center"><i style="display:block;height:100%;width:${vals[k] / max * 100}%;background:var(--g);border-radius:4px"></i></span>
          <b class="small">${vals[k] >= 1000 ? cop(vals[k]) : vals[k]}</b></div>`).join('') || '<p class="mut">Sin datos</p>'}</div></section>`;
    }
    return `<section class="card" style="margin-bottom:16px"><div class="chead"><h2>${esc(b.titulo)}</h2><span class="mut small">${b.total ?? b.filas.length} filas</span></div>
      <div class="tscroll"><table class="tbl"><thead><tr>${b.columnas.map(c => `<th>${esc(c)}</th>`).join('')}</tr></thead>
      <tbody>${b.filas.slice(0, 300).map(f => `<tr>${f.map(v => `<td>${celda(v)}</td>`).join('')}</tr>`).join('') || `<tr><td colspan="${b.columnas.length}"><div class="empty">Sin datos para los parámetros indicados</div></td></tr>`}</tbody></table></div>
      ${b.filas.length > 300 ? '<p class="mut small pad">Se muestran 300 filas; el PDF incluye todas.</p>' : ''}${b.nota ? `<p class="mut small pad">${esc(b.nota)}</p>` : ''}</section>`;
  }).join('');
}

/* ---- auditoría ---- */
async function aAuditoria(q) {
  const pagina = +(q.get('p') || 1), accion = q.get('accion') || '', usuario = q.get('usuario') || '';
  const r = await api(`/auditoria?${new URLSearchParams({pagina, tamano: 20, accion, usuario})}`);
  const pages = Math.max(1, Math.ceil(r.total / r.tamano));
  const link = n => `#/admin/auditoria?${new URLSearchParams({p: n, accion, usuario})}`;
  const cls = a => /FALLIDO|BLOQUEADO|SOSPECHOSA|ELIMINAR|CANCELAR/.test(a) ? 'bad' : /LOGIN$|PAGO|CREAR/.test(a) ? 'ok' : 'info';
  $('#main').innerHTML = `<section class="card"><form class="chead" id="af"><div class="toolbar">
      <select class="input" name="accion" aria-label="Acción"><option value="">Todas las acciones</option>${r.acciones.map(a => `<option ${a === accion ? 'selected' : ''}>${esc(a)}</option>`).join('')}</select>
      <label class="tsearch"><span class="sr">Usuario</span>${I('search', 16)}<input class="input" name="usuario" placeholder="Usuario" value="${esc(usuario)}"></label>
      <button class="btn sm">Filtrar</button></div><span class="mut small">${r.total} eventos</span></form>
    <div class="tscroll"><table class="tbl"><thead><tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Entidad</th><th>Detalle</th><th>IP</th></tr></thead><tbody>
      ${r.filas.map(f => `<tr><td>${fmtDateTime(f.fecha)}</td><td>${esc(f.username || '—')}</td><td><span class="badge ${cls(f.accion)}">${esc(f.accion)}</span></td>
        <td>${esc(f.entidad || '')}</td><td class="small">${esc(f.detalle || '')}</td><td class="small mut">${esc(f.ip || '')}</td></tr>`).join('') || '<tr><td colspan="6"><div class="empty">Sin eventos</div></td></tr>'}</tbody></table></div>
    <div class="pager"><span>Página ${r.pagina} de ${pages}</span><div>
      <a class="btn ghost sm" ${r.pagina > 1 ? `href="${link(r.pagina - 1)}"` : 'aria-disabled="true" style="opacity:.5;pointer-events:none"'}>Anterior</a>
      <a class="btn ghost sm" ${r.pagina < pages ? `href="${link(r.pagina + 1)}"` : 'aria-disabled="true" style="opacity:.5;pointer-events:none"'}>Siguiente</a></div></div></section>`;
  $('#af').onsubmit = e => { e.preventDefault(); const d = formData(e.target); go(`/admin/auditoria?${new URLSearchParams({p: 1, ...d})}`); };
}

Object.assign(window, {closeModal, go, logout, S, store, $});
render();
