import * as THREE from 'three';

import { GpuSurveyCloud } from './gpu-survey-cloud.js';
import { SurveyPoints } from './survey-points.js';

/** Keeps the 2MRS anchor alongside the complete DESI GPU cloud. */
export class CompositeFullCloud {
  constructor(buffer, manifest, objects, meta = {}) {
    this.meta = meta;
    this.desi = new GpuSurveyCloud(buffer, manifest, meta);
    const localObjects = objects.filter((object) => object.source_layer === '2mrs');
    this.anchor = new SurveyPoints(localObjects, { ...meta, dataset_id: '2mrs-anchor', object_count: localObjects.length, overview_count: localObjects.length });
    this.points = new THREE.Group();
    this.points.name = '2mrs-plus-desi-full-cloud';
    this.points.add(this.anchor.points, this.desi.points);
    this.maxDistanceMpc = Math.max(this.anchor.maxDatasetDistance || 0, this.desi.maxDistanceMpc || 0);
  }

  applyState(state) {
    const desi = this.desi.applyState(state);
    const anchorState = { ...state, pointBudget: Math.max(this.anchor.objects.length, Number(state.pointBudget) || 0) };
    const local = this.anchor.applyState(anchorState);
    return {
      ...desi,
      visibleCount: desi.visibleCount + local.visibleCount,
      drawBudget: desi.drawBudget + local.visibleCount,
      candidateCount: desi.candidateCount + local.candidateCount,
      underlyingCount: desi.underlyingCount + local.underlyingCount,
      maxDistance: Math.max(desi.maxDistance, local.maxDistance),
      maxLookback: Math.max(desi.maxLookback, local.maxLookback),
      sourceCounts: { '2mrs': local.visibleCount, 'desi-dr1': desi.gpuResidentCount },
      tracerCounts: desi.tracerCounts,
      fullCatalogue: true,
      compositeFullCatalogue: true,
    };
  }

  updateTime(seconds) { this.desi.updateTime(seconds); this.anchor.updateTime(seconds); }
  dispose() { this.desi.dispose(); this.anchor.dispose(); }
  getObject() { return null; }
  getDisplayPosition() { return new THREE.Vector3(); }
  selectFromRaycaster() { return null; }
}
