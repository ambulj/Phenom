import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbState } from '../types/protocol';

interface OrbProps {
  state: OrbState;
  isShrunk: boolean;
  amplitude?: number;
}

const PARTICLE_COUNT = 6000;

const STATE_CONFIGS = {
  idle: {
    color: new THREE.Color(0x2b7fff), // calm blue
    speed: 0.35,
    dispersion: 1.0,
    brightness: 0.85
  },
  listening: {
    color: new THREE.Color(0x00e5ff), // teal
    speed: 0.6,
    dispersion: 0.85,
    brightness: 0.95
  },
  thinking: {
    color: new THREE.Color(0xa855f7), // violet
    speed: 1.8,
    dispersion: 1.1,
    brightness: 1.0
  },
  speaking: {
    color: new THREE.Color(0xf59e0b), // amber
    speed: 2.2,
    dispersion: 1.4,
    brightness: 1.1
  },
  halted: {
    color: new THREE.Color(0xef4444), // red
    speed: 0.0,
    dispersion: 0.75,
    brightness: 0.4
  }
};

export const Orb: React.FC<OrbProps> = ({ state, isShrunk, amplitude = 0 }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const targetStateRef = useRef<OrbState>(state);
  const amplitudeRef = useRef<number>(amplitude);

  useEffect(() => {
    targetStateRef.current = state;
  }, [state]);

  useEffect(() => {
    amplitudeRef.current = amplitude;
  }, [amplitude]);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;
    let width = container.clientWidth || 600;
    let height = container.clientHeight || 500;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 1000);
    camera.position.z = 240;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(width, height);
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Geometry & distribution
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(PARTICLE_COUNT * 3);
    const basePositions = new Float32Array(PARTICLE_COUNT * 3);
    const angles = new Float32Array(PARTICLE_COUNT);
    const radii = new Float32Array(PARTICLE_COUNT);
    const vSpeeds = new Float32Array(PARTICLE_COUNT);

    for (let i = 0; i < PARTICLE_COUNT; i++) {
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

    // Radial texture
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

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const elapsedTime = clock.getElapsedTime();

      const target = STATE_CONFIGS[targetStateRef.current] || STATE_CONFIGS.idle;
      currentColor.lerp(target.color, lerpFactor);
      currentSpeed += (target.speed - currentSpeed) * lerpFactor;
      currentDispersion += (target.dispersion - currentDispersion) * lerpFactor;
      currentBrightness += (target.brightness - currentBrightness) * lerpFactor;

      material.color = currentColor;
      material.opacity = currentBrightness;

      const pos = geometry.attributes.position.array as Float32Array;
      const tstate = targetStateRef.current;
      const ampMod = Math.min(1.0, Math.max(0.0, amplitudeRef.current || 0.0));

      for (let i = 0; i < PARTICLE_COUNT; i++) {
        const idx = i * 3;
        const bx = basePositions[idx];
        const by = basePositions[idx + 1];
        const bz = basePositions[idx + 2];

        if (tstate === 'halted' && currentSpeed < 0.05) {
          continue; // Frozen
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
          // Idle calm slow drift
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
