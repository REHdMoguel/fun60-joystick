// Prueba de la lógica de negocio de la página Fase 4 sin navegador.
// Concatena el <script> del index.html + el código de prueba en un solo
// archivo para compartir scope (let/const), y lo ejecuta con node.
const fs = require('fs');
const path = require('path');
const os = require('os');

const html = fs.readFileSync(path.join(__dirname, '..', 'phase3-joystick', 'index.html'), 'utf8');
const pageJs = html.match(/<script>([\s\S]*?)<\/script>/)[1];

// ── stubs de entorno ──
const stubs = `
const __elements = {};
function __fakeEl(id) {
  return {
    id, innerHTML: '', textContent: '', value: '', checked: false,
    classList: { add(){}, remove(){}, toggle(){}, contains(){ return false; } },
    style: {}, appendChild(){}, querySelector(){ return null; },
  };
}
global.document = {
  getElementById: id => { if (!__elements[id]) __elements[id] = __fakeEl(id); return __elements[id]; },
  createElement: () => __fakeEl('created'),
};
global.window = { addEventListener(){} };
global.localStorage = {
  _d: {}, getItem(k){ return this._d[k] ?? null; }, setItem(k,v){ this._d[k] = String(v); },
};
global.navigator = { hid: null };
global.performance = { now: () => Date.now() };
global.WebSocket = function(){};
global.alert = () => {};
global.confirm = () => true;
global.Blob = class {};
global.URL = { createObjectURL: () => 'blob:x' };
global.FileReader = class {};
global.setInterval = () => 0;
global.setTimeout = (fn) => 0;
`;

// quitar el setInterval de arranque de la página
const cleanPageJs = pageJs.replace(/setInterval\(\(\) => sendState\(false\), 1000 \/ 120\);?\s*$/, '');

// ── código de prueba (se concatena, comparte scope con la página) ──
const tests = `
// ── pruebas ──
let passed = 0, failed = 0;
function t(name, cond) {
  if (cond) { passed++; console.log('  ✅', name); }
  else { failed++; console.log('  ❌', name); }
}

console.log('── friendly() ──');
t('KeyE → E', friendly('KeyE') === 'E');
t('Digit1 → 1', friendly('Digit1') === '1');
t('Space → ESPACIO', friendly('Space') === 'ESPACIO');
t('ShiftLeft → SHIFT', friendly('ShiftLeft') === 'SHIFT');
t('ArrowUp → ↑', friendly('ArrowUp') === '↑');
t('null → —', friendly(null) === '—');

console.log('── vksFor() ──');
t('KeyE → 0x45', vksFor('KeyE')[0] === 0x45);
t('KeyW → 0x57', vksFor('KeyW')[0] === 0x57);
t('Digit0 → 0x30', vksFor('Digit0')[0] === 0x30);
t('Space → 0x20', vksFor('Space')[0] === 0x20);
t('ShiftLeft → incluye 0x10 y 0xA0', vksFor('ShiftLeft').includes(0x10) && vksFor('ShiftLeft').includes(0xA0));
t('F1 → 0x70', vksFor('F1')[0] === 0x70);
t('F12 → 0x7B', vksFor('F12')[0] === 0x7B);
t('ArrowRight → 0x27', vksFor('ArrowRight')[0] === 0x27);
t('null → []', vksFor(null).length === 0);

console.log('── ejes ──');
state = { KeyD: 1.0, KeyA: 0.0, KeyW: 0.5, KeyS: 0.0 };
let ax = computeAxes('left');
// (1, 0.5) → len 1.118 > 1 → se normaliza al círculo unitario (correcto)
const expLen = Math.hypot(1.0, 0.5);
t('X = D−A normalizado', Math.abs(ax.X - 1.0/expLen) < 0.001);
t('Y = W−S normalizado', Math.abs(ax.Y - 0.5/expLen) < 0.001);
state = { KeyD: 1.0, KeyW: 1.0 };
ax = computeAxes('left');
const len = Math.hypot(ax.X, ax.Y);
t('diagonal normalizada (len=1)', Math.abs(len - 1.0) < 0.001);
currentProfile = profiles.find(p => p.id === 'aventura');
ax = computeAxes('right');
t('stick derecho inactivo → 0', ax.X === 0 && ax.Y === 0);

console.log('── botones (histeresis) ──');
currentProfile = profiles.find(p => p.id === 'aventura');
document.getElementById('sens').value = '15';
state = { KeyE: 0.3 };
let btns = computeButtons();
t('E 0.3 → botón A presionado', btns['A'] === 1);
state = { KeyE: 0.05 };
btns = computeButtons();
t('E 0.05 → botón A suelto', btns['A'] === 0);
state = { KeyE: 0.3 };
computeButtons();
state = { KeyE: 0.10 };
btns = computeButtons();
t('histeresis: 0.10 tras 0.30 se mantiene presionado', btns['A'] === 1);

console.log('── gatillos (rampa) ──');
currentProfile = profiles.find(p => p.id === 'mando_completo');
trigVal = { LT: 0, RT: 0 };
state = { KeyT: 1.0 };
let tr = computeTriggers(1/60);
t('LT sube tras 1 frame', tr.LT > 0 && tr.LT <= 1);
state = { KeyT: 0.0 };
tr = computeTriggers(0.5);
t('LT baja a 0 tras soltar', tr.LT === 0);

console.log('── bloqueo dinámico (block_vks) ──');
currentProfile = profiles.find(p => p.id === 'aventura');
document.getElementById('blockKeys').checked = true;
let vks = computeBlockVks();
t('bloquea W (0x57)', vks.includes(0x57));
t('bloquea A (0x41)', vks.includes(0x41));
t('NO bloquea E (no aprendida aún)', !vks.includes(0x45));
KEYMAP[69] = 'KeyE';
vks = computeBlockVks();
t('tras aprender E, sí la bloquea', vks.includes(0x45));
learnTarget = 'A';
vks = computeBlockVks();
t('durante aprendizaje → sin bloqueo', vks.length === 0);
learnTarget = null;

console.log('── perfiles ──');
t('hay 3 presets', profiles.length === 3);
t('perfil actual cargado', !!currentProfile);
const saveData = JSON.stringify({ keymap: KEYMAP, profiles, current: currentProfileId });
t('serializable sin errores', saveData.length > 50);

console.log('── aprendizaje (emparejamiento keydown+reporte) ──');
// simular: aprender tecla suelta con código HID 0x52 (R) y keydown KeyR
learnAnyMode = true;
lastKeyDown = { code: 'KeyR', t: performance.now() };
let nm = tryLearnPair(0x52);
t('empareja 0x52 → KeyR', nm === 'KeyR' && KEYMAP[0x52] === 'KeyR');
learnAnyMode = false;

console.log(\`\\n\${passed} pasaron, \${failed} fallaron\`);
process.exit(failed ? 1 : 0);
`;

const combined = stubs + '\n' + cleanPageJs + '\n' + tests;
const outFile = path.join(os.tmpdir(), 'page_logic_test.js');
fs.writeFileSync(outFile, combined, 'utf8');
console.log('Archivo de prueba: ' + outFile);
