/* Ilustraciones SVG propias (sin imágenes externas): logo, vehículo, bosque del hero, íconos de categorías y de interfaz. */
const ART = (() => {
  const M = '#c3cec7', D = '#34433a', G = '#2fb344', G2 = '#188a31', L = '#eef3ef';

  const ui = {
    cart: '<path d="M3 4h2.2l2.3 10.6a2 2 0 0 0 2 1.6h7.9a2 2 0 0 0 1.9-1.5L21 8H6.3" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="10" cy="20" r="1.6" fill="currentColor"/><circle cx="17" cy="20" r="1.6" fill="currentColor"/>',
    search: '<circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2.2"/><path d="m20 20-4-4" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>',
    filter: '<path d="M3 5h18l-7 8.5V19l-4 2v-7.5z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    down: '<path d="m6 9 6 6 6-6" fill="currentColor"/>',
    left: '<path d="m15 5-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>',
    right: '<path d="m9 5 7 7-7 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>',
    pin: '<path d="M12 22s7-6.2 7-12a7 7 0 1 0-14 0c0 5.8 7 12 7 12z" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="10" r="2.6" fill="none" stroke="currentColor" stroke-width="2"/>',
    phone: '<path d="M5 3h4l2 5-2.5 1.5a11 11 0 0 0 6 6L16 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 5a2 2 0 0 1 2-2z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="m3 7 9 6 9-6" fill="none" stroke="currentColor" stroke-width="2"/>',
    clock: '<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 7v5l3 2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    user: '<circle cx="12" cy="8" r="4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M4 21a8 8 0 0 1 16 0" fill="none" stroke="currentColor" stroke-width="2"/>',
    users: '<circle cx="9" cy="8" r="3.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14a6 6 0 0 1 3.5 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    home: '<path d="M3 11 12 4l9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    box: '<path d="m12 3 9 4.5v9L12 21l-9-4.5v-9z M3 7.5l9 4.5 9-4.5M12 12v9" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    truck: '<path d="M2 6h12v10H2zM14 10h4l3 3v3h-7z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><circle cx="6" cy="18" r="2" fill="currentColor"/><circle cx="17" cy="18" r="2" fill="currentColor"/>',
    receipt: '<path d="M6 2h12v20l-3-2-3 2-3-2-3 2zM9 7h6M9 11h6M9 15h4" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>',
    tag: '<path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><circle cx="8" cy="8" r="1.6" fill="currentColor"/>',
    layers: '<path d="m12 3 9 5-9 5-9-5zM3 13l9 5 9-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    alert: '<path d="M12 3 2 20h20zM12 10v4M12 17v.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>',
    check: '<path d="m5 12 5 5 9-10" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>',
    x: '<path d="M6 6l12 12M18 6 6 18" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>',
    lock: '<rect x="4" y="10" width="16" height="11" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3" fill="none" stroke="currentColor" stroke-width="2"/>',
    eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="2"/>',
    logout: '<path d="M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 16l-4-4 4-4M6 12h10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    store: '<path d="M3 9 5 4h14l2 5M3 9v11h18V9M3 9h18M9 20v-6h6v6" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    plus: '<path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>',
    card: '<rect x="2" y="5" width="20" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M2 10h20M6 15h4" stroke="currentColor" stroke-width="2"/>',
    bank: '<path d="M3 9 12 4l9 5M4 10v8M9 10v8M15 10v8M20 10v8M2 20h20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    cash: '<rect x="2" y="6" width="20" height="12" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="2.6" fill="none" stroke="currentColor" stroke-width="2"/>',
    wallet: '<path d="M3 7a2 2 0 0 1 2-2h13v4M3 7v11a2 2 0 0 0 2 2h15V9H5a2 2 0 0 1-2-2z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><circle cx="16" cy="14.5" r="1.4" fill="currentColor"/>',
    shield: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="m8.5 12 2.5 2.5 4.5-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    wrench: '<path d="M14.7 6.3a4 4 0 0 0 5 5L21 13l-8 8-3-3 8-8-1.3-1.3a4 4 0 0 1-5-5L14 2z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    sun: '<circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M5 19l1.5-1.5M17.5 6.5 19 5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  };
  const icon = (n, s = 20) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" aria-hidden="true">${ui[n] || ''}</svg>`;

  const logo = (s = 46) => `<svg width="${s}" height="${s}" viewBox="0 0 64 64" aria-hidden="true">
    <circle cx="32" cy="32" r="30" fill="${G2}"/><circle cx="32" cy="32" r="25" fill="none" stroke="#fff" stroke-width="2" stroke-dasharray="5 4"/>
    <g transform="translate(32 32)"><circle r="11" fill="#fff"/><circle r="5" fill="${G2}"/>
    ${[0, 45, 90, 135, 180, 225, 270, 315].map(a => `<rect x="-3" y="-15.5" width="6" height="6" rx="1" fill="#fff" transform="rotate(${a})"/>`).join('')}</g>
    <path d="M14 46 26 34" stroke="#e02424" stroke-width="5" stroke-linecap="round"/><path d="M50 46 38 34" stroke="#fff" stroke-width="5" stroke-linecap="round"/></svg>`;

  /* Camioneta genérica (sin marcas) — vista lateral */
  function car(color = '#e9edf0', w = 560) {
    const id = 'c' + Math.random().toString(36).slice(2, 7);
    const wheel = x => `<g transform="translate(${x} 166)"><circle r="44" fill="#151a17"/><circle r="40" fill="#22292a"/>
      <circle r="27" fill="url(#${id}r)"/>${[0, 72, 144, 216, 288].map(a => `<rect x="-3.5" y="-26" width="7" height="22" rx="3" fill="#56605b" transform="rotate(${a})"/>`).join('')}
      <circle r="7" fill="#9aa5a0"/><circle r="3" fill="#3d4642"/></g>`;
    return `<svg width="${w}" viewBox="0 0 560 230" role="img" aria-label="Camioneta ilustrada"><defs>
      <linearGradient id="${id}b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset=".45" stop-color="${color}"/><stop offset="1" stop-color="#9aa3a8"/></linearGradient>
      <linearGradient id="${id}g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3b4b55"/><stop offset="1" stop-color="#11181d"/></linearGradient>
      <radialGradient id="${id}r"><stop offset="0" stop-color="#e3e8e6"/><stop offset="1" stop-color="#8d9894"/></radialGradient></defs>
      <ellipse cx="282" cy="210" rx="250" ry="12" fill="#000" opacity=".35"/>
      <path d="M28 160 34 124q5-20 34-25l84-6 52-38q15-10 40-11h132q26 1 42 14l46 40 34 6q24 4 28 24l4 32q0 12-12 12h-34a46 46 0 0 0-92 0H180a46 46 0 0 0-92 0H40q-12 0-12-12z" fill="url(#${id}b)" stroke="#7d878c" stroke-width="1.5"/>
      <path d="M160 94 210 59q12-8 30-8h52v43z" fill="url(#${id}g)"/><path d="M304 51h68q20 1 32 12l34 31H304z" fill="url(#${id}g)"/>
      <path d="M296 51v104" stroke="#8a9499" stroke-width="2"/><path d="M40 128h470" stroke="#fff" stroke-opacity=".7" stroke-width="2"/>
      <rect x="250" y="106" width="22" height="5" rx="2.5" fill="#6d777b"/><rect x="368" y="106" width="22" height="5" rx="2.5" fill="#6d777b"/>
      <path d="M496 108q14 2 18 14h-24z" fill="#fff8d6" stroke="#b8b28c"/><path d="M31 120h12v14H29z" fill="#d32020"/>
      <path d="M506 146h22" stroke="#4b5559" stroke-width="6" stroke-linecap="round"/>
      ${wheel(134)}${wheel(424)}</svg>`;
  }

  /* Fondo del hero: bosque nocturno con camino y rayo de luz */
  function forest(seed = 1) {
    let r = seed * 9301;
    const rnd = () => (r = (r * 9301 + 49297) % 233280) / 233280;
    const row = (y, h, color, n) => Array.from({length: n}, (_, i) => {
      const x = i * (1240 / n) - 20 + rnd() * 30, hh = h * (0.7 + rnd() * 0.5), w = hh * 0.36;
      return `<path d="M${x} ${y - hh}L${x + w} ${y}H${x - w}Z" fill="${color}"/>`;
    }).join('');
    return `<svg viewBox="0 0 1200 440" preserveAspectRatio="xMidYMid slice" width="100%" height="100%" aria-hidden="true"><defs>
      <linearGradient id="fsky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0b2416"/><stop offset="1" stop-color="#16402a"/></linearGradient>
      <linearGradient id="fray" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d9f7c8" stop-opacity=".55"/><stop offset="1" stop-color="#d9f7c8" stop-opacity="0"/></linearGradient>
      <linearGradient id="froad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4c5a56"/><stop offset="1" stop-color="#1d2523"/></linearGradient>
      <linearGradient id="fshade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#04110a" stop-opacity=".85"/><stop offset=".55" stop-color="#04110a" stop-opacity=".1"/><stop offset="1" stop-color="#04110a" stop-opacity=".3"/></linearGradient></defs>
      <rect width="1200" height="440" fill="url(#fsky)"/>
      <path d="M560 0h120l40 300H520z" fill="url(#fray)"/>
      ${row(300, 230, '#1f5a37', 26)}${row(330, 260, '#164a2c', 22)}
      <path d="M560 250h80l330 190H230z" fill="url(#froad)"/>
      <path d="M598 260 590 440M602 260l10 180" stroke="#e9d36b" stroke-width="3" stroke-dasharray="14 12" opacity=".8"/>
      ${row(380, 300, '#0f3a22', 18)}${row(470, 360, '#082a17', 14)}
      <rect width="1200" height="440" fill="url(#fshade)"/></svg>`;
  }

  /* Íconos de categorías de repuestos (viewBox 120) */
  const P = {
    radiador: `<rect x="22" y="22" width="76" height="12" rx="3" fill="${D}"/><rect x="22" y="86" width="76" height="12" rx="3" fill="${D}"/>
      <rect x="26" y="34" width="68" height="52" fill="${M}"/>${Array.from({length: 11}, (_, i) => `<rect x="${29 + i * 6}" y="36" width="2.4" height="48" fill="#8d9a92"/>`).join('')}
      <rect x="98" y="26" width="10" height="7" rx="2" fill="${G}"/><rect x="12" y="88" width="10" height="7" rx="2" fill="${G}"/>`,
    filtro: `<rect x="32" y="30" width="56" height="66" rx="8" fill="${G2}"/>${[42, 52, 62, 72, 82].map(y => `<rect x="32" y="${y}" width="56" height="3" fill="#127028"/>`).join('')}
      <ellipse cx="60" cy="30" rx="28" ry="9" fill="${M}"/><ellipse cx="60" cy="30" rx="10" ry="3.5" fill="${D}"/>`,
    freno: `<circle cx="60" cy="62" r="38" fill="${M}"/><circle cx="60" cy="62" r="30" fill="none" stroke="#a7b3ac" stroke-width="2"/><circle cx="60" cy="62" r="14" fill="${D}"/>
      ${[0, 60, 120, 180, 240, 300].map(a => `<circle cx="60" cy="38" r="2.6" fill="#8d9a92" transform="rotate(${a} 60 62)"/>`).join('')}
      <path d="M78 26q24 10 26 36l-14 2q-2-16-18-24z" fill="#e02424"/>`,
    amortiguador: `<rect x="54" y="14" width="12" height="30" rx="3" fill="${M}"/><rect x="48" y="44" width="24" height="56" rx="5" fill="${D}"/>
      ${[30, 42, 54, 66, 78].map(y => `<ellipse cx="60" cy="${y}" rx="24" ry="5" fill="none" stroke="${G}" stroke-width="5"/>`).join('')}
      <circle cx="60" cy="12" r="7" fill="none" stroke="${D}" stroke-width="4"/><circle cx="60" cy="104" r="7" fill="none" stroke="${D}" stroke-width="4"/>`,
    motor: `<rect x="24" y="44" width="72" height="46" rx="6" fill="${M}"/><rect x="30" y="26" width="60" height="20" rx="4" fill="${D}"/>
      ${[38, 54, 70].map(x => `<rect x="${x}" y="30" width="12" height="12" rx="2" fill="${G}"/>`).join('')}<rect x="14" y="58" width="10" height="18" rx="2" fill="${D}"/>
      <rect x="96" y="54" width="12" height="24" rx="3" fill="${D}"/><rect x="34" y="90" width="52" height="10" rx="3" fill="${D}"/>`,
    embrague: `<circle cx="60" cy="60" r="40" fill="${D}"/><circle cx="60" cy="60" r="32" fill="${M}"/><circle cx="60" cy="60" r="12" fill="${D}"/>
      ${[0, 60, 120, 180, 240, 300].map(a => `<rect x="54" y="30" width="12" height="9" rx="2" fill="${G}" transform="rotate(${a} 60 60)"/>`).join('')}`,
    bujia: `<rect x="54" y="12" width="12" height="14" rx="3" fill="${M}"/><rect x="48" y="26" width="24" height="34" rx="6" fill="#f3f4f2" stroke="#c8cfca"/>
      <path d="M46 60h28l-4 8H50z" fill="${D}"/><rect x="50" y="68" width="20" height="10" fill="${G2}"/>${[80, 86, 92].map(y => `<rect x="52" y="${y}" width="16" height="3" fill="${M}"/>`).join('')}
      <path d="M60 96v10h8" fill="none" stroke="${D}" stroke-width="3"/>`,
    luz: `<path d="M24 40q36-16 72 0v40q-36 16-72 0z" fill="${D}"/><path d="M30 46q30-12 60 0v28q-30 12-60 0z" fill="#e8f2ff"/>
      <circle cx="48" cy="60" r="10" fill="#fff6c9"/><circle cx="74" cy="60" r="7" fill="#fff6c9"/><path d="M98 50h14M98 60h16M98 70h14" stroke="${G}" stroke-width="4" stroke-linecap="round"/>`,
    bateria: `<rect x="20" y="36" width="80" height="56" rx="6" fill="${D}"/><rect x="20" y="36" width="80" height="14" rx="6" fill="${G2}"/>
      <rect x="32" y="26" width="12" height="10" rx="2" fill="#e02424"/><rect x="76" y="26" width="12" height="10" rx="2" fill="${M}"/>
      <path d="M33 70h10M38 65v10M77 70h10" stroke="#fff" stroke-width="3" stroke-linecap="round"/><path d="M58 58l-6 14h8l-4 12 12-16h-8l4-10z" fill="#ffd34d"/>`,
    correa: `<circle cx="38" cy="44" r="20" fill="${M}"/><circle cx="84" cy="78" r="16" fill="${M}"/><circle cx="38" cy="44" r="6" fill="${D}"/><circle cx="84" cy="78" r="5" fill="${D}"/>
      <path d="M38 22Q74 20 100 76Q100 96 84 96Q60 96 20 50Q16 22 38 22z" fill="none" stroke="#1d2420" stroke-width="6" stroke-linejoin="round"/>`,
    bomba: `<circle cx="56" cy="62" r="34" fill="${M}"/><circle cx="56" cy="62" r="10" fill="${D}"/>${[0, 72, 144, 216, 288].map(a => `<path d="M56 52q14-10 22 4" fill="none" stroke="${G2}" stroke-width="6" stroke-linecap="round" transform="rotate(${a} 56 62)"/>`).join('')}
      <rect x="86" y="54" width="22" height="14" rx="3" fill="${D}"/>`,
    escape: `<rect x="44" y="40" width="52" height="40" rx="18" fill="${M}"/><path d="M10 68h34" stroke="${D}" stroke-width="10" stroke-linecap="round"/><path d="M96 56h16" stroke="${D}" stroke-width="8" stroke-linecap="round"/>
      <path d="M52 50h36M52 60h36M52 70h36" stroke="#a5b1aa" stroke-width="2"/>`,
    direccion: `<circle cx="60" cy="60" r="38" fill="none" stroke="${D}" stroke-width="10"/><circle cx="60" cy="60" r="11" fill="${G2}"/>
      <path d="M24 56h25M71 56h25M60 71v26" stroke="${D}" stroke-width="9" stroke-linecap="round"/>`,
    transmision: `<g transform="translate(46 64)"><circle r="26" fill="${M}"/>${Array.from({length: 10}, (_, i) => `<rect x="-5" y="-33" width="10" height="10" rx="2" fill="${M}" transform="rotate(${i * 36})"/>`).join('')}<circle r="8" fill="${D}"/></g>
      <g transform="translate(86 34)"><circle r="16" fill="${G2}"/>${Array.from({length: 8}, (_, i) => `<rect x="-4" y="-22" width="8" height="8" rx="2" fill="${G2}" transform="rotate(${i * 45})"/>`).join('')}<circle r="5" fill="${D}"/></g>`,
    carroceria: `<path d="M12 78 18 60q4-8 14-9l18-2 16-14q6-5 16-5h14q10 0 16 8l8 12q8 3 8 12v16H12z" fill="${G2}"/><path d="M50 50 64 38q4-3 10-3h10v15z" fill="#d9e7f2"/>
      <circle cx="34" cy="84" r="11" fill="${D}"/><circle cx="90" cy="84" r="11" fill="${D}"/><circle cx="34" cy="84" r="4" fill="${M}"/><circle cx="90" cy="84" r="4" fill="${M}"/>`,
    espejo: `<path d="M20 44q4-14 24-14h40q18 0 18 18v20q0 18-22 18H40q-20 0-20-18z" fill="${D}"/><path d="M28 48q2-10 18-10h36q12 0 12 12v14q0 12-16 12H44q-16 0-16-12z" fill="#cfe2ee"/>
      <path d="M40 46 70 74" stroke="#fff" stroke-width="4" opacity=".7"/><rect x="50" y="86" width="12" height="18" rx="3" fill="${D}"/>`,
    rodamiento: `<circle cx="60" cy="60" r="40" fill="${M}"/><circle cx="60" cy="60" r="30" fill="${D}"/>${Array.from({length: 10}, (_, i) => `<circle cx="60" cy="35" r="5.5" fill="#e6ebe8" transform="rotate(${i * 36} 60 60)"/>`).join('')}
      <circle cx="60" cy="60" r="20" fill="${M}"/><circle cx="60" cy="60" r="12" fill="${L}"/>`,
    sensor: `<rect x="40" y="20" width="22" height="36" rx="5" fill="${D}"/><rect x="44" y="56" width="14" height="14" fill="${M}"/>${[72, 78, 84].map(y => `<rect x="46" y="${y}" width="10" height="3" fill="${M}"/>`).join('')}
      <rect x="48" y="88" width="6" height="14" rx="2" fill="#a5b1aa"/><path d="M62 30q30 0 36 26t-8 40" fill="none" stroke="${G}" stroke-width="5" stroke-linecap="round"/>`,
    aceite: `<path d="M38 36h44l6 10v50a6 6 0 0 1-6 6H38a6 6 0 0 1-6-6V46z" fill="${G2}"/><rect x="48" y="20" width="18" height="16" rx="3" fill="${D}"/>
      <path d="M82 40q14 0 14 12v6" fill="none" stroke="${D}" stroke-width="5"/><rect x="40" y="58" width="40" height="26" rx="3" fill="#fff"/><path d="M60 62q8 10 0 16-8-6 0-16z" fill="#f2b705"/>`,
    generico: `<path d="M76 18a20 20 0 0 0-22 26L18 80a10 10 0 0 0 14 14l36-36a20 20 0 0 0 26-22L82 48 72 46 70 36z" fill="${M}" stroke="${D}" stroke-width="3" stroke-linejoin="round"/>`,
  };
  const MAP = {radiador: 'radiador', filtro: 'filtro', fren: 'freno', suspens: 'amortiguador', amortigu: 'amortiguador', motor: 'motor',
    embrag: 'embrague', encend: 'bujia', ilumin: 'luz', bater: 'bateria', correa: 'correa', bomba: 'bomba', escape: 'escape',
    direcc: 'direccion', transmis: 'transmision', carrocer: 'carroceria', espejo: 'espejo', rodamient: 'rodamiento', sensor: 'sensor', lubric: 'aceite'};
  const kind = cat => { const c = (cat || '').toLowerCase(); for (const k in MAP) if (c.includes(k)) return MAP[k]; return 'generico'; };
  const part = (cat, s = 110) => `<svg width="${s}" height="${s}" viewBox="0 0 120 120" aria-hidden="true">${P[kind(cat)]}</svg>`;

  return {icon, logo, car, forest, part};
})();
