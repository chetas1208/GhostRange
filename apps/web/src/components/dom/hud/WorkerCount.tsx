import { selectWorkerCount } from '../../../state/selectors';
import { useGhostStore } from '../../../state/store';

export function WorkerCount() {
  const workers = useGhostStore(selectWorkerCount);
  return <span className="worker-count">{workers} WORKERS</span>;
}
