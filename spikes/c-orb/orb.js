// Phenom Orb Engine - Spike C
(function() {
  const PARTICLE_COUNT = 6000;
  const container = document.getElementById('canvas-container');
  
  // State definitions from ARCHITECTURE.md
  const STATES = {
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

  let currentState = 'idle';
  let targetState = 'idle';
  let lerpFactor = 0.08;
  let currentColor = STATES.idle.color.clone();
  let currentSpeed = STATES.idle.speed;
  let currentDispersion = STATES.idle.dispersion;
  let currentBrightness = STATES.idle.brightness;

  // Scene setup
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(55, container.clientWidth / container.clientHeight, 0.1, 1000);
  camera.position.z = 240;

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  container.appendChild(renderer.domElement);

  // Particles geometry
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array(PARTICLE_COUNT * 3);
  const basePositions = new Float32Array(PARTICLE_COUNT * 3);
  const angles = new Float32Array(PARTICLE_COUNT);
  const radii = new Float32Array(PARTICLE_COUNT);
  const vSpeeds = new Float32Array(PARTICLE_COUNT);

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    // Generate spherical cloud with golden ratio distribution
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

  // Custom circular point texture
  function createParticleTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    const grad = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    grad.addColorStop(0, 'rgba(255,255,255,1)');
    grad.addColorStop(0.25, 'rgba(255,255,255,0.85)');
    grad.addColorStop(0.6, 'rgba(255,255,255,0.25)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 64, 64);
    return new THREE.CanvasTexture(canvas);
  }

  const material = new THREE.PointsMaterial({
    size: 3.2,
    map: createParticleTexture(),
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    color: currentColor
  });

  const particleSystem = new THREE.Points(geometry, material);
  scene.add(particleSystem);

  // Performance monitoring
  let frameCount = 0;
  let lastTime = performance.now();
  let fps = 60;
  const hudFps = document.getElementById('hud-fps');
  const hudState = document.getElementById('hud-state');
  const hudSize = document.getElementById('hud-size');

  function updateHUD() {
    frameCount++;
    const now = performance.now();
    if (now - lastTime >= 500) {
      fps = Math.round((frameCount * 1000) / (now - lastTime));
      hudFps.textContent = fps;
      frameCount = 0;
      lastTime = now;
    }
  }

  // Animation loop
  let clock = new THREE.Clock();

  function animate() {
    requestAnimationFrame(animate);
    const delta = clock.getDelta();
    const elapsedTime = clock.getElapsedTime();

    // Smooth state parameter interpolation (< 500ms transition)
    const target = STATES[targetState];
    currentColor.lerp(target.color, lerpFactor);
    currentSpeed += (target.speed - currentSpeed) * lerpFactor;
    currentDispersion += (target.dispersion - currentDispersion) * lerpFactor;
    currentBrightness += (target.brightness - currentBrightness) * lerpFactor;

    material.color = currentColor;
    material.opacity = currentBrightness;

    const pos = geometry.attributes.position.array;

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const idx = i * 3;
      const bx = basePositions[idx];
      const by = basePositions[idx + 1];
      const bz = basePositions[idx + 2];

      if (targetState === 'halted' && currentSpeed < 0.05) {
        // Frozen
        continue;
      }

      if (targetState === 'thinking') {
        // Swirl around core
        angles[i] += delta * currentSpeed * vSpeeds[i];
        const r = radii[i] * currentDispersion;
        pos[idx] = Math.cos(angles[i]) * r;
        pos[idx + 1] = Math.sin(angles[i]) * r;
        pos[idx + 2] = bz * (0.8 + 0.2 * Math.sin(elapsedTime * 3.0 + i));
      } else if (targetState === 'speaking') {
        // Burst timed to simulated speech amplitude
        const burst = 1.0 + 0.35 * Math.sin(elapsedTime * 8.0 + (i % 20)) * Math.cos(elapsedTime * 4.0);
        pos[idx] = bx * burst * currentDispersion;
        pos[idx + 1] = by * burst * currentDispersion;
        pos[idx + 2] = bz * burst * currentDispersion;
      } else if (targetState === 'listening') {
        // Gentle pulse toward centre
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
    updateHUD();
  }

  // Handle Resize & Container Shrink
  function onResize() {
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }

  window.addEventListener('resize', onResize);

  // State switching UI controls
  document.querySelectorAll('.state-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.state-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const newState = btn.getAttribute('data-state');
      targetState = newState;
      hudState.textContent = newState;
    });
  });

  // Shrink toggle
  const toggleBtn = document.getElementById('toggle-size-btn');
  let isShrunk = false;
  toggleBtn.addEventListener('click', () => {
    isShrunk = !isShrunk;
    if (isShrunk) {
      container.classList.add('shrunk');
      toggleBtn.textContent = 'Restore to Center';
      hudSize.textContent = 'Shrunk (Corner Icon)';
    } else {
      container.classList.remove('shrunk');
      toggleBtn.textContent = 'Shrink to Corner';
      hudSize.textContent = 'Centered (Full)';
    }
    setTimeout(onResize, 460);
  });

  animate();
})();
