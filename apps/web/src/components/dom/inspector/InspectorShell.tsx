import { AnimatePresence, motion } from 'framer-motion';
import { WorldInspector } from './WorldInspector';
import { TaskInspector } from './TaskInspector';
import { ComputeInspector } from './ComputeInspector';
import { EvidenceInspector } from './EvidenceInspector';
import { AssetInspector } from './AssetInspector';
import { AttackInspector } from './AttackInspector';
import { DecisionInspector } from './DecisionInspector';
import { CostInspector } from './CostInspector';
import { useGhostStore } from '../../../state/store';

export function InspectorShell() {
  const selection = useGhostStore((s) => s.selection);
  const clearSelection = useGhostStore((s) => s.clearSelection);

  let panel = null;
  if (selection?.kind === 'world') panel = <WorldInspector worldId={selection.id} />;
  else if (selection?.kind === 'task') panel = <TaskInspector taskId={selection.id} />;
  else if (selection?.kind === 'worker') panel = <ComputeInspector workerId={selection.id} />;
  else if (selection?.kind === 'artifact' || selection?.kind === 'claim')
    panel = <EvidenceInspector selection={selection} />;
  else if (selection?.kind === 'asset') panel = <AssetInspector assetId={selection.id} />;
  else if (selection?.kind === 'attack') panel = <AttackInspector worldId={selection.worldId} />;
  else if (selection?.kind === 'decision') panel = <DecisionInspector decisionId={selection.id} />;
  else if (selection?.kind === 'cost') panel = <CostInspector />;

  return (
    <AnimatePresence>
      {panel && (
        <motion.aside
          className="inspector-shell"
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 16 }}
        >
          <button type="button" className="inspector-clear" onClick={() => clearSelection()}>
            Clear selection
          </button>
          {panel}
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
