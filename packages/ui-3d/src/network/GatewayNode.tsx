import type { ComponentProps } from 'react';
import { NetworkNode } from './NetworkNode';

export function GatewayNode(props: Omit<ComponentProps<typeof NetworkNode>, 'kind'>) {
  return <NetworkNode kind="gateway" {...props} />;
}
