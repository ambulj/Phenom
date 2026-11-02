import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbState } from '../types/protocol';

export type OrbQualityLevel = 'high' | 'medium' | 'low' | 'freeze';

interface OrbProps {
  state: OrbState;
  isShrunk: boolean;
  amplitude?: number;
  qualityLevel?: OrbQualityLevel;
}

export const MAX_PARTICLE_COUNT = 15000;

export const QUALITY_LOD_CONFIGS: Record<OrbQualityLevel, {
  particles: number;
  fps: number;
  speedFactor: number;
  brightness: number;
  gpuCondition: string;
}> = {
  high: {
    particles: 15000,
    fps: 60,
    speedFactor: 1.0,
    brightness: 1.0,
    gpuCondition: 'Idle / Free (< 20%)'
  },
  medium: {
    particles: 7500,
    fps: 30,
    speedFactor: 0.85,
    brightness: 0.85,
    gpuCondition: 'Light Tasks (20-60%)'
  },
  low: {
    particles: 2000,
    fps: 15,
    speedFactor: 0.5,
    brightness: 0.65,
    gpuCondition: 'High Load (> 60%)'
  },
  freeze: {
    particles: 0,
    fps: 0,
    speedFactor: 0.0,
    brightness: 0.0,
    gpuCondition: 'DirectX / 3D Game Exclusive'
  }
};

const STATE_CONFIGS = {
  idle: {
    color: new THREE.Color(0x00e5ff), // Electric Cyan (#00E5FF)
    speed: 0.35,
    dispersion: 1.0,
    brightness: 0.90
  },
  listening: {
    color: new THREE.Color(0x38bdf8), // Bright Aqua (#38BDF8)
    speed: 0.65,
    dispersion: 0.85,
    brightness: 1.0
  },
  thinking: {
    color: new THREE.Color(0xffb300), // Amber Gold (#FFB300)
    speed: 1.8,
    dispersion: 1.15,
    brightness: 1.05
  },
  speaking: {
    color: new THREE.Color(0xf59e0b), // Radiant Amber (#F59E0B)
    speed: 2.2,
    dispersion: 1.4,
    brightness: 1.15
  },
  halted: {
    color: new THREE.Color(0xd32f2f), // Stark Crimson (#D32F2F)
    speed: 0.0,
    dispersion: 0.75,
    brightness: 0.4
  }
};

