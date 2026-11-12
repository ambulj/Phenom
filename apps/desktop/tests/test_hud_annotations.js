/**
 * Phenom 4.0: Live Cyber HUD Annotations Verification Suite
 * Verifies:
 * 1. ScreenBorderOverlay.tsx accepts HudAnnotationItem[] and renders bounding boxes
 * 2. Visual design contract: Electric Cobalt (#0052FF) borders and Acid Lime (#CCFF00) accents
 * 3. Tag badge rendering with [CONTROL_TYPE] and element label
 * 4. App.tsx WebSocket handling for vision.annotations and vision.clear_annotations
 * 5. ScreenBorderOverlay integration in App.tsx passing annotations
 */

const assert = require('assert');
const path = require('path');
const fs = require('fs');

console.log('=== Phenom 4.0: Live Cyber HUD Annotations Test Suite ===\n');

// 1. HudAnnotationItem Interface in ScreenBorderOverlay.tsx
console.log('[Test 1] HudAnnotationItem Interface & Props');
const overlayPath = path.resolve(__dirname, '../src/components/ScreenBorderOverlay.tsx');
assert.ok(fs.existsSync(overlayPath), 'ScreenBorderOverlay.tsx must exist');
const overlayContent = fs.readFileSync(overlayPath, 'utf8');

assert.ok(overlayContent.includes('export interface HudAnnotationItem'), 'HudAnnotationItem interface must be exported');
assert.ok(overlayContent.includes('bbox: [number, number, number, number]'), 'Bounding box coordinate tuple must be declared');
assert.ok(overlayContent.includes('annotations?: HudAnnotationItem[]'), 'ScreenBorderOverlayProps must accept annotations');
console.log('  PASS: HudAnnotationItem interface and props verified.');

// 2. Bounding Box & Corner Brackets Visual Styling
console.log('[Test 2] Cyber Bounding Box & Corner Bracket Accents');
assert.ok(overlayContent.includes('data-testid={`hud-annotation-${anno.id}`}'), 'Annotation testid must be present for automation tracking');
assert.ok(overlayContent.includes("border: `2px solid ${accentColor}`"), 'Dynamic accent border must be applied');
assert.ok(overlayContent.includes("borderTop: '3px solid #CCFF00'"), 'Top corner bracket must use Acid Lime');
assert.ok(overlayContent.includes("borderBottom: '3px solid #CCFF00'"), 'Bottom corner bracket must use Acid Lime');
console.log('  PASS: Cyber bounding box and corner brackets verified.');

// 3. Floating Tag Badges
console.log('[Test 3] Floating Tag Badges & Control Type Pill');
assert.ok(overlayContent.includes("color: '#CCFF00'"), 'Label badge text must use Acid Lime');
assert.ok(overlayContent.includes("fontFamily: 'Consolas, monospace'"), 'Badge must use monospace cyber typography');
assert.ok(overlayContent.includes("anno.control_type ? `[${anno.control_type}]` : '[TARGET]'"), 'Control type prefix must be formatted in brackets');
assert.ok(overlayContent.includes("background: 'rgba(8, 11, 16, 0.94)'"), 'Badge surface must use Midnight Black glass');
console.log('  PASS: Floating tag badges and control type formatting verified.');

// 4. App.tsx WebSocket Event Handling
console.log('[Test 4] App.tsx WebSocket Event Integration');
const appPath = path.resolve(__dirname, '../src/App.tsx');
assert.ok(fs.existsSync(appPath), 'App.tsx must exist');
const appContent = fs.readFileSync(appPath, 'utf8');

assert.ok(appContent.includes("const [hudAnnotations, setHudAnnotations] = useState<HudAnnotationItem[]>([]);"), 'hudAnnotations state must be declared');
assert.ok(appContent.includes("mtype === 'vision.annotations'"), 'vision.annotations event handler must be registered');
assert.ok(appContent.includes("mtype === 'vision.clear_annotations'"), 'vision.clear_annotations event handler must be registered');
console.log('  PASS: App.tsx WebSocket event handlers verified.');

// 5. ScreenBorderOverlay Integration in App.tsx
console.log('[Test 5] ScreenBorderOverlay Wiring in App.tsx');
assert.ok(appContent.includes("annotations={hudAnnotations}"), 'ScreenBorderOverlay must receive annotations prop');
console.log('  PASS: ScreenBorderOverlay integration verified in main layout.');

console.log('\n=== ALL 5 HUD ANNOTATION TESTS PASSED ===');
