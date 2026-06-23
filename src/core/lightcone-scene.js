import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const SLICE_CAMERA = new THREE.Vector3(0, 0, 940);
const LIGHTCONE_CAMERA = new THREE.Vector3(1060, 570, 1260);

function scaledFrame(distanceMpc, mode) {
  const scaledRadius = Math.max(300, Number(distanceMpc || 0) * 3.0);
  if (mode === 'lightcone') {
    // Tighter, still full-footprint framing: the survey is the visual subject, not the surrounding empty canvas.
    const distance = Math.max(1320, scaledRadius * 1.30);
    return { position: new THREE.Vector3(distance * 0.72, distance * 0.39, distance * 0.94), target: new THREE.Vector3() };
  }
  return { position: new THREE.Vector3(0, 0, Math.max(840, scaledRadius * 0.62)), target: new THREE.Vector3() };
}

function createObserverMarker() {
  const group = new THREE.Group();
  const core = new THREE.Mesh(
    new THREE.SphereGeometry(4.2, 20, 20),
    new THREE.MeshBasicMaterial({ color: 0xf7fbff }),
  );
  const halo = new THREE.Mesh(
    new THREE.RingGeometry(12, 13, 64),
    new THREE.MeshBasicMaterial({
      color: 0x72e7ff,
      transparent: true,
      opacity: 0.52,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
  );
  const outer = new THREE.Mesh(
    new THREE.RingGeometry(26, 27, 64),
    new THREE.MeshBasicMaterial({
      color: 0x72e7ff,
      transparent: true,
      opacity: 0.13,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
  );
  group.add(core, halo, outer);
  return group;
}

function createSelectionMarker() {
  const group = new THREE.Group();
  const ring = new THREE.Mesh(
    new THREE.RingGeometry(10, 12.5, 72),
    new THREE.MeshBasicMaterial({
      color: 0xeab276,
      transparent: true,
      opacity: 0.92,
      side: THREE.DoubleSide,
      depthWrite: false,
    }),
  );
  const core = new THREE.Mesh(
    new THREE.SphereGeometry(2.7, 16, 16),
    new THREE.MeshBasicMaterial({ color: 0xfff6eb, transparent: true, opacity: 0.95 }),
  );
  group.add(ring, core);
  group.visible = false;
  return group;
}

export class LightconeScene {
  constructor(canvas) {
    this.canvas = canvas;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x020611);
    this.scene.fog = new THREE.FogExp2(0x020611, 0.00030);

    this.camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100000);
    this.camera.position.copy(SLICE_CAMERA);

    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.9));
    this.renderer.setSize(window.innerWidth, window.innerHeight, false);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.11;

    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.065;
    this.controls.minDistance = 18;
    this.controls.maxDistance = 70000;
    this.controls.target.set(0, 0, 0);

    this.world = new THREE.Group();
    this.scene.add(this.world);

    this.observer = createObserverMarker();
    this.observer.visible = true;
    this.world.add(this.observer);

    this.selectionMarker = createSelectionMarker();
    this.world.add(this.selectionMarker);

    this.mode = 'slice';
    this.datasetMaxDistanceMpc = 350;
    this.focusAnimation = null;
    this.timeStart = performance.now();

    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(window.innerWidth, window.innerHeight, false);
  }

  defaultFrame(mode = this.mode) {
    if (this.datasetMaxDistanceMpc <= 380) {
      if (mode === 'lightcone') return { position: LIGHTCONE_CAMERA.clone(), target: new THREE.Vector3() };
      return { position: SLICE_CAMERA.clone(), target: new THREE.Vector3() };
    }
    return scaledFrame(this.datasetMaxDistanceMpc, mode);
  }

  setDatasetExtent(maxDistanceMpc) {
    this.datasetMaxDistanceMpc = Math.max(1, Number(maxDistanceMpc) || 1);
  }

  animateCamera(position, target, duration = 720) {
    this.focusAnimation = {
      startedAt: performance.now(),
      duration,
      fromPosition: this.camera.position.clone(),
      toPosition: position.clone(),
      fromTarget: this.controls.target.clone(),
      toTarget: target.clone(),
    };
  }

  setSpatialMode(mode, { immediate = false } = {}) {
    this.mode = mode;
    this.observer.visible = mode === 'lightcone';
    const frame = this.defaultFrame(mode);
    if (immediate) {
      this.camera.position.copy(frame.position);
      this.controls.target.copy(frame.target);
      this.controls.update();
      return;
    }
    this.animateCamera(frame.position, frame.target, 800);
  }

  resetView() {
    const frame = this.defaultFrame();
    this.animateCamera(frame.position, frame.target, 720);
  }

  focusLocalSlice() {
    this.setSpatialMode('slice');
  }

  focusOn(position, scale = 80) {
    if (this.mode === 'slice') {
      const destination = position.clone().add(new THREE.Vector3(0, 0, THREE.MathUtils.clamp(scale * 3 + 150, 260, 720)));
      this.animateCamera(destination, position, 750);
      return;
    }
    const direction = position.clone();
    if (direction.lengthSq() < 1) direction.set(0.4, 0.4, 0.7);
    direction.normalize();
    const destination = position.clone().add(direction.multiplyScalar(THREE.MathUtils.clamp(scale * 2.35 + 70, 120, 1300)));
    this.animateCamera(destination, position, 800);
  }

  setSelection(position = null) {
    if (!position) {
      this.selectionMarker.visible = false;
      return;
    }
    this.selectionMarker.visible = true;
    this.selectionMarker.position.copy(position);
    this.selectionMarker.lookAt(this.camera.position);
  }

  tick(now) {
    if (this.focusAnimation) {
      const progress = Math.min(1, (now - this.focusAnimation.startedAt) / this.focusAnimation.duration);
      const eased = 1 - (1 - progress) ** 3;
      this.camera.position.lerpVectors(this.focusAnimation.fromPosition, this.focusAnimation.toPosition, eased);
      this.controls.target.lerpVectors(this.focusAnimation.fromTarget, this.focusAnimation.toTarget, eased);
      if (progress >= 1) this.focusAnimation = null;
    }

    const elapsed = (now - this.timeStart) * 0.001;
    if (this.observer.visible) {
      this.observer.children[1].rotation.z += 0.008;
      this.observer.children[2].rotation.z -= 0.003;
      const pulse = 1 + Math.sin(elapsed * 2.4) * 0.04;
      this.observer.children[2].scale.setScalar(pulse);
    }
    if (this.selectionMarker.visible) {
      this.selectionMarker.children[0].rotation.z += 0.015;
      const scale = 1 + Math.sin(elapsed * 3.4) * 0.06;
      this.selectionMarker.scale.setScalar(scale);
      this.selectionMarker.lookAt(this.camera.position);
    }

    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}
