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

function detectPythonCommand() {
  const path = require('path');
  const fs = require('fs');
  const venvCandidates = [
    path.resolve(__dirname, '../../../.venv-clean/Scripts/python.exe'),
    path.resolve(__dirname, '../../../.venv/Scripts/python.exe'),
    'C:\\Phenom\\.venv-clean\\Scripts\\python.exe',
    'C:\\Phenom\\.venv\\Scripts\\python.exe'
  ];

  const candidates = [];
  for (const venvPath of venvCandidates) {
    if (fs.existsSync(venvPath)) {
      candidates.push({ cmd: venvPath, args: ['--version'], execArgs: [] });
    }
  }
  candidates.push(
    { cmd: 'python', args: ['--version'], execArgs: [] },
    { cmd: 'py', args: ['-3.11', '--version'], execArgs: ['-3.11'] },
    { cmd: 'py', args: ['--version'], execArgs: [] },
    { cmd: 'python3', args: ['--version'], execArgs: [] }
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
          version: parsed
        };
      }
    } catch {
      // candidate not executable
    }
  }
  return null;
}

module.exports = { parsePythonVersion, detectPythonCommand };
