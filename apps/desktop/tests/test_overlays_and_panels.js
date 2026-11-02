/**
 * Phenom 3.0: Overlays, Modals, System Tray & Secondary Panels Verification Suite
 * Verifies Midnight Black, Electric Cobalt, and Acid Lime styling across:
 * - App.tsx drawer wrapper
 * - ScreenBorderOverlay.tsx
 * - ConfirmationModal.tsx
 * - MiniOverlay.tsx
 * - All 7 panels (ActionLog, Approvals, Dashboard, History, LearnedRules, LiveView, Settings)
 * - Electron main.cjs window and tray configuration
 */

const assert = require('assert');
const path = require('path');
const fs = require('fs');

console.log('=== Phenom 3.0: Overlays & Panels Test Suite ===\n');

// 1. App.tsx Drawer Wrapper
console.log('[Test 1] App.tsx Cyber Drawer Container');
const appPath = path.resolve(__dirname, '../src/App.tsx');
assert.ok(fs.existsSync(appPath), 'App.tsx must exist');
const appContent = fs.readFileSync(appPath, 'utf8');
assert.ok(appContent.includes("background: 'rgba(8, 11, 16, 0.96)'"), 'Drawer must use Midnight Black glass');
assert.ok(appContent.includes("borderLeft: '1px solid rgba(0, 82, 255, 0.35)'"), 'Drawer must have Electric Cobalt border');
console.log('  PASS: App.tsx cyber drawer wrapper verified.');

// 2. ScreenBorderOverlay.tsx
console.log('[Test 2] ScreenBorderOverlay Cyber Glow & HUD Ticker');
const screenOverlayPath = path.resolve(__dirname, '../src/components/ScreenBorderOverlay.tsx');
assert.ok(fs.existsSync(screenOverlayPath), 'ScreenBorderOverlay.tsx must exist');
const screenContent = fs.readFileSync(screenOverlayPath, 'utf8');
assert.ok(screenContent.includes("return '#0052FF'; // Electric Cobalt"), 'Active automation border must be Electric Cobalt');
assert.ok(screenContent.includes("return '#CCFF00'; // Acid Lime"), 'Success automation border must be Acid Lime');
assert.ok(screenContent.includes("border: '2px solid #0052FF'"), 'Click ring outer border must be Electric Cobalt');
assert.ok(screenContent.includes("background: '#CCFF00'"), 'Click target dot must be Acid Lime');
assert.ok(screenContent.includes("background: 'rgba(8, 11, 16, 0.92)'"), 'Action ticker must use Midnight Black glass');
assert.ok(screenContent.includes("background: '#080B10'"), 'Takeover modal must use Midnight Black');
console.log('  PASS: ScreenBorderOverlay cyber automation glow and ticker verified.');

// 3. ConfirmationModal.tsx
console.log('[Test 3] ConfirmationModal Security Dialog');
const modalPath = path.resolve(__dirname, '../src/components/ConfirmationModal.tsx');
assert.ok(fs.existsSync(modalPath), 'ConfirmationModal.tsx must exist');
const modalContent = fs.readFileSync(modalPath, 'utf8');
assert.ok(modalContent.includes("backgroundColor: '#080B10'"), 'Dialog surface must be Midnight Black');
assert.ok(modalContent.includes("border: '1px solid rgba(0, 82, 255, 0.45)'"), 'Dialog must have Electric Cobalt border');
assert.ok(modalContent.includes("background: 'rgba(13, 17, 26, 0.85)'"), 'Action preview must use Midnight Surface');
assert.ok(modalContent.includes("background: '#040609'"), 'Code preview must use deep black');
console.log('  PASS: ConfirmationModal cyber security dialog verified.');

// 4. MiniOverlay.tsx
console.log('[Test 4] MiniOverlay Cyber Floating HUD');
const miniOverlayPath = path.resolve(__dirname, '../src/components/MiniOverlay.tsx');
assert.ok(fs.existsSync(miniOverlayPath), 'MiniOverlay.tsx must exist');
const miniContent = fs.readFileSync(miniOverlayPath, 'utf8');
assert.ok(miniContent.includes("background: 'rgba(8, 11, 16, 0.94)'"), 'Mini overlay must use Midnight Black glass');
assert.ok(miniContent.includes("border: '1px solid rgba(0, 82, 255, 0.35)'"), 'Mini overlay must have Electric Cobalt border');
assert.ok(miniContent.includes("color: '#CCFF00'"), 'Mini overlay mode badge/reminder must use Acid Lime');
console.log('  PASS: MiniOverlay cyber floating widget verified.');

