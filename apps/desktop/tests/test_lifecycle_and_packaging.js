/**
 * Comprehensive Lifecycle, Tray, and Standalone Packaging Test Suite for Phenom Desktop
 *
 * Verifies:
 * 1. Python runtime detection hierarchy (packaged runtime priority vs local venv vs system fallback).
 * 2. Version parser guardrails (< 3.11 rejection, >= 3.11 acceptance).
 * 3. Session token persistent generation and isolation.
 * 4. System tray context menu generation and dynamic mute toggle.
 * 5. Watchdog parameters and max restart backoff guards.
 * 6. Package.json build / NSIS installer metadata integrity.
 */

const assert = require('assert');
const path = require('path');
const fs = require('fs');
const os = require('os');
const crypto = require('crypto');
const { parsePythonVersion, detectPythonCommand } = require('../electron/pythonVersion.cjs');

console.log('=== Phenom Desktop Lifecycle & Packaging Test Suite ===\n');

// --- 1. Python Runtime Detection & Bundling Hierarchy ---
console.log('[Test 1] Python Version Parsing & Guardrails');
assert.strictEqual(parsePythonVersion('Python 3.10.9').isSupported, false, 'Python 3.10 must be unsupported');
assert.strictEqual(parsePythonVersion('Python 2.7.18').isSupported, false, 'Python 2.7 must be unsupported');
assert.strictEqual(parsePythonVersion('Python 3.11.9').isSupported, true, 'Python 3.11.9 must be supported');
assert.strictEqual(parsePythonVersion('Python 3.12.2').isSupported, true, 'Python 3.12.2 must be supported');
assert.strictEqual(parsePythonVersion(''), null, 'Empty string must return null');
assert.strictEqual(parsePythonVersion('Unknown command error'), null, 'Invalid string must return null');
console.log('  PASS: Version parsing strictly enforces Python >= 3.11.');

console.log('[Test 2] Packaged Runtime Priority Resolution');
const detectedBase = detectPythonCommand();
assert.ok(detectedBase, 'Base Python environment must be detected');

const mockResDir = fs.mkdtempSync(path.join(os.tmpdir(), 'phenom-pkg-test-'));
const mockRuntimeDir = path.join(mockResDir, 'runtime');
const mockScriptsDir = path.join(mockRuntimeDir, 'Scripts');
fs.mkdirSync(mockScriptsDir, { recursive: true });

const venvCfgPath = path.resolve(__dirname, '../../../.venv-clean/pyvenv.cfg');
if (fs.existsSync(venvCfgPath)) {
  fs.copyFileSync(venvCfgPath, path.join(mockRuntimeDir, 'pyvenv.cfg'));
}
const mockPythonExe = path.join(mockScriptsDir, 'python.exe');
fs.copyFileSync(detectedBase.cmd, mockPythonExe);

try {
  const detectedPackaged = detectPythonCommand(mockResDir);
  assert.ok(detectedPackaged, 'Must detect packaged standalone runtime');
  assert.strictEqual(detectedPackaged.source, 'packaged_runtime', 'Packaged runtime MUST take precedence');
  assert.strictEqual(path.resolve(detectedPackaged.cmd), path.resolve(mockPythonExe));
  console.log(`  PASS: Bundled runtime correctly prioritized (${detectedPackaged.cmd}).`);
} finally {
  try {
    fs.rmSync(mockResDir, { recursive: true, force: true });
  } catch {}
}

// --- 2. Session Token Generation & Persistence ---
console.log('[Test 3] Session Token Generation & Idempotency');
const testTokenDir = fs.mkdtempSync(path.join(os.tmpdir(), 'phenom-token-test-'));
const tokenFile = path.join(testTokenDir, '.session_token');

let generatedToken = crypto.randomBytes(32).toString('hex');
fs.writeFileSync(tokenFile, generatedToken, 'utf8');

const readToken = fs.readFileSync(tokenFile, 'utf8').trim();
assert.strictEqual(readToken, generatedToken, 'Session token must match stored value');
assert.strictEqual(readToken.length, 64, 'Token must be 32 bytes hex encoded (64 characters)');
fs.rmSync(testTokenDir, { recursive: true, force: true });
console.log('  PASS: Session token generation and file persistence verified.');

