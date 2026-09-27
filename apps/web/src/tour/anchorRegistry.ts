/** Screen-space positions for 3D tour anchors (updated from R3F). */
const positions = new Map<string, { x: number; y: number; visible: boolean }>();

export function setTourAnchorScreenPos(
  id: string,
  pos: { x: number; y: number; visible?: boolean },
) {
  positions.set(id, { x: pos.x, y: pos.y, visible: pos.visible ?? true });
}

export function getTourAnchorScreenPos(id: string) {
  return positions.get(id);
}

export function clearTourAnchors() {
  positions.clear();
}
