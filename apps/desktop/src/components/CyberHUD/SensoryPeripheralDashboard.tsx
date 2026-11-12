import React, { useState } from 'react';
import {
  VideoRegular,
  VideoOffRegular,
  ArrowUploadRegular,
  ArrowDownloadRegular,
  CheckmarkCircleRegular,
  DismissRegular,
  WarningRegular,
  ShieldCheckmarkRegular,
  BatteryChargeRegular,
  DocumentTextRegular,
  EyeRegular,
} from '@fluentui/react-icons';
import {
  CameraStatusPayload,
  MediaDropTransferPayload,
} from '../../types/protocol';

export interface SensoryPeripheralDashboardProps {
  cameraStatus?: CameraStatusPayload;
  activeTransfers?: MediaDropTransferPayload[];
  transferHistory?: MediaDropTransferPayload[];
  onToggleCameraStream?: (enable: boolean) => void;
  onAbortTransfer?: (transferId: string) => void;
  onTriggerAnalysis?: (taskType: 'ocr' | 'whiteboard' | 'object') => void;
  onSendFile?: () => void;
}

export const SensoryPeripheralDashboard: React.FC<SensoryPeripheralDashboardProps> = ({
  cameraStatus,
  activeTransfers = [],
  transferHistory = [],
  onToggleCameraStream,
  onAbortTransfer,
  onTriggerAnalysis,
  onSendFile,
}) => {
  const [selectedTab, setSelectedTab] = useState<'camera' | 'drops'>('camera');

  const isHalted = cameraStatus?.is_halted ?? false;
  const isStreaming = cameraStatus?.is_streaming && !isHalted;
  const batteryPct = cameraStatus?.battery_level !== undefined ? Math.round(cameraStatus.battery_level) : null;
  const wifiRssi = cameraStatus?.wifi_rssi;

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div
      style={{
        background: 'rgba(12, 16, 22, 0.94)',
        border: isHalted ? '1px solid #FF3B30' : '1px solid rgba(0, 255, 204, 0.3)',
        borderRadius: 8,
        padding: 16,
        color: '#E0E6ED',
        fontFamily: 'monospace',
        boxShadow: isHalted
          ? '0 0 16px rgba(255, 59, 48, 0.3)'
          : '0 0 16px rgba(0, 255, 204, 0.1)',
        maxWidth: 720,
        margin: '12px auto',
        backdropFilter: 'blur(10px)',
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          paddingBottom: 10,
          marginBottom: 12,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: isHalted ? '#FF3B30' : isStreaming ? '#00FFCC' : '#FFB800',
              boxShadow: isHalted
                ? '0 0 8px #FF3B30'
                : isStreaming
                ? '0 0 8px #00FFCC'
                : 'none',
            }}
          />
          <span style={{ fontWeight: 'bold', fontSize: 13, letterSpacing: 1 }}>
            SENSORY FABRIC & P2P DROP
          </span>
          {isHalted && (
            <span
              style={{
                fontSize: 10,
                background: 'rgba(255, 59, 48, 0.2)',
                border: '1px solid #FF3B30',
                color: '#FF3B30',
                padding: '2px 6px',
                borderRadius: 4,
                fontWeight: 'bold',
              }}
            >
              GUARDIAN HALTED
            </span>
          )}
        </div>

        {/* Companion Telemetry Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 11, color: '#8899A6' }}>
          {batteryPct !== null && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <BatteryChargeRegular style={{ color: cameraStatus?.is_charging ? '#00FFCC' : '#8899A6' }} />
              <span>{batteryPct}%</span>
            </div>
          )}
          {wifiRssi !== undefined && wifiRssi !== null && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span>RSSI: {wifiRssi} dBm</span>
            </div>
          )}
          {cameraStatus?.node_id && (
            <div style={{ color: '#00FFCC' }}>
              [{cameraStatus.node_id.slice(0, 12)}]
            </div>
          )}
        </div>
      </div>

      {/* Guardian Alert Banner */}
      {isHalted && (
        <div
          style={{
            background: 'rgba(255, 59, 48, 0.15)',
            border: '1px solid rgba(255, 59, 48, 0.5)',
            borderRadius: 6,
            padding: '8px 12px',
            marginBottom: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            color: '#FF7B72',
            fontSize: 11,
          }}
        >
          <WarningRegular />
          <span>Guardian kill switch engaged: Camera frame ingestion and P2P transfers are severed in memory.</span>
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button
          onClick={() => setSelectedTab('camera')}
          style={{
            flex: 1,
            padding: '6px 12px',
            background: selectedTab === 'camera' ? 'rgba(0, 255, 204, 0.15)' : 'rgba(255, 255, 255, 0.05)',
            border: selectedTab === 'camera' ? '1px solid #00FFCC' : '1px solid rgba(255, 255, 255, 0.1)',
            color: selectedTab === 'camera' ? '#00FFCC' : '#8899A6',
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 11,
            fontFamily: 'monospace',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
          }}
        >
          <EyeRegular /> Companion Camera Vision
        </button>
        <button
          onClick={() => setSelectedTab('drops')}
          style={{
            flex: 1,
            padding: '6px 12px',
            background: selectedTab === 'drops' ? 'rgba(0, 255, 204, 0.15)' : 'rgba(255, 255, 255, 0.05)',
            border: selectedTab === 'drops' ? '1px solid #00FFCC' : '1px solid rgba(255, 255, 255, 0.1)',
            color: selectedTab === 'drops' ? '#00FFCC' : '#8899A6',
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 11,
            fontFamily: 'monospace',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
          }}
        >
          <ArrowDownloadRegular /> AirDrop P2P Media ({activeTransfers.length} Active)
        </button>
      </div>

      {/* Tab Content: Camera */}
      {selectedTab === 'camera' && (
        <div>
          {/* Camera Viewfinder Box */}
          <div
            style={{
              position: 'relative',
              width: '100%',
              height: 220,
              background: '#080B0F',
              border: '1px solid rgba(0, 255, 204, 0.2)',
              borderRadius: 6,
              overflow: 'hidden',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 12,
            }}
          >
            {cameraStatus?.thumbnail_base64 && !isHalted ? (
              <img
                src={`data:image/jpeg;base64,${cameraStatus.thumbnail_base64}`}
                alt="Companion View"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            ) : (
              <div style={{ textAlign: 'center', color: '#556677' }}>
                <VideoOffRegular style={{ fontSize: 32, marginBottom: 8 }} />
                <div style={{ fontSize: 11 }}>
                  {isHalted
                    ? 'FEED SEVERED BY GUARDIAN'
                    : cameraStatus?.node_id
                    ? 'STREAM READY - AWAITING FRAMES IN RAM'
                    : 'NO COMPANION CAMERA CONNECTED'}
                </div>
              </div>
            )}

            {/* Viewfinder Crosshair Overlay */}
            <div
              style={{
                position: 'absolute',
                top: 8,
                left: 8,
                fontSize: 10,
                color: '#00FFCC',
                background: 'rgba(0, 0, 0, 0.6)',
                padding: '2px 6px',
                borderRadius: 3,
              }}
            >
              RES: {cameraStatus?.resolution || 'IDLE'} | IN-RAM ONLY
            </div>
            {cameraStatus?.frames_received !== undefined && (
              <div
                style={{
                  position: 'absolute',
                  top: 8,
                  right: 8,
                  fontSize: 10,
                  color: '#8899A6',
                  background: 'rgba(0, 0, 0, 0.6)',
                  padding: '2px 6px',
                  borderRadius: 3,
                }}
              >
                FRAMES: {cameraStatus.frames_received}
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              disabled={isHalted}
              onClick={() => onToggleCameraStream?.(!isStreaming)}
              style={{
                flex: 1,
                padding: '8px 12px',
                background: isStreaming ? 'rgba(255, 59, 48, 0.2)' : 'rgba(0, 255, 204, 0.2)',
                border: isStreaming ? '1px solid #FF3B30' : '1px solid #00FFCC',
                color: isStreaming ? '#FF7B72' : '#00FFCC',
                borderRadius: 4,
                cursor: isHalted ? 'not-allowed' : 'pointer',
                fontFamily: 'monospace',
                fontSize: 11,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
                opacity: isHalted ? 0.4 : 1,
              }}
            >
              {isStreaming ? <VideoOffRegular /> : <VideoRegular />}
              {isStreaming ? 'Stop Camera Stream' : 'Start Camera Stream'}
            </button>

            <button
              disabled={isHalted}
              onClick={() => onTriggerAnalysis?.('ocr')}
              style={{
                padding: '8px 12px',
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                color: '#E0E6ED',
                borderRadius: 4,
                cursor: isHalted ? 'not-allowed' : 'pointer',
                fontFamily: 'monospace',
                fontSize: 11,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                opacity: isHalted ? 0.4 : 1,
              }}
            >
              <DocumentTextRegular /> Scan Document (OCR)
            </button>

            <button
              disabled={isHalted}
              onClick={() => onTriggerAnalysis?.('whiteboard')}
              style={{
                padding: '8px 12px',
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                color: '#E0E6ED',
                borderRadius: 4,
                cursor: isHalted ? 'not-allowed' : 'pointer',
                fontFamily: 'monospace',
                fontSize: 11,
                opacity: isHalted ? 0.4 : 1,
              }}
            >
              Whiteboard Notes
            </button>

            <button
              disabled={isHalted}
              onClick={() => onTriggerAnalysis?.('object')}
              style={{
                padding: '8px 12px',
                background: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                color: '#E0E6ED',
                borderRadius: 4,
                cursor: isHalted ? 'not-allowed' : 'pointer',
                fontFamily: 'monospace',
                fontSize: 11,
                opacity: isHalted ? 0.4 : 1,
              }}
            >
              Inspect Object
            </button>
          </div>
        </div>
      )}

      {/* Tab Content: AirDrop Media Drops */}
      {selectedTab === 'drops' && (
        <div>
          {/* Active Transfers */}
          {activeTransfers.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 11, color: '#00FFCC', fontWeight: 'bold', marginBottom: 8 }}>
                ACTIVE P2P TRANSFERS
              </div>
              {activeTransfers.map((t) => (
                <div
                  key={t.transfer_id}
                  style={{
                    background: 'rgba(0, 0, 0, 0.4)',
                    border: '1px solid rgba(0, 255, 204, 0.2)',
                    borderRadius: 6,
                    padding: 10,
                    marginBottom: 8,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 6 }}>
                    <span style={{ fontWeight: 'bold' }}>{t.filename}</span>
                    <span style={{ color: '#8899A6' }}>
                      {formatFileSize(t.bytes_transferred)} / {formatFileSize(t.file_size)} (
                      {Math.round(t.progress * 100)}%)
                    </span>
                  </div>

                  {/* Progress Bar */}
                  <div
                    style={{
                      height: 4,
                      background: 'rgba(255, 255, 255, 0.1)',
                      borderRadius: 2,
                      overflow: 'hidden',
                      marginBottom: 6,
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        width: `${t.progress * 100}%`,
                        background: '#00FFCC',
                        boxShadow: '0 0 6px #00FFCC',
                      }}
                    />
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 10, color: '#8899A6' }}>
                    <span>
                      {t.direction === 'incoming' ? '📥 Receiving to' : '📤 Sending from'}: {t.destination}/
                    </span>
                    <button
                      onClick={() => onAbortTransfer?.(t.transfer_id)}
                      style={{
                        background: 'transparent',
                        border: '1px solid #FF3B30',
                        color: '#FF7B72',
                        borderRadius: 3,
                        padding: '2px 6px',
                        cursor: 'pointer',
                        fontSize: 10,
                      }}
                    >
                      Abort
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Send File Trigger Button */}
          <div style={{ marginBottom: 14 }}>
            <button
              disabled={isHalted}
              onClick={() => onSendFile?.()}
              style={{
                width: '100%',
                padding: '8px 12px',
                background: 'rgba(0, 255, 204, 0.15)',
                border: '1px dashed #00FFCC',
                color: '#00FFCC',
                borderRadius: 6,
                cursor: isHalted ? 'not-allowed' : 'pointer',
                fontFamily: 'monospace',
                fontSize: 11,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
                opacity: isHalted ? 0.4 : 1,
              }}
            >
              <ArrowUploadRegular /> Send Note or Document to Companion (AirDrop P2P)
            </button>
          </div>

          {/* Recent History */}
          <div>
            <div style={{ fontSize: 11, color: '#8899A6', fontWeight: 'bold', marginBottom: 8 }}>
              RECENT P2P DROPS
            </div>
            {transferHistory.length === 0 ? (
              <div style={{ fontSize: 11, color: '#556677', textAlign: 'center', padding: 12 }}>
                No recent media drops recorded.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {transferHistory.slice(0, 5).map((h) => (
                  <div
                    key={h.transfer_id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid rgba(255, 255, 255, 0.06)',
                      borderRadius: 4,
                      padding: '6px 10px',
                      fontSize: 11,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {h.state === 'completed' ? (
                        <CheckmarkCircleRegular style={{ color: '#00FFCC' }} />
                      ) : h.state === 'aborted' ? (
                        <DismissRegular style={{ color: '#FFB800' }} />
                      ) : (
                        <WarningRegular style={{ color: '#FF3B30' }} />
                      )}
                      <div>
                        <div>{h.filename}</div>
                        <div style={{ fontSize: 9, color: '#667788' }}>
                          {formatFileSize(h.file_size)} • {h.destination}/
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span
                        style={{
                          fontSize: 9,
                          color: '#00FFCC',
                          border: '1px solid rgba(0, 255, 204, 0.3)',
                          padding: '1px 4px',
                          borderRadius: 3,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 2,
                        }}
                      >
                        <ShieldCheckmarkRegular style={{ fontSize: 10 }} /> SHA-256
                      </span>
                      <span
                        style={{
                          fontSize: 10,
                          color:
                            h.state === 'completed'
                              ? '#00FFCC'
                              : h.state === 'aborted'
                              ? '#FFB800'
                              : '#FF3B30',
                          textTransform: 'uppercase',
                        }}
                      >
                        {h.state}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
