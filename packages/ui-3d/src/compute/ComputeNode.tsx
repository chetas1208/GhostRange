import type { ResourceClass } from '../types';
import { CpuWorker } from './CpuWorker';
import { GpuWorker } from './GpuWorker';
import { ProvisioningGhost } from './ProvisioningGhost';

export type ComputeNodeProps = {
  resourceClass: ResourceClass;
  status:
    | 'REQUESTED'
    | 'PROVISIONING'
    | 'BOOTING'
    | 'READY'
    | 'BUSY'
    | 'DRAINING'
    | 'DESTROYING'
    | 'RELEASED'
    | 'FAILED';
  position?: [number, number, number];
  utilization?: number;
};

export function ComputeNode({ resourceClass, status, position, utilization = 0.4 }: ComputeNodeProps) {
  if (status === 'RELEASED') return null;

  if (status === 'REQUESTED' || status === 'PROVISIONING') {
    const fill = status === 'REQUESTED' ? 0.05 : 0.45;
    return <ProvisioningGhost position={position} fill={fill} />;
  }

  if (status === 'BOOTING') {
    return <ProvisioningGhost position={position} fill={0.75} />;
  }

  if (status === 'DESTROYING' || status === 'DRAINING') {
    const isGpu = resourceClass.startsWith('GPU');
    const Worker = isGpu ? GpuWorker : CpuWorker;
    return (
      <group scale={[1, 0.35, 1]}>
        <Worker position={position} utilization={utilization * 0.3} />
      </group>
    );
  }

  const isGpu = resourceClass.startsWith('GPU');
  if (isGpu) return <GpuWorker position={position} utilization={utilization} />;
  return <CpuWorker position={position} utilization={utilization} />;
}
