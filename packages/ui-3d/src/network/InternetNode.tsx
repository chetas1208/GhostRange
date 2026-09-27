import type { ComponentProps } from 'react';
import { NetworkNode } from './NetworkNode';

export function InternetNode(props: Omit<ComponentProps<typeof NetworkNode>, 'kind'>) {
  return <NetworkNode kind="internet" {...props} />;
}