export const Orb: React.FC<OrbProps> = ({
  state,
  isShrunk,
  amplitude = 0,
  qualityLevel = 'high'
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const targetStateRef = useRef<OrbState>(state);
  const amplitudeRef = useRef<number>(amplitude);
  const qualityRef = useRef<OrbQualityLevel>(qualityLevel);

  useEffect(() => {
    targetStateRef.current = state;
  }, [state]);

  useEffect(() => {
    amplitudeRef.current = amplitude;
  }, [amplitude]);

  useEffect(() => {
    qualityRef.current = qualityLevel;
  }, [qualityLevel]);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    let width = container.clientWidth || 600;
    let height = container.clientHeight || 500;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 1000);
    camera.position.z = 240;

    let renderer: THREE.WebGLRenderer | null = null;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, depth: false, stencil: false });
    } catch (e1) {
      try {
        renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true, depth: false, stencil: false, powerPreference: 'low-power' });
      } catch (e2) {
        console.warn('WebGL initialization failed, using 2D Canvas fallback:', e2);
      }
    }

    if (!renderer) {
      const fallbackCanvas = document.createElement('canvas');
      fallbackCanvas.width = width;
      fallbackCanvas.height = height;
      fallbackCanvas.style.width = '100%';
      fallbackCanvas.style.height = '100%';
      const fctx = fallbackCanvas.getContext('2d');
      container.innerHTML = '';
      container.appendChild(fallbackCanvas);

      let animId: number;
      const animateFallback = () => {
        animId = requestAnimationFrame(animateFallback);
        if (!fctx) return;
        fctx.clearRect(0, 0, width, height);

        const activeLod = QUALITY_LOD_CONFIGS[qualityRef.current] || QUALITY_LOD_CONFIGS.high;
        if (activeLod.fps === 0 || activeLod.particles === 0) return;

        const target = STATE_CONFIGS[targetStateRef.current] || STATE_CONFIGS.idle;
        const colorHex = '#' + target.color.getHexString();
        const t = performance.now() * 0.002;
        const cx = width / 2;
        const cy = height / 2;

        const grad = fctx.createRadialGradient(cx, cy, 10, cx, cy, 90 + Math.sin(t * 3) * 15);
        grad.addColorStop(0, colorHex);
        grad.addColorStop(0.4, colorHex + '99');
        grad.addColorStop(1, 'transparent');
        fctx.fillStyle = grad;
        fctx.beginPath();
        fctx.arc(cx, cy, 110, 0, Math.PI * 2);
        fctx.fill();

        const pCount = Math.min(250, activeLod.particles);
        for (let i = 0; i < pCount; i++) {
          const angle = (i / pCount) * Math.PI * 2 + t * 0.8 * (i % 2 === 0 ? 1 : -1);
          const dist = 70 + (i % 5) * 12 + Math.sin(t * 4 + i) * 8;
          const px = cx + Math.cos(angle) * dist;
          const py = cy + Math.sin(angle) * (dist * 0.65);
          fctx.fillStyle = colorHex;
          fctx.beginPath();
          fctx.arc(px, py, 2.0, 0, Math.PI * 2);
          fctx.fill();
        }
      };
      animateFallback();

      return () => {
        cancelAnimationFrame(animId);
      };
    }

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Dynamic Geometry supporting up to MAX_PARTICLE_COUNT (15,000)
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(MAX_PARTICLE_COUNT * 3);
    const basePositions = new Float32Array(MAX_PARTICLE_COUNT * 3);
    const angles = new Float32Array(MAX_PARTICLE_COUNT);
    const radii = new Float32Array(MAX_PARTICLE_COUNT);
    const vSpeeds = new Float32Array(MAX_PARTICLE_COUNT);

    for (let i = 0; i < MAX_PARTICLE_COUNT; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0);
      const r = Math.cbrt(Math.random()) * 65.0 + 10.0;

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
      vSpeeds[i] = 0.4 + Math.random() * 0.8;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setDrawRange(0, QUALITY_LOD_CONFIGS[qualityRef.current].particles);

    // Radial gradient particle texture
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d')!;
    const grad = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    grad.addColorStop(0, 'rgba(255,255,255,1)');
    grad.addColorStop(0.25, 'rgba(255,255,255,0.85)');
    grad.addColorStop(0.6, 'rgba(255,255,255,0.25)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 64, 64);
    const texture = new THREE.CanvasTexture(canvas);

    let currentColor = STATE_CONFIGS.idle.color.clone();
    let currentSpeed = STATE_CONFIGS.idle.speed;
    let currentDispersion = STATE_CONFIGS.idle.dispersion;
    let currentBrightness = STATE_CONFIGS.idle.brightness;
    const lerpFactor = 0.08;

    const material = new THREE.PointsMaterial({
      size: 3.2,
      map: texture,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      color: currentColor
    });

    const particleSystem = new THREE.Points(geometry, material);
    scene.add(particleSystem);

    const clock = new THREE.Clock();
    let animId: number;
    let lastRenderTime = performance.now();

    const animate = () => {
      animId = requestAnimationFrame(animate);

      const activeLod = QUALITY_LOD_CONFIGS[qualityRef.current] || QUALITY_LOD_CONFIGS.high;

      // Freeze mode: pause rendering loop and hide
      if (activeLod.fps === 0 || activeLod.particles === 0) {
        if (renderer.domElement.style.display !== 'none') {
          renderer.domElement.style.display = 'none';
        }
        return;
      } else {
        if (renderer.domElement.style.display === 'none') {
          renderer.domElement.style.display = 'block';
        }
      }

      // Frame rate governor throttling
      const now = performance.now();
      const targetInterval = 1000 / activeLod.fps;
      if (now - lastRenderTime < targetInterval - 2) {
        return;
      }
      lastRenderTime = now;

      // Update particle draw range dynamically
      geometry.setDrawRange(0, activeLod.particles);

      const delta = clock.getDelta();
      const elapsedTime = clock.getElapsedTime();

      const target = STATE_CONFIGS[targetStateRef.current] || STATE_CONFIGS.idle;
      currentColor.lerp(target.color, lerpFactor);
      currentSpeed += (target.speed * activeLod.speedFactor - currentSpeed) * lerpFactor;
      currentDispersion += (target.dispersion - currentDispersion) * lerpFactor;
      currentBrightness += (target.brightness * activeLod.brightness - currentBrightness) * lerpFactor;

      material.color = currentColor;
      material.opacity = currentBrightness;

      const pos = geometry.attributes.position.array as Float32Array;
      const tstate = targetStateRef.current;
      const ampMod = Math.min(1.0, Math.max(0.0, amplitudeRef.current || 0.0));
      const activeCount = activeLod.particles;

      for (let i = 0; i < activeCount; i++) {
        const idx = i * 3;
        const bx = basePositions[idx];
        const by = basePositions[idx + 1];
        const bz = basePositions[idx + 2];

        if (tstate === 'halted' && currentSpeed < 0.05) {
          continue; // Frozen in halted state
        }

        if (tstate === 'thinking') {
          angles[i] += delta * currentSpeed * vSpeeds[i];
          const r = radii[i] * currentDispersion;
          pos[idx] = Math.cos(angles[i]) * r;
          pos[idx + 1] = Math.sin(angles[i]) * r;
          pos[idx + 2] = bz * (0.8 + 0.2 * Math.sin(elapsedTime * 3.0 + i));
        } else if (tstate === 'speaking') {
          const burstAmp = 1.0 + ampMod * 0.75;
          const burst = (1.0 + 0.35 * Math.sin(elapsedTime * 8.0 + (i % 20)) * Math.cos(elapsedTime * 4.0)) * burstAmp;
          pos[idx] = bx * burst * currentDispersion;
          pos[idx + 1] = by * burst * currentDispersion;
          pos[idx + 2] = bz * burst * currentDispersion;
        } else if (tstate === 'listening') {
          const pulse = 0.85 + 0.15 * Math.sin(elapsedTime * 3.5);
          pos[idx] = bx * pulse;
          pos[idx + 1] = by * pulse;
          pos[idx + 2] = bz * pulse;
        } else {
          // Idle calm drift
          const wave = Math.sin(elapsedTime * 0.8 + bx * 0.02) * 2.5;
          pos[idx] = bx + wave;
          pos[idx + 1] = by + Math.cos(elapsedTime * 0.8 + by * 0.02) * 2.5;
          pos[idx + 2] = bz + Math.sin(elapsedTime * 0.5 + bz * 0.02) * 2.0;
        }
      }

      geometry.attributes.position.needsUpdate = true;
      particleSystem.rotation.y += delta * 0.15 * currentSpeed;

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w === 0 || h === 0) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);
    const resizeObserver = new ResizeObserver(() => handleResize());
    resizeObserver.observe(container);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      resizeObserver.disconnect();
      renderer.dispose();
    };
  }, []);

  return (
    <div
      style={{
        position: 'absolute',
        transition: 'all 0.45s cubic-bezier(0.4, 0, 0.2, 1)',
        ...(isShrunk
          ? {
              top: 16,
              right: 16,
              width: 110,
              height: 110,
              borderRadius: '50%',
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.6)',
              zIndex: 30
            }
          : {
              top: 50,
              left: '50%',
              transform: 'translateX(-50%)',
              width: '100%',
              maxWidth: 650,
              height: 420,
              zIndex: 5
            })
      }}
    >
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
    </div>
  );
};
