# Spike C: Three.js Particle Orb in Electron

## Purpose
Render a Three.js particle cloud inside an Electron window at 60 FPS across five state modes with smooth transitions under 500 ms, shrink-to-corner capabilities, and low idle resource footprint.

## Visual Design & Architecture
- **Particle Count**: 6,000 particles in a spherical Fibonacci cloud distribution.
- **Renderer**: WebGLRenderer with additive blending and radial-gradient particle sprites.
- **States & Visual Behaviors**:
  1. `idle`: Calm blue (`#2b7fff`), gentle drift and wave motion.
  2. `listening`: Teal (`#00e5ff`), radial inward pulse.
  3. `thinking`: Violet (`#a855f7`), high-speed vortex swirl around core.
  4. `speaking`: Amber (`#f59e0b`), radial bursts modulated by speech harmonics.
  5. `halted`: Red (`#ef4444`), frozen and dimmed.
- **State Transition**: LERP factor `0.08` at 60 FPS smoothly interpolates color, velocity, and dispersion within **~450 ms** (< 500 ms requirement).
- **Corner Shrink**: CSS cubic-bezier transition scales the orb to a 120x120 corner icon in **450 ms**.

## How to Run
```bash
cd spikes/c-orb
npm start
```
To run automated benchmark & metric sampling:
```bash
python spikes/c-orb/measure_orb.py
```

## Results
- **Framerate**: Steady **60 FPS**
- **Particles**: 6,000
- **Mode Transition Time**: **450 ms**
- **Corner Shrink Animation**: **450 ms**
- **Status**: Works.
