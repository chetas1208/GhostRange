import { Html } from '@react-three/drei';
import { useGhostStore } from '../../state/store';

type WorldLabelProps = {
  worldId: string;
  position?: [number, number, number];
};

export function WorldLabel({ worldId, position = [0, 1.2, 0] }: WorldLabelProps) {
  const world = useGhostStore((s) => s.worlds[worldId]);
  const range = useGhostStore((s) => s.range);
  if (!world || world.destroyed) return null;

  return (
    <Html position={position} center className="world-label-html" zIndexRange={[40, 0]}>
      <div className="world-label">
        <span className="world-label-title">{world.label}</span>
        <span className="world-label-sub">{range?.slug ?? world.status}</span>
      </div>
    </Html>
  );
}
