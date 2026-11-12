import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

export type OrbEmotion = 'urgent' | 'focused' | 'chill' | 'idle' | 'speaking' | 'halted';
export type OrbQualityLevel = 'high' | 'medium' | 'low' | 'freeze';

export interface FrequencyBands {
  bass: number;    // 20 - 250 Hz (radius dilation)
  mid: number;     // 250 - 2000 Hz (surface turbulence)
  treble: number;  // 2000 - 16000 Hz (glitter dispersion)
  overall: number; // 0.0 to 1.0
}

interface ParticleOrbProps {
  emotion?: OrbEmotion;
  frequencyBands?: FrequencyBands;
  qualityLevel?: OrbQualityLevel;
  isHalted?: boolean;
  width?: number;
  height?: number;
}

export const MAX_PARTICLE_COUNT = 15000;

export const QUALITY_CONFIGS: Record<OrbQualityLevel, { particles: number; fps: number; speedFactor: number }> = {
  high: { particles: 15000, fps: 60, speedFactor: 1.0 },
  medium: { particles: 7500, fps: 30, speedFactor: 0.8 },
  low: { particles: 2500, fps: 20, speedFactor: 0.5 },
  freeze: { particles: 0, fps: 0, speedFactor: 0.0 }
};

export const EMOTION_THEMES: Record<OrbEmotion, {
  color: THREE.Color;
  peakColor: THREE.Color;
  speed: number;
  dispersion: number;
  brightness: number;
}> = {
  urgent: {
    color: new THREE.Color(0xef4444),     // Stark Crimson (#EF4444)
    peakColor: new THREE.Color(0xff8888),
    speed: 3.2,
    dispersion: 1.6,
    brightness: 1.3
  },
  focused: {
    color: new THREE.Color(0x00e5ff),    // Electric Cyan (#00E5FF)
    peakColor: new THREE.Color(0x80f2ff),
    speed: 1.5,
    dispersion: 1.1,
    brightness: 1.1
  },
  chill: {
    color: new THREE.Color(0xa855f7),      // Neon Violet (#A855F7)
    peakColor: new THREE.Color(0xd8b4fe),
    speed: 0.35,
    dispersion: 0.8,
    brightness: 0.75
  },
  idle: {
    color: new THREE.Color(0xffb300),      // Cyber Gold (#FFB300)
    peakColor: new THREE.Color(0xffe082),
    speed: 0.45,
    dispersion: 0.95,
    brightness: 0.9
  },
  speaking: {
    color: new THREE.Color(0x0052ff),      // Electric Cobalt (#0052FF)
    peakColor: new THREE.Color(0xccff00),  // Acid Lime (#CCFF00) peaks
    speed: 2.4,
    dispersion: 1.45,
    brightness: 1.2
  },
  halted: {
    color: new THREE.Color(0xef4444),      // Stark Crimson (#EF4444)
    peakColor: new THREE.Color(0x7f1d1d),
    speed: 0.0,
    dispersion: 0.5,
    brightness: 0.35
  }
};

