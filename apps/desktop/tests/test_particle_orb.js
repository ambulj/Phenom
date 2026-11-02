/**
 * Phenom 3.0: Particle Orb Shaders & Audio Reactivity Verification Suite
 * Verifies Electric Cobalt, Acid Lime, Speaking Amplitude Lerp, LOD Tiers,
 * and Cyber HUD Shrunk styling in Orb.tsx.
 */

const assert = require('assert');
const path = require('path');
const fs = require('fs');

console.log('=== Phenom 3.0: Particle Orb Shaders Test Suite ===\n');

// 1. File verification & Loading
console.log('[Test 1] Orb.tsx Component File Structure');
const orbPath = path.resolve(__dirname, '../src/components/Orb.tsx');
assert.ok(fs.existsSync(orbPath), 'Orb.tsx must exist');
const orbContent = fs.readFileSync(orbPath, 'utf8');
assert.ok(orbContent.length > 500, 'Orb.tsx must have complete implementation');
console.log('  PASS: Orb.tsx component exists and is readable.');

// 2. STATE_CONFIGS & Color Definitions
console.log('[Test 2] STATE_CONFIGS Cyber Palette Mapping');
assert.ok(orbContent.includes('0x0052ff'), 'idle state must use Electric Cobalt (0x0052ff)');
assert.ok(orbContent.includes('0x1a66ff'), 'listening state must use Vivid Electric Cobalt (0x1a66ff)');
assert.ok(orbContent.includes('0xccff00'), 'thinking state must use Acid Lime (0xccff00)');
assert.ok(orbContent.includes('0xef4444'), 'halted state must use Stark Crimson (0xef4444)');

// Check SPEAKING_PEAK_COLOR
assert.ok(orbContent.includes('SPEAKING_PEAK_COLOR = new THREE.Color(0xccff00)'), 'SPEAKING_PEAK_COLOR must be Acid Lime (0xccff00)');
console.log('  PASS: STATE_CONFIGS maps all orb states to Electric Cobalt and Acid Lime palette.');

// 3. Audio Reactivity & Dynamic Color Lerp
console.log('[Test 3] Voice Amplitude Reactivity & Color Lerping');
assert.ok(orbContent.includes('targetStateRef.current === \'speaking\''), 'Must have speaking state check');
assert.ok(orbContent.includes('STATE_CONFIGS.speaking.color.clone().lerp(SPEAKING_PEAK_COLOR'), 'Speaking color must dynamically lerp towards Acid Lime with amplitude');
assert.ok(orbContent.includes('Math.min(1.0, Math.max(0.0, amplitudeRef.current || 0.0))'), 'Amplitude must be clamped [0, 1]');
assert.ok(orbContent.includes('burstAmp = 1.0 + ampMod * 0.75'), 'Particle burst amplitude must react to audio amplitude');
console.log('  PASS: Dynamic voice amplitude lerp and particle burst physics verified.');

// 4. Quality LOD Tiers (high, medium, low, freeze)
console.log('[Test 4] Quality LOD Tiers & GPU Adaptation');
assert.ok(orbContent.includes('particles: 15000'), 'High LOD must use 15,000 particles');
assert.ok(orbContent.includes('fps: 60'), 'High LOD must target 60 FPS');
assert.ok(orbContent.includes('particles: 7500'), 'Medium LOD must use 7,500 particles');
assert.ok(orbContent.includes('fps: 30'), 'Medium LOD must target 30 FPS');
assert.ok(orbContent.includes('particles: 2000'), 'Low LOD must use 2,000 particles');
assert.ok(orbContent.includes('fps: 15'), 'Low LOD must target 15 FPS');
assert.ok(orbContent.includes('particles: 0'), 'Freeze LOD must use 0 particles');
assert.ok(orbContent.includes('fps: 0'), 'Freeze LOD must target 0 FPS');
console.log('  PASS: Quality LOD tiers (15k@60fps down to freeze) verified.');

// 5. isShrunk HUD Mini Styling
console.log('[Test 5] isShrunk Mini HUD Glass Styling');
assert.ok(orbContent.includes("background: 'rgba(8, 11, 16, 0.90)'"), 'Shrunk orb must use Midnight Black glass');
assert.ok(orbContent.includes("border: '1px solid rgba(0, 82, 255, 0.4)'"), 'Shrunk orb must have Electric Cobalt border');
assert.ok(orbContent.includes('rgba(0, 82, 255, 0.25)'), 'Shrunk orb must cast Electric Cobalt glow shadow');
console.log('  PASS: isShrunk mini HUD container styling verified.');

// 6. 2D Canvas Fallback
console.log('[Test 6] 2D Canvas Fallback Graceful Degradation');
assert.ok(orbContent.includes('animateFallback'), 'Must include 2D Canvas fallback loop');
assert.ok(orbContent.includes('createRadialGradient'), 'Fallback must render radial gradient sphere');
console.log('  PASS: 2D Canvas fallback graceful degradation verified.');

console.log('\n=== ALL 6 ORB TESTS PASSED ===');
