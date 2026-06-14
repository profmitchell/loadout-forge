import * as THREE from "three";
import type { SlotId } from "@/lib/types";

/** After normalization every preview occupies the same max axis length in scene units. */
export const PREVIEW_TARGET_MAX_DIM = 2.0;

const CARD_MARGIN = 1.18;
const LIGHTBOX_MARGIN = 1.34;

/** Per-slot tweaks — lanterns export at 27 cm while some Meshy GLBs are ~1.9 m. */
const SLOT_ZOOM: Partial<Record<SlotId, number>> = {
  lantern: 1.05,
  helm: 1.0,
};

export function previewMargin(interactive: boolean, slot?: SlotId | string): number {
  const base = interactive ? LIGHTBOX_MARGIN : CARD_MARGIN;
  const zoom = slot && slot in SLOT_ZOOM ? SLOT_ZOOM[slot as SlotId]! : 1;
  return base / zoom;
}

/**
 * Center mesh at origin and scale so the longest axis matches PREVIEW_TARGET_MAX_DIM.
 * Fixes tiny card thumbnails when GLB units differ (e.g. 0.28 m vs 1.9 m exports).
 */
export function normalizePreviewModel(
  scene: THREE.Object3D,
  margin: number,
): THREE.Object3D {
  const model = scene.clone(true);
  model.updateMatrixWorld(true);

  const box = new THREE.Box3().setFromObject(model);
  const center = new THREE.Vector3();
  const size = new THREE.Vector3();
  box.getCenter(center);
  box.getSize(size);
  model.position.sub(center);

  const maxDim = Math.max(size.x, size.y, size.z, 1e-6);
  model.scale.setScalar(PREVIEW_TARGET_MAX_DIM / maxDim / margin);
  return model;
}