export const ParticleOrb: React.FC<ParticleOrbProps> = ({
  emotion = 'idle',
  frequencyBands = { bass: 0, mid: 0, treble: 0, overall: 0 },
  qualityLevel = 'high',
  isHalted = false,
  width = 460,
  height = 360
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const emotionRef = useRef<OrbEmotion>(isHalted ? 'halted' : emotion);
  const freqRef = useRef<FrequencyBands>(frequencyBands);
  const qualityRef = useRef<OrbQualityLevel>(qualityLevel);
  const haltedRef = useRef<boolean>(isHalted);

  useEffect(() => {
    emotionRef.current = isHalted ? 'halted' : emotion;
  }, [emotion, isHalted]);

  useEffect(() => {
    freqRef.current = frequencyBands;
  }, [frequencyBands]);

  useEffect(() => {
    qualityRef.current = qualityLevel;
  }, [qualityLevel]);

  useEffect(() => {
    haltedRef.current = isHalted;
  }, [isHalted]);

  useEffect(() => {
    if (!containerRef.current) return;
    const container = containerRef.current;
    const actualWidth = width;
    const actualHeight = height;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, actualWidth / actualHeight, 0.1, 1000);
    camera.position.z = 230;

    let renderer: THREE.WebGLRenderer | null = null;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    } catch {
      try {
        renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true });
      } catch (e) {
        console.warn('WebGL initialization failed for ParticleOrb:', e);
      }
    }

    if (!renderer) return;

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(actualWidth, actualHeight);
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Particle Geometry (15,000 points)
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(MAX_PARTICLE_COUNT * 3);
    const basePositions = new Float32Array(MAX_PARTICLE_COUNT * 3);
    const angles = new Float32Array(MAX_PARTICLE_COUNT);
    const radii = new Float32Array(MAX_PARTICLE_COUNT);
    const speeds = new Float32Array(MAX_PARTICLE_COUNT);

    for (let i = 0; i < MAX_PARTICLE_COUNT; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = Math.cbrt(Math.random()) * 65.0 + 12.0;

      const x = r * Math.sin(phi) * Math.cos(theta);
      const y = r * Math.sin(phi) * Math.sin(theta);
      const z = r * Math.cos(phi);

      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;

      basePositions[i * 3] = x;
      basePositions[i * 3 + 1] = y;
      basePositions[i * 3 + 2] = z;

      angles[i] = Math.random() * Math.PI * 2;
      radii[i] = Math.sqrt(x * x + y * y);
      speeds[i] = 0.5 + Math.random() * 0.8;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setDrawRange(0, QUALITY_CONFIGS[qualityRef.current].particles);

    // Radial gradient glow particle texture
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d')!;
    const grad = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    grad.addColorStop(0, 'rgba(255,255,255,1)');
    grad.addColorStop(0.2, 'rgba(255,255,255,0.9)');
    grad.addColorStop(0.5, 'rgba(255,255,255,0.25)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 64, 64);
    const texture = new THREE.CanvasTexture(canvas);

    const initialTheme = EMOTION_THEMES[emotionRef.current] || EMOTION_THEMES.idle;
    let currentColor = initialTheme.color.clone();
    let currentBrightness = initialTheme.brightness;
    let currentSpeed = initialTheme.speed;

    const material = new THREE.PointsMaterial({
      size: 3.2,
      map: texture,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      color: currentColor,
      opacity: currentBrightness
    });

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);

    let animId: number;
    let timeVal = 0;

    const animate = () => {
      animId = requestAnimationFrame(animate);

      if (haltedRef.current) {
        material.color.set(EMOTION_THEMES.halted.color);
        material.opacity = EMOTION_THEMES.halted.brightness;
        renderer?.render(scene, camera);
        return;
      }

      const activeLod = QUALITY_CONFIGS[qualityRef.current] || QUALITY_CONFIGS.high;
      if (activeLod.particles === 0) return;
      geometry.setDrawRange(0, activeLod.particles);

      const targetTheme = EMOTION_THEMES[emotionRef.current] || EMOTION_THEMES.idle;
      const freq = freqRef.current;

      // Frequency deformation metrics:
      // Bass -> radius dilation & breathing
      // Mid -> surface turbulence & wave ripples
      // Treble -> particle dispersion & micro-jitter
      const bassFactor = (freq.bass || 0) * 1.8;
      const midFactor = (freq.mid || 0) * 2.2;
      const trebleFactor = (freq.treble || 0) * 2.6;
      const overallAudio = (freq.overall || 0);

      // Color interpolation: speaking peaks transition to peakColor
      const targetColor = emotionRef.current === 'speaking'
        ? targetTheme.color.clone().lerp(targetTheme.peakColor, Math.min(1.0, overallAudio * 1.5))
        : targetTheme.color;

      currentColor.lerp(targetColor, 0.08);
      currentBrightness += (targetTheme.brightness * (1.0 + overallAudio * 0.4) - currentBrightness) * 0.08;
      currentSpeed += (targetTheme.speed * (1.0 + bassFactor * 0.6) - currentSpeed) * 0.08;

      material.color.copy(currentColor);
      material.opacity = Math.min(1.0, currentBrightness);

      timeVal += 0.015 * currentSpeed * activeLod.speedFactor;

      const posAttr = geometry.attributes.position as THREE.BufferAttribute;
      const posArray = posAttr.array as Float32Array;
      const pCount = Math.min(activeLod.particles, MAX_PARTICLE_COUNT);

      for (let i = 0; i < pCount; i++) {
        const i3 = i * 3;
        const bx = basePositions[i3];
        const by = basePositions[i3 + 1];
        const bz = basePositions[i3 + 2];

        // Harmonic sphere deformation
        const angle = angles[i] + timeVal * speeds[i];
        const wave = Math.sin(angle * 2.0 + timeVal) * (3.0 + midFactor * 14.0);
        const jitter = (Math.random() - 0.5) * (trebleFactor * 6.0);
        const radialPulse = 1.0 + (bassFactor * 0.35);

        posArray[i3] = (bx * radialPulse) + Math.cos(angle) * wave + jitter;
        posArray[i3 + 1] = (by * radialPulse) + Math.sin(angle) * wave + jitter;
        posArray[i3 + 2] = (bz * radialPulse) + Math.sin(angle * 1.5) * wave + jitter;
      }

      posAttr.needsUpdate = true;
      particles.rotation.y = timeVal * 0.25;
      particles.rotation.x = Math.sin(timeVal * 0.15) * 0.15;

      renderer?.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animId);
      if (renderer) {
        renderer.dispose();
      }
      geometry.dispose();
      material.dispose();
      texture.dispose();
    };
  }, [width, height]);

  return (
    <div
      ref={containerRef}
      style={{
        width: `${width}px`,
        height: `${height}px`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
        position: 'relative'
      }}
    />
  );
};
