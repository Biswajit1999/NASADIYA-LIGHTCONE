import * as THREE from 'three';

import { LIGHTCONE_CONFIG } from '../config.js';

function phase(progress) {
  if (progress < 0.25) return 'overview';
  if (progress < 0.50) return 'approach';
  if (progress < 0.75) return 'interior';
  return 'return';
}

export class GuidedFlyby {
  constructor(scene) {
    this.scene = scene;
    this.active = false;
    this.listeners = new Set();
    this.lastUpdate = 0;
    scene.controls.addEventListener('start', () => this.stop('manual'));
  }

  onChange(listener) { this.listeners.add(listener); return () => this.listeners.delete(listener); }

  emit(status) { this.listeners.forEach((listener) => listener(status)); }

  start() {
    if (this.active) return;
    this.scene.setSpatialMode('lightcone', { immediate: true });
    const radius = Math.max(1200, this.scene.datasetMaxDistanceMpc * LIGHTCONE_CONFIG.displayScale * 1.12);
    const positions = [
      new THREE.Vector3(radius * 0.72, radius * 0.38, radius * 0.94),
      new THREE.Vector3(radius * 0.40, radius * 0.16, radius * 0.47),
      new THREE.Vector3(radius * 0.09, -radius * 0.03, radius * 0.14),
      new THREE.Vector3(-radius * 0.18, radius * 0.07, -radius * 0.20),
      new THREE.Vector3(-radius * 0.68, radius * 0.30, -radius * 0.82),
    ];
    const targets = [
      new THREE.Vector3(),
      new THREE.Vector3(radius * 0.10, 0, radius * 0.03),
      new THREE.Vector3(radius * 0.16, radius * 0.02, radius * 0.10),
      new THREE.Vector3(-radius * 0.12, 0, -radius * 0.10),
      new THREE.Vector3(),
    ];
    this.route = {
      startedAt: performance.now(),
      duration: 22000,
      positions: new THREE.CatmullRomCurve3(positions, false, 'centripetal'),
      targets: new THREE.CatmullRomCurve3(targets, false, 'centripetal'),
    };
    this.active = true;
    this.emit({ active: true, phase: 'overview', progress: 0 });
  }

  stop(reason = 'stopped') {
    if (!this.active) return;
    this.active = false;
    this.route = null;
    this.emit({ active: false, reason, progress: 0 });
  }

  toggle() { this.active ? this.stop() : this.start(); }

  tick(now) {
    if (!this.active || !this.route) return;
    const progress = ((now - this.route.startedAt) % this.route.duration) / this.route.duration;
    this.scene.camera.position.copy(this.route.positions.getPointAt(progress));
    this.scene.controls.target.copy(this.route.targets.getPointAt(progress));
    if (now - this.lastUpdate > 120) {
      this.lastUpdate = now;
      this.emit({ active: true, phase: phase(progress), progress });
    }
  }
}
