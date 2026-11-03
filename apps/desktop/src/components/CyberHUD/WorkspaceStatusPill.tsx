import React, { useState } from 'react';
import { CodeRegular, BranchRegular, DismissRegular, LockClosedRegular } from '@fluentui/react-icons';
import { DeveloperWorkspaceState } from '../../types/workspace';

interface WorkspaceStatusPillProps {
  workspace: DeveloperWorkspaceState | null;
}

export const WorkspaceStatusPill: React.FC<WorkspaceStatusPillProps> = ({ workspace }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!workspace) {
    return null;
  }

  const isDirty = workspace.is_dirty;
  const isGit = workspace.is_git;

  // Badge label formatting
  const branchLabel = isGit ? (workspace.branch || 'detached') : workspace.name;
  const diffLabel = isGit
    ? `+${workspace.lines_added} -${workspace.lines_deleted}`
    : 'folder';

  const badgeColor = !isGit
    ? 'rgba(140, 150, 170, 0.2)'
    : isDirty
    ? 'rgba(204, 255, 0, 0.12)'
    : 'rgba(0, 82, 255, 0.12)';

  const borderColor = !isGit
    ? 'rgba(140, 150, 170, 0.4)'
    : isDirty
    ? '#CCFF00'
    : 'rgba(0, 82, 255, 0.4)';

  const textColor = !isGit
    ? '#b0b8c8'
    : isDirty
    ? '#CCFF00'
    : '#80b8ff';

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          background: badgeColor,
          border: `1px solid ${borderColor}`,
          color: textColor,
          borderRadius: 6,
          padding: '3px 8px',
          fontSize: 11,
          fontFamily: 'monospace',
          cursor: 'pointer',
          outline: 'none',
          boxShadow: isDirty ? '0 0 8px rgba(204, 255, 0, 0.2)' : 'none',
          transition: 'all 0.2s ease',
        }}
        title={`Workspace: ${workspace.name} (${workspace.ide_name.toUpperCase()})\nClick to view git diffs`}
      >
        {isGit ? <BranchRegular style={{ fontSize: 13 }} /> : <CodeRegular style={{ fontSize: 13 }} />}
        <span style={{ fontWeight: 600 }}>{branchLabel}</span>
        <span style={{ opacity: 0.85 }}>•</span>
        <span>{diffLabel}</span>
        {workspace.is_private && <LockClosedRegular style={{ fontSize: 11, color: '#f59e0b' }} />}
      </button>

      {/* Popover Card */}
      {isOpen && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 8px)',
            left: 0,
            width: 320,
            background: '#0d1117',
            border: '1px solid rgba(0, 82, 255, 0.4)',
            borderRadius: 8,
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.6), 0 0 12px rgba(0, 82, 255, 0.2)',
            zIndex: 1000,
            padding: 12,
            fontFamily: 'system-ui, -apple-system, sans-serif',
            color: '#e6edf3',
          }}
        >
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, borderBottom: '1px solid #21262d', paddingBottom: 6 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontWeight: 600, fontSize: 12, color: '#58a6ff' }}>{workspace.name}</span>
              <span style={{ fontSize: 10, background: '#21262d', padding: '1px 5px', borderRadius: 4, textTransform: 'uppercase', color: '#8b949e' }}>
                {workspace.ide_name}
              </span>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              style={{ background: 'transparent', border: 'none', color: '#8b949e', cursor: 'pointer', padding: 2 }}
            >
              <DismissRegular style={{ fontSize: 14 }} />
            </button>
          </div>

          {/* Path & Stats */}
          <div style={{ fontSize: 10, color: '#8b949e', marginBottom: 8, wordBreak: 'break-all', fontFamily: 'monospace' }}>
            {workspace.root_path}
          </div>

          <div style={{ display: 'flex', gap: 12, fontSize: 11, marginBottom: 8, background: '#161b22', padding: '6px 8px', borderRadius: 6 }}>
            <div>
              <span style={{ color: '#8b949e' }}>Branch: </span>
              <span style={{ fontWeight: 600, color: '#58a6ff' }}>{workspace.branch || 'None'}</span>
            </div>
            <div>
              <span style={{ color: '#3fb950' }}>+{workspace.lines_added}</span> / <span style={{ color: '#f85149' }}>-{workspace.lines_deleted}</span>
            </div>
          </div>

          {/* Changed Files */}
          <div style={{ maxHeight: 180, overflowY: 'auto' }}>
            {workspace.modified_files.length === 0 ? (
              <div style={{ fontSize: 11, color: '#8b949e', textAlign: 'center', padding: '12px 0' }}>
                Worktree is clean
              </div>
            ) : (
              workspace.modified_files.map((file, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: 11,
                    padding: '4px 6px',
                    borderRadius: 4,
                    background: idx % 2 === 0 ? 'transparent' : 'rgba(255, 255, 255, 0.02)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <span
                      style={{
                        fontSize: 9,
                        fontFamily: 'monospace',
                        fontWeight: 700,
                        padding: '1px 3px',
                        borderRadius: 3,
                        background: file.status.includes('?') ? '#8b949e' : file.status.includes('M') ? '#d29922' : '#238636',
                        color: '#0d1117',
                      }}
                    >
                      {file.status}
                    </span>
                    <span
                      style={{
                        fontFamily: 'monospace',
                        fontSize: 10,
                        color: file.is_secret ? '#f85149' : '#c9d1d9',
                      }}
                      title={file.path}
                    >
                      {file.path}
                    </span>
                  </div>
                  <div style={{ fontSize: 10, fontFamily: 'monospace', flexShrink: 0, marginLeft: 6 }}>
                    {file.lines_added > 0 && <span style={{ color: '#3fb950' }}>+{file.lines_added} </span>}
                    {file.lines_deleted > 0 && <span style={{ color: '#f85149' }}>-{file.lines_deleted}</span>}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
