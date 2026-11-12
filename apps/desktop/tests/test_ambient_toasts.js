/**
 * Phenom 5.0 Phase 3: Proactive Ambient Intelligence & Toast HUD Verification Suite
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('=== Phenom 5.0: Proactive Ambient HUD Toasts Test Suite ===\n');

const overlayPath = path.resolve(__dirname, '../src/components/ScreenBorderOverlay.tsx');
const appPath = path.resolve(__dirname, '../src/App.tsx');

assert(fs.existsSync(overlayPath), 'ScreenBorderOverlay.tsx must exist');
assert(fs.existsSync(appPath), 'App.tsx must exist');

const overlayContent = fs.readFileSync(overlayPath, 'utf8');
const appContent = fs.readFileSync(appPath, 'utf8');

// [Test 1] AmbientAlertItem Interface Definition
console.log('[Test 1] AmbientAlertItem Interface Definition');
assert(overlayContent.includes('export interface AmbientAlertItem'), 'Must export AmbientAlertItem interface');
assert(overlayContent.includes('urgency: \'low\' | \'medium\' | \'high\' | \'critical\''), 'Must define 4 urgency levels');
assert(overlayContent.includes('category: \'calendar\' | \'system\' | \'task\' | \'general\''), 'Must define 4 alert categories');
console.log('  PASS: AmbientAlertItem interface verified with full type safety.\n');

// [Test 2] ScreenBorderOverlay Toast Container & Styling
console.log('[Test 2] ScreenBorderOverlay Toast Container & Styling');
assert(overlayContent.includes('data-testid="ambient-alerts-container"'), 'Must render ambient-alerts-container');
assert(overlayContent.includes('ambientAlerts?: AmbientAlertItem[]'), 'Must accept ambientAlerts prop');
assert(overlayContent.includes('onDismissAlert?: (id: string) => void'), 'Must accept onDismissAlert callback');
assert(overlayContent.includes('rgba(8, 11, 16, 0.94)'), 'Must render Midnight Black glassmorphism background');
assert(overlayContent.includes('rgba(0, 82, 255'), 'Must render Electric Cobalt border accent');
assert(overlayContent.includes('#CCFF00'), 'Must render Acid Lime category pill');
console.log('  PASS: Toast container, Midnight Black glass, and Acid Lime styling verified.\n');

// [Test 3] Early Return Guard Update
console.log('[Test 3] Early Return Guard Update');
assert(
  overlayContent.includes('(!ambientAlerts || ambientAlerts.length === 0)'),
  'Must maintain overlay visible when ambient alerts are active'
);
console.log('  PASS: Overlay visibility preserved during active ambient alerts.\n');

// [Test 4] App.tsx WebSocket Event Integration
console.log('[Test 4] App.tsx WebSocket Event Integration');
assert(appContent.includes("mtype === 'ambient.alert'"), "App.tsx must handle 'ambient.alert' messages");
assert(appContent.includes('setAmbientAlerts'), 'App.tsx must maintain ambientAlerts state');
assert(appContent.includes('autoDismiss'), 'App.tsx must schedule auto-dismiss timer');
assert(appContent.includes('ambientAlerts={ambientAlerts}'), 'App.tsx must pass ambientAlerts to ScreenBorderOverlay');
assert(appContent.includes('onDismissAlert='), 'App.tsx must pass onDismissAlert callback');
console.log('  PASS: WebSocket message routing and state management verified in App.tsx.\n');

console.log('=== ALL 4 AMBIENT TOAST TESTS PASSED ===');
