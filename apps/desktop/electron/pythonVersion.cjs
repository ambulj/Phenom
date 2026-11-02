const { spawnSync } = require('child_process');

function parsePythonVersion(versionStr) {
  if (!versionStr) return null;
  const match = versionStr.trim().match(/Python\s+([0-9]+)\.([0-9]+)(?:\.([0-9]+))?/i);
  if (!match) return null;
  const major = parseInt(match[1], 10);
  const minor = parseInt(match[2], 10);
  const patch = match[3] ? parseInt(match[3], 10) : 0;
  const isSupported = major > 3 || (major === 3 && minor >= 11);
  return { major, minor, patch, isSupported, raw: versionStr.trim() };
}

function detectPythonCommand(overrideResourcesPath = null) {
  const path = require('path');
  const fs = require('fs');

  const resPath = overrideResourcesPath || process.resourcesPath || '';

  // 1. Packaged standalone/embedded Python runtime candidates (highest priority in production)
  const packagedCandidates = [
    path.join(resPath, 'runtime', 'Scripts', 'python.exe'),
    path.join(resPath, 'runtime', 'python.exe'),
    path.join(resPath, 'python', 'python.exe'),
    path.join(resPath, '.venv-clean', 'Scripts', 'python.exe'),
    path.join(resPath, '.venv', 'Scripts', 'python.exe')
  ];

  // 2. Development virtual environment candidates
  const devVenvCandidates = [
    path.resolve(__dirname, '../../../.venv-clean/Scripts/python.exe'),
    path.resolve(__dirname, '../../../.venv/Scripts/python.exe'),
    'C:\\Phenom\\.venv-clean\\Scripts\\python.exe',
    'C:\\Phenom\\.venv\\Scripts\\python.exe'
  ];

  const candidates = [];

  // Add existing packaged candidates
  for (const p of packagedCandidates) {
    if (p && fs.existsSync(p)) {
      candidates.push({ cmd: p, args: ['--version'], execArgs: [], source: 'packaged_runtime' });
    }
  }

  // Add existing dev venvs
  for (const venvPath of devVenvCandidates) {
    if (fs.existsSync(venvPath)) {
      candidates.push({ cmd: venvPath, args: ['--version'], execArgs: [], source: 'dev_venv' });
    }
  }

  // 3. System installed Python binaries
  candidates.push(
    { cmd: 'python', args: ['--version'], execArgs: [], source: 'system' },
    { cmd: 'py', args: ['-3.11', '--version'], execArgs: ['-3.11'], source: 'system' },
    { cmd: 'py', args: ['--version'], execArgs: [], source: 'system' },
    { cmd: 'python3', args: ['--version'], execArgs: [], source: 'system' }
  );

  for (const candidate of candidates) {
    try {
      const res = spawnSync(candidate.cmd, candidate.args, { encoding: 'utf-8', windowsHide: true });
      const output = ((res.stdout || '') + (res.stderr || '')).trim();
      const parsed = parsePythonVersion(output);
      if (parsed && parsed.isSupported) {
        return {
          cmd: candidate.cmd,
          execArgs: candidate.execArgs,
          version: parsed,
          source: candidate.source
        };
      }
    } catch {
      // candidate not executable
    }
  }
  return null;
}

module.exports = { parsePythonVersion, detectPythonCommand };
