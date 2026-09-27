import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { setTourAnchorScreenPos } from './anchorRegistry';

export function TourAnchorTracker({
  anchorId,
  position,
}: {
  anchorId: string;
  position: [number, number, number];
}) {
  const { camera, gl } = useThree();
  const vec = new THREE.Vector3(...position);

  useFrame(() => {
    const projected = vec.clone().project(camera);
    const visible = projected.z < 1 && projected.z > -1;
    const x = (projected.x * 0.5 + 0.5) * gl.domElement.clientWidth;
    const y = (-projected.y * 0.5 + 0.5) * gl.domElement.clientHeight;
    setTourAnchorScreenPos(anchorId, { x, y, visible });
  });

  return null;
}
