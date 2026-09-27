import { Instance, Instances } from '@react-three/drei';
import { colors } from '../materials/theme';

export type InstancedVm = {
  id: string;
  position: [number, number, number];
};

/** Batched VM monoliths — keeps draw calls low for large ranges. */
export function InstancedNetworkNodes({ vms }: { vms: InstancedVm[] }) {
  if (vms.length === 0) return null;
  return (
    <Instances limit={vms.length} range={vms.length}>
      <boxGeometry args={[0.5, 0.35, 0.4]} />
      <meshStandardMaterial color={colors.surface} metalness={0.2} roughness={0.7} />
      {vms.map((vm) => (
        <Instance key={vm.id} position={vm.position} />
      ))}
    </Instances>
  );
}
