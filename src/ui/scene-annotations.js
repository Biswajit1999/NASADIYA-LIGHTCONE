import * as THREE from 'three';

import { LIGHTCONE_CONFIG } from '../config.js';

const LABELS = Object.freeze([
  { key: 'axis-x-plus', position: (radius) => new THREE.Vector3(radius, 0, 0), offset: [12, 0] },
  { key: 'axis-x-minus', position: (radius) => new THREE.Vector3(-radius, 0, 0), offset: [-12, 0] },
  { key: 'axis-y-plus', position: (radius) => new THREE.Vector3(0, radius * 0.55, 0), offset: [10, -8] },
  { key: 'axis-y-minus', position: (radius) => new THREE.Vector3(0, -radius * 0.55, 0), offset: [10, 8] },
  { key: 'axis-z-plus', position: (radius) => new THREE.Vector3(0, 0, radius), offset: [0, -10] },
  { key: 'axis-z-minus', position: (radius) => new THREE.Vector3(0, 0, -radius), offset: [0, 10] },
  { key: 'observer', position: () => new THREE.Vector3(), offset: [14, -10] },
  { key: 'radial-1', position: (radius) => new THREE.Vector3(radius * 0.18, 0, -radius * 0.18), offset: [8, -4] },
  { key: 'radial-2', position: (radius) => new THREE.Vector3(radius * 0.36, 0, -radius * 0.36), offset: [8, -4] },
  { key: 'radial-3', position: (radius) => new THREE.Vector3(radius * 0.54, 0, -radius * 0.54), offset: [8, -4] },
]);

function withinClipVolume(vector) {
  return vector.z >= -1 && vector.z <= 1 && Math.abs(vector.x) <= 1.08 && Math.abs(vector.y) <= 1.08;
}

/**
 * Projects world-space reference locations into the browser overlay each frame.
 * Labels therefore follow camera orbit/pan/zoom rather than being fixed screen
 * decorations. The coordinate frame is observer-centred Cartesian display
 * geometry derived from RA/Dec positions; it is not a Galactic coordinate grid.
 */
export class SceneAnnotations {
  constructor(host, canvas) {
    this.host = host;
    this.canvas = canvas;
    this.nodes = new Map();
    this.enabled = true;
    this.mode = 'lightcone';
    this.extentMpc = 1;
    this.scratch = new THREE.Vector3();
    host.querySelectorAll('[data-scene-label]').forEach((node) => this.nodes.set(node.dataset.sceneLabel, node));
  }

  setVisible(visible) {
    this.enabled = Boolean(visible);
    if (!this.enabled) this.hideAll();
  }

  setContext({ extentMpc, mode } = {}) {
    this.extentMpc = Math.max(1, Number(extentMpc) || this.extentMpc);
    this.mode = mode || this.mode;
  }

  hideAll() {
    this.nodes.forEach((node) => node.classList.remove('is-projected'));
  }

  update(camera) {
    if (!this.enabled || this.mode !== 'lightcone') {
      this.hideAll();
      return;
    }
    const canvasRect = this.canvas.getBoundingClientRect();
    const hostRect = this.host.getBoundingClientRect();
    const radius = Math.max(330, this.extentMpc * LIGHTCONE_CONFIG.displayScale);
    camera.updateMatrixWorld();

    LABELS.forEach((label) => {
      const node = this.nodes.get(label.key);
      if (!node) return;
      this.scratch.copy(label.position(radius)).project(camera);
      if (!withinClipVolume(this.scratch)) {
        node.classList.remove('is-projected');
        return;
      }
      const x = canvasRect.left - hostRect.left + (this.scratch.x * 0.5 + 0.5) * canvasRect.width + label.offset[0];
      const y = canvasRect.top - hostRect.top + (-this.scratch.y * 0.5 + 0.5) * canvasRect.height + label.offset[1];
      node.style.transform = `translate3d(${x.toFixed(1)}px, ${y.toFixed(1)}px, 0) translate(-50%, -50%)`;
      node.classList.add('is-projected');
    });
  }
}
