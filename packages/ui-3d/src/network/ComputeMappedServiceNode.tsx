import type { ComponentProps } from 'react';
import { NetworkNode } from './NetworkNode';

/** Logical service placed on a physical compute resource (§32). */
export function ComputeMappedServiceNode(
  props: Omit<ComponentProps<typeof NetworkNode>, 'kind'>,
) {
  return <NetworkNode kind="compute_mapped" {...props} />;
}
