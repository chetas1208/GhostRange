import { colors } from '../materials/theme';

export type CpuWorkerProps = {
  position?: [number, number, number];
  utilization?: number;
  label?: string;
};

export function CpuWorker({ position = [0, 0, 0], utilization = 0 }: CpuWorkerProps) {
  const h = 0.35 + utilization * 0.25;
  return (
    <group position={position}>
      <mesh scale={[1, h, 1]}>
        <boxGeometry args={[0.5, 0.5, 0.45]} />
        <meshStandardMaterial color={colors.surface} metalness={0.25} roughness={0.65} />
      </mesh>
    </group>
  );
}
