import { colors } from '../materials/theme';

export type GpuWorkerProps = {
  position?: [number, number, number];
  utilization?: number;
};

export function GpuWorker({ position = [0, 0, 0], utilization = 0 }: GpuWorkerProps) {
  return (
    <group position={position}>
      <mesh>
        <boxGeometry args={[0.6, 0.2 + utilization * 0.15, 0.5]} />
        <meshStandardMaterial color={colors.graphite} />
      </mesh>
      {[-0.18, -0.06, 0.06, 0.18].map((x) => (
        <mesh key={x} position={[x, 0.12, 0]}>
          <boxGeometry args={[0.04, 0.18, 0.42]} />
          <meshStandardMaterial color={colors.electric} emissive={colors.electric} emissiveIntensity={0.15} />
        </mesh>
      ))}
    </group>
  );
}
