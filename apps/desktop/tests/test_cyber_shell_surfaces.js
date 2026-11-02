/**
 * Phenom 3.0: Cyber Shell & App Surfaces Verification Suite
 * Verifies Midnight Black, Electric Cobalt, and Acid Lime styling across HeaderBar, ChatBox,
 * StreamingConsole, CommandPalette, and HUDCard.
 */

const assert = require('assert');
const path = require('path');
const fs = require('fs');

console.log('=== Phenom 3.0: Cyber Shell Surfaces Test Suite ===\n');

// 1. HeaderBar.tsx
console.log('[Test 1] HeaderBar Cyber Styling');
const headerBarPath = path.resolve(__dirname, '../src/components/HeaderBar.tsx');
assert.ok(fs.existsSync(headerBarPath), 'HeaderBar.tsx must exist');
const headerContent = fs.readFileSync(headerBarPath, 'utf8');

assert.ok(headerContent.includes("background: 'rgba(13, 17, 26, 0.82)'"), 'Header must have Midnight surface background');
assert.ok(headerContent.includes('linear-gradient(135deg, #0052FF 0%, #337AFF 50%, #CCFF00 100%)'), 'Header title must have Cobalt-to-Lime gradient');
assert.ok(headerContent.includes("color: isConnected ? '#CCFF00' : '#ef4444'"), 'Online badge must use Acid Lime');
assert.ok(headerContent.includes('CUDA • 8B VRAM'), 'CUDA badge must be present');
console.log('  PASS: HeaderBar cyber glass and telemetry verified.');

// 2. ChatBox.tsx
console.log('[Test 2] ChatBox & Conversation HUD Cyber Styling');
const chatBoxPath = path.resolve(__dirname, '../src/components/ChatBox.tsx');
assert.ok(fs.existsSync(chatBoxPath), 'ChatBox.tsx must exist');
const chatContent = fs.readFileSync(chatBoxPath, 'utf8');

assert.ok(chatContent.includes("background: 'rgba(8, 11, 16, 0.88)'"), 'Conversation HUD must use Midnight Black glass');
assert.ok(chatContent.includes("border: '1px solid rgba(0, 82, 255, 0.28)'"), 'Conversation HUD must have Electric Cobalt border');
assert.ok(chatContent.includes("linear-gradient(135deg, rgba(0, 82, 255, 0.35), rgba(0, 50, 160, 0.50))"), 'User bubble must use Electric Cobalt gradient');
assert.ok(chatContent.includes("'rgba(13, 17, 26, 0.85)'"), 'Assistant bubble must use Midnight Surface');
assert.ok(chatContent.includes("color: '#ccff00'"), 'Streaming indicator must use Acid Lime');
assert.ok(chatContent.includes("background: 'linear-gradient(135deg, #0052FF, #1a66ff)'"), 'Send button must use Electric Cobalt');
console.log('  PASS: ChatBox conversation HUD, bubbles, and streaming indicators verified.');

// 3. StreamingConsole.tsx
console.log('[Test 3] StreamingConsole Cyber Terminal Styling');
const consolePath = path.resolve(__dirname, '../src/components/StreamingConsole.tsx');
assert.ok(fs.existsSync(consolePath), 'StreamingConsole.tsx must exist');
const consoleContent = fs.readFileSync(consolePath, 'utf8');

assert.ok(consoleContent.includes("backgroundColor: 'rgba(8, 11, 16, 0.95)'"), 'Console must use Midnight Black background');
assert.ok(consoleContent.includes("border: '1px solid rgba(0, 82, 255, 0.45)'"), 'Console must have Electric Cobalt border');
assert.ok(consoleContent.includes("color: '#ccff00'"), 'Console header and prompt must use Acid Lime');
console.log('  PASS: StreamingConsole terminal styling verified.');

// 4. CommandPalette.tsx
console.log('[Test 4] CommandPalette Cyber Styling');
const palettePath = path.resolve(__dirname, '../src/components/CommandPalette.tsx');
assert.ok(fs.existsSync(palettePath), 'CommandPalette.tsx must exist');
const paletteContent = fs.readFileSync(palettePath, 'utf8');

assert.ok(paletteContent.includes("backgroundColor: 'rgba(8, 11, 16, 0.95)'"), 'Command palette must use Midnight Black glass');
assert.ok(paletteContent.includes("color: '#0052FF'"), 'Search icon must use Electric Cobalt');
assert.ok(paletteContent.includes("borderLeft: isSelected ? '3px solid #ccff00' : '3px solid transparent'"), 'Selected command must feature Acid Lime accent border');
console.log('  PASS: CommandPalette glass and selection accent verified.');

// 5. HUDCard.tsx
console.log('[Test 5] HUDCard Floating Widget Styling');
const hudCardPath = path.resolve(__dirname, '../src/components/HUDCard.tsx');
assert.ok(fs.existsSync(hudCardPath), 'HUDCard.tsx must exist');
const hudContent = fs.readFileSync(hudCardPath, 'utf8');

assert.ok(hudContent.includes("backgroundColor: 'rgba(8, 11, 16, 0.92)'"), 'HUDCard must use Midnight Black glass');
assert.ok(hudContent.includes("border: '1px solid rgba(0, 82, 255, 0.35)'"), 'HUDCard must have Electric Cobalt border');
assert.ok(hudContent.includes("return '#CCFF00'; // Default Acid Lime"), 'HUDCard default badge must use Acid Lime');
console.log('  PASS: HUDCard glass and badge verified.');

console.log('\nAll 5/5 Cyber Shell surface tests PASSED cleanly!');
