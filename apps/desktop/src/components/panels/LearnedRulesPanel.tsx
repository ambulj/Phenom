import React, { useState } from 'react';
import { Button, Input } from '@fluentui/react-components';
import { DismissRegular, DeleteRegular, EditRegular, CheckmarkRegular } from '@fluentui/react-icons';
import { LearnedRuleItem } from '../../types/protocol';

interface LearnedRulesPanelProps {
  onClose: () => void;
  rules: LearnedRuleItem[];
  onDeleteRule: (id: string) => void;
  onEditRule: (id: string, text: string) => void;
}

export const LearnedRulesPanel: React.FC<LearnedRulesPanelProps> = ({
  onClose,
  rules,
  onDeleteRule,
  onEditRule
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  const handleStartEdit = (rule: LearnedRuleItem) => {
    setEditingId(rule.id);
    setEditText(rule.rule_text);
  };

  const handleSaveEdit = (id: string) => {
    if (editText.trim()) {
      onEditRule(id, editText.trim());
    }
    setEditingId(null);
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingBottom: 16,
          borderBottom: '1px solid rgba(0, 82, 255, 0.25)'
        }}
      >
        <h2 style={{ fontSize: 16, fontWeight: 600, color: '#f8fafc', margin: 0 }}>Learned Rules</h2>
        <Button appearance="subtle" icon={<DismissRegular />} onClick={onClose} />
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingTop: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
        {rules.length === 0 ? (
          <div style={{ color: '#64748b', fontSize: 14 }}>
            No learned rules recorded yet. Phenom automatically extracts rules when you state preferences.
          </div>
        ) : (
          rules.map((r) => (
            <div
              key={r.id}
              style={{
                background: 'rgba(13, 17, 26, 0.85)',
                border: '1px solid rgba(0, 82, 255, 0.22)',
                borderRadius: 8,
                padding: '12px 14px',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.4)'
              }}
            >
              {editingId === r.id ? (
                <div style={{ display: 'flex', gap: 8 }}>
                  <Input
                    value={editText}
                    onChange={(_, d) => setEditText(d.value)}
                    style={{ flex: 1 }}
                  />
                  <Button
                    appearance="primary"
                    icon={<CheckmarkRegular />}
                    onClick={() => handleSaveEdit(r.id)}
                    style={{ background: '#CCFF00', color: '#080B10', fontWeight: 600 }}
                  />
                  <Button
                    appearance="subtle"
                    icon={<DismissRegular />}
                    onClick={() => setEditingId(null)}
                  />
                </div>
              ) : (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 14, color: '#f8fafc', flex: 1 }}>{r.rule_text}</span>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <Button
                      appearance="subtle"
                      icon={<EditRegular />}
                      size="small"
                      onClick={() => handleStartEdit(r)}
                    />
                    <Button
                      appearance="subtle"
                      icon={<DeleteRegular />}
                      size="small"
                      onClick={() => onDeleteRule(r.id)}
                    />
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