// 5. Drawer Secondary Panels (ActionLog, Approvals, Dashboard, History, LearnedRules, LiveView, Settings)
console.log('[Test 5] Administrative Drawer Panels Cyber Styling');

// ActionLogPanel
const actionLogContent = fs.readFileSync(path.resolve(__dirname, '../src/components/panels/ActionLogPanel.tsx'), 'utf8');
assert.ok(actionLogContent.includes("background: 'rgba(13, 17, 26, 0.85)'"), 'ActionLog must use Midnight Surface cards');
assert.ok(actionLogContent.includes("color: '#CCFF00'"), 'ActionLog tool names must use Acid Lime');

// ApprovalsPanel
const approvalsContent = fs.readFileSync(path.resolve(__dirname, '../src/components/panels/ApprovalsPanel.tsx'), 'utf8');
assert.ok(approvalsContent.includes("background: 'rgba(13, 17, 26, 0.85)'"), 'Approvals must use Midnight Surface cards');
assert.ok(approvalsContent.includes("color: '#CCFF00'"), 'Approvals tool names must use Acid Lime');

// HistoryPanel
const historyContent = fs.readFileSync(path.resolve(__dirname, '../src/components/panels/HistoryPanel.tsx'), 'utf8');
assert.ok(historyContent.includes("background: m.role === 'user' ? 'rgba(0, 82, 255, 0.20)' : 'rgba(13, 17, 26, 0.85)'"), 'History message bubbles must use Cobalt and Midnight');

// LearnedRulesPanel
const rulesContent = fs.readFileSync(path.resolve(__dirname, '../src/components/panels/LearnedRulesPanel.tsx'), 'utf8');
assert.ok(rulesContent.includes("background: 'rgba(13, 17, 26, 0.85)'"), 'Learned rules must use Midnight Surface cards');
assert.ok(rulesContent.includes("background: '#CCFF00'"), 'Rule save button must use Acid Lime');

// LiveViewPanel
const liveViewContent = fs.readFileSync(path.resolve(__dirname, '../src/components/panels/LiveViewPanel.tsx'), 'utf8');
assert.ok(liveViewContent.includes("background: '#040609'"), 'Live viewport container must use deep black');
assert.ok(liveViewContent.includes("border: '1px solid rgba(0, 82, 255, 0.35)'"), 'Live viewport must have Electric Cobalt border');

// DashboardPanel
const dashboardContent = fs.readFileSync(path.resolve(__dirname, '../src/components/panels/DashboardPanel.tsx'), 'utf8');
assert.ok(dashboardContent.includes("background: 'rgba(8, 11, 16, 0.96)'"), 'Dashboard panel must use Midnight Black');
assert.ok(dashboardContent.includes("borderLeft: '1px solid rgba(0, 82, 255, 0.35)'"), 'Dashboard panel must have Electric Cobalt border');

// SettingsPanel
const settingsContent = fs.readFileSync(path.resolve(__dirname, '../src/components/panels/SettingsPanel.tsx'), 'utf8');
assert.ok(settingsContent.includes("borderBottom: '1px solid rgba(0, 82, 255, 0.25)'"), 'Settings header must have Electric Cobalt divider');
assert.ok(settingsContent.includes("background: 'rgba(13, 17, 26, 0.85)'"), 'Settings cards must use Midnight Surface');

console.log('  PASS: All 7 secondary drawer panels verified.');

// 6. Electron main.cjs Window and Tray Configuration
console.log('[Test 6] Electron Window Shell & System Tray Configuration');
const mainPath = path.resolve(__dirname, '../electron/main.cjs');
assert.ok(fs.existsSync(mainPath), 'main.cjs must exist');
const mainContent = fs.readFileSync(mainPath, 'utf8');
assert.ok(mainContent.includes("backgroundColor: '#080B10'"), 'BrowserWindow background must be Midnight Black (#080B10)');
assert.ok(mainContent.includes("tray.setToolTip('Phenom 3.0 Cyber Assistant (Windows 11)')"), 'Tray tooltip must reflect Phenom 3.0 Cyber Assistant');
console.log('  PASS: Electron main process window and tray verified.');

console.log('\n=== ALL 6 OVERLAYS & PANELS TESTS PASSED ===');