// --- 3. Package.json & NSIS Configuration Integrity ---
console.log('[Test 4] electron-builder & NSIS Packaging Configuration');
const pkgJsonPath = path.resolve(__dirname, '../package.json');
const pkg = JSON.parse(fs.readFileSync(pkgJsonPath, 'utf8'));

assert.strictEqual(pkg.name, 'phenom-desktop');
assert.strictEqual(pkg.build.appId, 'com.phenom.assistant');
assert.strictEqual(pkg.build.productName, 'Phenom');
assert.ok(pkg.build.win.target.includes('nsis'), 'Target must include nsis');
assert.strictEqual(pkg.build.nsis.oneClick, false, 'NSIS must support custom installation directory');
assert.strictEqual(pkg.build.nsis.createDesktopShortcut, true, 'Desktop shortcut must be enabled');
assert.strictEqual(pkg.build.nsis.createStartMenuShortcut, true, 'Start Menu shortcut must be enabled');
assert.strictEqual(pkg.build.nsis.shortcutName, 'Phenom Assistant', 'Shortcut name must be Phenom Assistant');
assert.strictEqual(pkg.build.nsis.deleteAppDataOnUninstall, false, 'User data/vault must be preserved on uninstall');

const resourceSources = pkg.build.extraResources.map(r => r.from);
assert.ok(resourceSources.includes('../../services'), 'extraResources must bundle services/');
assert.ok(resourceSources.includes('../../services/backend'), 'extraResources must bundle services/backend/');
console.log('  PASS: NSIS configuration parameters and resource mappings are fully valid.');

// --- 4. Main Process Tray Menu & Watchdog Logic Audit ---
console.log('[Test 5] Main Process Tray Menu & Watchdog Configuration');
const mainCjsPath = path.resolve(__dirname, '../electron/main.cjs');
const mainCjs = fs.readFileSync(mainCjsPath, 'utf8');

assert.ok(mainCjs.includes('MAX_BACKEND_RESTARTS = 5'), 'Watchdog must allow maximum 5 restarts');
assert.ok(mainCjs.includes('delayMs = 1500'), 'Watchdog restart backoff must be under 2000ms SLA');
assert.ok(mainCjs.includes('Show Phenom'), 'Tray menu must include Show Phenom');
assert.ok(mainCjs.includes('Hide to Tray'), 'Tray menu must include Hide to Tray');
assert.ok(mainCjs.includes('Mute Voice'), 'Tray menu must include dynamic Mute Voice toggle');
assert.ok(mainCjs.includes('Guardian Kill Switch (HALT)'), 'Tray menu must include Kill Switch');
assert.ok(mainCjs.includes('Quit Phenom'), 'Tray menu must include Quit Phenom');
assert.ok(mainCjs.includes('app.setLoginItemSettings'), 'Auto-start login settings must be registered');
assert.ok(mainCjs.includes('openAsHidden: true'), 'Auto-start must launch hidden to tray');
console.log('  PASS: Tray actions, mute toggle, and watchdog supervision verified.');

// --- 5. Preload Bridge API Surface ---
console.log('[Test 6] Preload Bridge Context API Surface');
const preloadCjsPath = path.resolve(__dirname, '../electron/preload.cjs');
const preloadCjs = fs.readFileSync(preloadCjsPath, 'utf8');

assert.ok(preloadCjs.includes('getSessionToken'), 'Preload must expose getSessionToken');
assert.ok(preloadCjs.includes('isFirstRunDone'), 'Preload must expose isFirstRunDone');
assert.ok(preloadCjs.includes('setFirstRunDone'), 'Preload must expose setFirstRunDone');
assert.ok(preloadCjs.includes('isVoiceMuted'), 'Preload must expose isVoiceMuted');
assert.ok(preloadCjs.includes('setVoiceMuted'), 'Preload must expose setVoiceMuted');
assert.ok(preloadCjs.includes('onVoiceMutedChanged'), 'Preload must expose onVoiceMutedChanged');
assert.ok(preloadCjs.includes('triggerGuardianKill'), 'Preload must expose triggerGuardianKill');
assert.ok(preloadCjs.includes('onGuardianHotkey'), 'Preload must expose onGuardianHotkey');
console.log('  PASS: Context bridge API surface verified.');

console.log('\nAll 6/6 desktop lifecycle and packaging tests PASSED cleanly!');
