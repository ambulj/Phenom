import React, { useState } from 'react';
import { SparkleRegular, DocumentRegular } from '@fluentui/react-icons';

export const OrbWindow: React.FC = () => {
  const [isHovered, setIsHovered] = useState(false);
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [droppedFileName, setDroppedFileName] = useState<string | null>(null);

  // Hover-to-solid and idle click-through (Task 6E.1)
  const handleMouseEnter = () => {
    setIsHovered(true);
    if ((window as any).phenom?.setIgnoreMouseEvents) {
      (window as any).phenom.setIgnoreMouseEvents(false);
    }
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    setIsDraggingFile(false);
    if ((window as any).phenom?.setIgnoreMouseEvents) {
      (window as any).phenom.setIgnoreMouseEvents(true, { forward: true });
    }
  };

  // Drag-and-drop onto click-through window fallback / handler (Task 6E.1 & 6E.2)
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDraggingFile) setIsDraggingFile(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingFile(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingFile(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      const filePath = (file as any).path || file.name;
      setDroppedFileName(file.name);

      // Send to main window for local-only summarization
      if ((window as any).phenom?.sendOrbFileDrop) {
        (window as any).phenom.sendOrbFileDrop(filePath);
      }
      setTimeout(() => setDroppedFileName(null), 3000);
    }
  };

  const handleDoubleClick = () => {
    if ((window as any).phenom?.toggleMainWindow) {
      (window as any).phenom.toggleMainWindow();
    }
  };

  // Check prefers-reduced-motion
  const prefersReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  return (
    <div
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onDoubleClick={handleDoubleClick}
      style={{
        width: '100vw',
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'transparent',
        overflow: 'hidden',
        userSelect: 'none',
        cursor: isHovered ? 'pointer' : 'default',
      }}
      title="Phenom Floating Orb (Double-click to toggle HUD, Drop file for local summary)"
    >
      {/* 3D Particle Holographic Orb Core */}
      <div
        style={{
          width: 130,
          height: 130,
          borderRadius: '50%',
          background: isDraggingFile
            ? 'radial-gradient(circle, rgba(204, 255, 0, 0.4) 0%, rgba(0, 229, 255, 0.2) 60%, transparent 100%)'
            : isHovered
            ? 'radial-gradient(circle, rgba(0, 229, 255, 0.35) 0%, rgba(0, 82, 255, 0.25) 50%, transparent 100%)'
            : 'radial-gradient(circle, rgba(0, 229, 255, 0.25) 0%, rgba(0, 82, 255, 0.15) 50%, transparent 100%)',
          border: isDraggingFile
            ? '2px dashed #ccff00'
            : isHovered
            ? '2px solid #00e5ff'
            : '1px solid rgba(0, 229, 255, 0.4)',
          boxShadow: isDraggingFile
            ? '0 0 25px rgba(204, 255, 0, 0.6)'
            : '0 0 20px rgba(0, 229, 255, 0.4), inset 0 0 15px rgba(0, 82, 255, 0.3)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          transition: prefersReducedMotion ? 'none' : 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          transform: isHovered && !prefersReducedMotion ? 'scale(1.05)' : 'scale(1)',
          position: 'relative',
        }}
      >
        {/* Subtle breathing pulse ring */}
        {!prefersReducedMotion && (
          <div
            style={{
              position: 'absolute',
              width: '100%',
              height: '100%',
              borderRadius: '50%',
              border: '1px solid rgba(0, 229, 255, 0.3)',
              animation: 'pulse 2.5s infinite',
              pointerEvents: 'none',
            }}
          />
        )}

        {isDraggingFile ? (
          <>
            <DocumentRegular style={{ fontSize: 28, color: '#ccff00' }} />
            <span style={{ fontSize: 10, fontWeight: 700, color: '#ccff00', marginTop: 4 }}>
              DROP FOR LOCAL SUMMARY
            </span>
          </>
        ) : droppedFileName ? (
          <span style={{ fontSize: 10, fontWeight: 700, color: '#00e5ff', textAlign: 'center', padding: '0 8px' }}>
            {droppedFileName}
          </span>
        ) : (
          <>
            <SparkleRegular style={{ fontSize: 26, color: '#00e5ff' }} />
            <span
              style={{
                fontSize: 10,
                fontWeight: 700,
                color: '#f8fafc',
                letterSpacing: '0.8px',
                marginTop: 2,
                textTransform: 'uppercase',
              }}
            >
              Phenom
            </span>
            {isHovered && (
              <span style={{ fontSize: 9, color: '#94a3b8', marginTop: 2 }}>
                Click to Summon
              </span>
            )}
          </>
        )}
      </div>
    </div>
  );
};
