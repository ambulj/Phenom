const assert = require('assert');
const { parsePythonVersion, detectPythonCommand } = require('./electron/pythonVersion.cjs');

console.log('Testing Python Version Guard and Parser Logic...');

// 1. Rejects older versions (< 3.11)
const v310 = parsePythonVersion('Python 3.10.12');
assert.strictEqual(v310.major, 3);
assert.strictEqual(v310.minor, 10);
assert.strictEqual(v310.isSupported, false, 'Python 3.10 must be rejected');

const v27 = parsePythonVersion('Python 2.7.18');
assert.strictEqual(v27.isSupported, false, 'Python 2.7 must be rejected');

const v39 = parsePythonVersion('Python 3.9.5');
assert.strictEqual(v39.isSupported, false, 'Python 3.9 must be rejected');

// 2. Accepts supported versions (>= 3.11)
const v3110 = parsePythonVersion('Python 3.11.0');
assert.strictEqual(v3110.isSupported, true, 'Python 3.11.0 must be accepted');

const v3119 = parsePythonVersion('Python 3.11.9');
assert.strictEqual(v3119.isSupported, true, 'Python 3.11.9 must be accepted');

const v312 = parsePythonVersion('Python 3.12.4');
assert.strictEqual(v312.isSupported, true, 'Python 3.12 must be accepted');

// 3. Handles empty or malformed strings gracefully
assert.strictEqual(parsePythonVersion(''), null);
assert.strictEqual(parsePythonVersion('Not python at all'), null);

// 4. Detects local system Python
const detected = detectPythonCommand();
assert.ok(detected, 'Local Python 3.11+ must be detected');
assert.ok(detected.version.isSupported, 'Detected Python must be >= 3.11');

console.log(`PASS: All Python version guard tests passed! Detected: ${detected.cmd} ${detected.execArgs.join(' ')} (${detected.version.raw})`);
