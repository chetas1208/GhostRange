import { NetworkNode } from './NetworkNode';

export function ServiceNode(props: Omit<React.ComponentProps<typeof NetworkNode>, 'kind'>) {
  return <NetworkNode kind="service" {...props} />;
}
