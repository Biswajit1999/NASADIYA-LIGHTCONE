import * as THREE from 'three';

import { LIGHTCONE_CONFIG } from '../config.js';

function line(points, color, opacity) {
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = new THREE.LineBasicMaterial({ color, transparent: true, opacity, depthWrite: false });
  return new THREE.Line(geometry, material);
}

function ring(radius, color, opacity) {
  const points = [];
  for (let index = 0; index < 128; index += 1) {
    const angle = (index / 128) * Math.PI * 2;
    points.push(new THREE.Vector3(Math.cos(angle) * radius, 0, Math.sin(angle) * radius));
  }
  const loop = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(points), new THREE.LineBasicMaterial({ color, transparent: true, opacity, depthWrite: false }));
  return loop;
}

/** Subtle observer-centred reference geometry; labels remain in the DOM HUD. */
export class SurveyReferenceFrame {
  constructor(parent) {
    this.group = new THREE.Group();
    this.group.name = 'observer-centred-reference-frame';
    this.group.visible = false;
    parent.add(this.group);
  }

  setExtent(maxDistanceMpc) {
    this.group.clear();
    const radius = Math.max(330, Number(maxDistanceMpc || 0) * LIGHTCONE_CONFIG.displayScale);
    this.group.add(
      line([new THREE.Vector3(-radius, 0, 0), new THREE.Vector3(radius, 0, 0)], 0x72e7ff, 0.19),
      line([new THREE.Vector3(0, -radius * 0.55, 0), new THREE.Vector3(0, radius * 0.55, 0)], 0x72e7ff, 0.14),
      line([new THREE.Vector3(0, 0, -radius), new THREE.Vector3(0, 0, radius)], 0x72e7ff, 0.19),
    );
    [0.25, 0.5, 0.75, 1].forEach((fraction, index) => this.group.add(ring(radius * fraction, index === 3 ? 0xeab276 : 0x5bc9e1, index === 3 ? 0.08 : 0.10)));
  }

  setVisible(visible) { this.group.visible = Boolean(visible); }

  dispose() {
    this.group.traverse((item) => { item.geometry?.dispose?.(); item.material?.dispose?.(); });
    this.group.removeFromParent();
  }
}
