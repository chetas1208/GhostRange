import type { ComponentProps } from 'react';
import { NetworkNode } from './NetworkNode';

export function AuthNode(props: Omit<ComponentProps<typeof NetworkNode>, 'kind'>) {
  return <NetworkNode kind="auth" {...props} />;
}
