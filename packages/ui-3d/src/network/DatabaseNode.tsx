import { NetworkNode } from './NetworkNode';

export function DatabaseNode(props: Omit<React.ComponentProps<typeof NetworkNode>, 'kind'>) {
  return <NetworkNode kind="database" {...props} />;
}
