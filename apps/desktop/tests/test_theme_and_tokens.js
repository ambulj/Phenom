/**
 * Phenom 3.0: Theme & Token Verification Suite
 * Verifies Midnight Black, Electric Cobalt, and Acid Lime theme tokens and Fluent UI configuration.
 */

const assert = require('assert');
const path = require('path');
const fs = require('fs');

console.log('=== Phenom 3.0: Theme & Design Tokens Test Suite ===\n');

// 1. Verify theme.css
console.log('[Test 1] CSS Design Tokens in theme.css');
const themeCssPath = path.resolve(__dirname, '../src/theme.css');
assert.ok(fs.existsSync(themeCssPath), 'theme.css must exist');
const cssContent = fs.readFileSync(themeCssPath, 'utf8');

const expectedTokens = [
  '--color-bg-base: #080b10',
  '--color-cobalt-primary: #0052ff',
  '--color-lime-accent: #ccff00',
  '--color-cobalt-glow',
  '--color-lime-glow',
  '--glass-backdrop-blur: blur(16px)',
  '--glass-border'
];

for (const token of expectedTokens) {
  assert.ok(
    cssContent.includes(token),
    `theme.css must include definition for ${token}`
  );
}
console.log('  PASS: All core Midnight Black, Electric Cobalt, and Acid Lime CSS tokens defined.');

// 2. Verify theme.ts Structure & Ramp
console.log('[Test 2] Fluent UI Theme Ramp & Overrides in theme.ts');
const themeTsPath = path.resolve(__dirname, '../src/theme.ts');
assert.ok(fs.existsSync(themeTsPath), 'theme.ts must exist');
const tsContent = fs.readFileSync(themeTsPath, 'utf8');

// Check Cobalt Brand Ramp 10 to 160
const rampLevels = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160];
for (const level of rampLevels) {
  assert.ok(
    tsContent.includes(`${level}:`),
    `cobaltBrandRamp must contain variant level ${level}`
  );
}
assert.ok(tsContent.includes("70: '#0052ff'"), 'Brand ramp level 70 must be base Electric Cobalt (#0052ff)');
assert.ok(tsContent.includes("colorNeutralBackground1: '#080B10'"), 'Neutral background must be Midnight Black (#080B10)');
assert.ok(tsContent.includes("colorBrandBackground: '#0052FF'"), 'Brand background must be Electric Cobalt (#0052FF)');
assert.ok(tsContent.includes("colorStrokeFocus2: '#CCFF00'"), 'Focus stroke must be Acid Lime (#CCFF00)');
console.log('  PASS: Cobalt brand ramp (16 levels) and Fluent UI overrides verified.');

// 3. Verify main.tsx Integration
console.log('[Test 3] FluentProvider Mounting in main.tsx');
const mainTsxPath = path.resolve(__dirname, '../src/main.tsx');
const mainTsx = fs.readFileSync(mainTsxPath, 'utf8');

assert.ok(mainTsx.includes("import './theme.css';"), 'main.tsx must import theme.css');
assert.ok(mainTsx.includes("import { phenomCyberTheme } from './theme';"), 'main.tsx must import phenomCyberTheme');
assert.ok(mainTsx.includes('<FluentProvider theme={phenomCyberTheme}>'), 'FluentProvider must use phenomCyberTheme');
console.log('  PASS: Custom theme engine mounted in root FluentProvider.');

// 4. Verify index.html Styling
console.log('[Test 4] Root HTML Background Color');
const htmlPath = path.resolve(__dirname, '../index.html');
const htmlContent = fs.readFileSync(htmlPath, 'utf8');
assert.ok(htmlContent.includes('background-color: #080b10;'), 'HTML body background must be Midnight Black (#080b10)');
console.log('  PASS: index.html body background updated to Midnight Black.');

console.log('\nAll 4/4 Theme & Design Token tests PASSED cleanly!');
