import {
  AgentEntity,
  AttackPath,
  ComputeNode,
  HypothesisBranch,
  NetworkLink,
  NetworkNode,
  RangeWorld,
  ThreatPulse,
  WorldCollapse,
  WorldProvisioningShell,
  type NetworkNodeKind,
  type NodeStatus,
  type WorldLifecycleStatus,
} from '@ghostrange/ui-3d';
import { useShallow } from 'zustand/react/shallow';
import { useGhostStore } from '../../state/store';
import {
  selectActiveAttack,
  selectConnectionStatus,
  selectMaterializedWorkers,
  selectWorldAssets,
  selectForkBranchProgress,
  selectWorldLayout,
  selectWorldLinks,
  worldToSemantic,
} from '../../state/selectors';
import { WorldLabel } from './WorldLabel';
import { MultiverseOrbitField } from './MultiverseOrbitField';
import { ProductionShadow } from '../promotion/ProductionShadow';
import { TourAnchorTracker } from '../../tour/TourAnchorTracker';
import { useTourStore } from '../../tour/tourStore';

function assetNodeStatus(asset: { fractured?: boolean }, attackActive: boolean, onPath: boolean): NodeStatus {
  if (asset.fractured) return 'compromised';
  if (attackActive && onPath) return 'under_attack';
  return 'healthy';
}

function WorldNetwork({
  worldId,
  scale = 1,
  attackSelectionId,
  dimUnrelated,
}: {
  worldId: string;
  scale?: number;
  attackSelectionId?: string | null;
  dimUnrelated?: boolean;
}) {
  const assets = useGhostStore(useShallow((s) => selectWorldAssets(s, worldId)));
  const links = useGhostStore(useShallow((s) => selectWorldLinks(s, worldId)));
  const attack = useGhostStore((s) => selectActiveAttack(s, worldId));
  const selection = useGhostStore((s) => s.selection);
  const hoverTarget = useGhostStore((s) => s.hoverTarget);
  const setSelection = useGhostStore((s) => s.setSelection);
  const setHoverTarget = useGhostStore((s) => s.setHoverTarget);
  const focusWorld = useGhostStore((s) => s.focusWorld);
  const agentsRecord = useGhostStore((s) => s.agents);
  const agents = Object.values(agentsRecord).filter((a) => a.world_id === worldId);

  const assetPos = (id: string): [number, number, number] => {
    const a = assets.find((x) => x.id === id);
    const l = a?.layout;
    return [(l?.x ?? 0) * scale, (l?.y ?? 0) * scale, (l?.z ?? 0) * scale];
  };

  const pathSet = new Set(attack?.path_asset_ids ?? []);
  const attackPoints = attack?.path_asset_ids.map((id) => assetPos(id)) ?? [];
  const attackSelected = attackSelectionId === worldId;

  return (
    <group scale={scale}>
      {links.map((link) => {
        const onPath = pathSet.has(link.from_id) && pathSet.has(link.to_id);
        const dim = dimUnrelated && attackSelectionId && !onPath;
        if (dim) return null;
        return (
          <NetworkLink
            key={link.id}
            from={assetPos(link.from_id)}
            to={assetPos(link.to_id)}
            attack={link.attack || (attack?.active && onPath)}
            faint={link.faint || (dimUnrelated && !onPath && !!attackSelectionId)}
            activeTraffic={!!attack?.active && onPath}
          />
        );
      })}
      {attackPoints.length > 1 && (
        <group
          onClick={(e) => {
            e.stopPropagation();
            setSelection({ kind: 'attack', id: worldId, worldId });
            focusWorld(worldId);
          }}
        >
          <AttackPath
            points={attackPoints}
            active={!!attack?.active}
            state={attack?.active ? 'active' : attackSelected ? 'historical' : 'historical'}
          />
        </group>
      )}
      {attack?.active && attackPoints.length > 0 && (
        <ThreatPulse position={attackPoints[attackPoints.length - 1]} active />
      )}
      {assets.map((a) => {
        const onPath = pathSet.has(a.id);
        if (dimUnrelated && attackSelectionId && !onPath) return null;
        const selected = selection?.kind === 'asset' && selection.id === a.id;
        const hovered = hoverTarget?.kind === 'asset' && hoverTarget.id === a.id;
        const interaction = selected ? 'selected' : hovered ? 'hovered' : 'idle';
        const status = assetNodeStatus(a, !!attack?.active, onPath);
        return (
          <NetworkNode
            key={a.id}
            kind={(a.kind ?? 'vm') as NetworkNodeKind}
            position={[
              (a.layout?.x ?? 0) * scale,
              (a.layout?.y ?? 0) * scale,
              (a.layout?.z ?? 0) * scale,
            ]}
            status={status}
            interaction={interaction}
            fractured={a.fractured}
            onClick={() => {
              setSelection({ kind: 'asset', id: a.id });
              focusWorld(worldId);
            }}
            onPointerOver={() => setHoverTarget({ kind: 'asset', id: a.id })}
            onPointerOut={() => setHoverTarget(null)}
          />
        );
      })}
      {agents.map((ag) => (
        <AgentEntity
          key={ag.id}
          agentType={ag.agent_type}
          position={(() => {
            const anchor = assets.find((x) => x.id === ag.asset_id);
            return anchor
              ? [anchor.layout?.x ?? 0, (anchor.layout?.y ?? 0) + 0.4, anchor.layout?.z ?? 0]
              : [0, 0.5, 0];
          })()}
        />
      ))}
    </group>
  );
}

function SingleWorld({ worldId, position }: { worldId: string; position: [number, number, number] }) {
  const world = useGhostStore((s) => s.worlds[worldId]);
  const selection = useGhostStore((s) => s.selection);
  const focusedWorldId = useGhostStore((s) => s.focusedWorldId);
  const setSelection = useGhostStore((s) => s.setSelection);
  const focusWorld = useGhostStore((s) => s.focusWorld);
  const workers = useGhostStore(useShallow((s) => selectMaterializedWorkers(s, worldId)));
  const attackSelectionId =
    selection?.kind === 'attack' ? selection.worldId : null;

  if (!world) return null;
  if (world.destroyed && world.status !== 'DESTROYING') return null;

  const shellOnly = world.shell_visible && !world.network_ready;
  const ready = world.network_ready && world.status !== 'DESTROYED';
  const destroying = world.status === 'DESTROYING';
  const dimmed = !!focusedWorldId && focusedWorldId !== worldId;

  const enterWorld = () => {
    setSelection({ kind: 'world', id: worldId });
    focusWorld(worldId);
  };

  return (
    <group position={position}>
      <group
        onDoubleClick={(e) => {
          e.stopPropagation();
          enterWorld();
        }}
      >
        {shellOnly && (
          <group
            onClick={(e) => {
              e.stopPropagation();
              enterWorld();
            }}
          >
            <WorldProvisioningShell />
            <WorldLabel worldId={worldId} position={[0, 0.8, 0]} />
          </group>
        )}
        {(ready || destroying) && (
          <RangeWorld
            worldId={worldId}
            label={world.label}
            status={world.status as WorldLifecycleStatus}
            semanticState={worldToSemantic(world.status, world.collapsed)}
            fill={destroying ? Math.max(0.2, (world.fill ?? 1) * 0.6) : (world.fill ?? 1)}
            selected={selection?.kind === 'world' && selection.id === worldId}
            dimmed={dimmed}
            collapsed={world.collapsed}
          >
            <WorldLabel worldId={worldId} />
            {!destroying && (
              <WorldNetwork
                worldId={worldId}
                scale={0.95}
                attackSelectionId={attackSelectionId}
                dimUnrelated={!!attackSelectionId || !!focusedWorldId}
              />
            )}
            {destroying && (
              <group position={[0, 0.3, 0]}>
                <WorldCollapse active />
              </group>
            )}
          </RangeWorld>
        )}
      </group>
      <group position={[2.8, -0.5, 0]}>
        {workers.map((w, i) => (
          <group key={w.id} position={[i * 1.1, 0, 0]}>
            <ComputeNode resourceClass={w.resource_class} status={w.status} utilization={w.utilization} />
          </group>
        ))}
      </group>
    </group>
  );
}

export function MultiverseScene() {
  const showShadow = useGhostStore((s) => s.promotion?.showProductionShadow);
  const mode = useGhostStore((s) => s.mode);
  const connection = useGhostStore(selectConnectionStatus);
  const worldsRecord = useGhostStore((s) => s.worlds);
  const forks = useGhostStore((s) => s.forks);
  const worlds = Object.values(worldsRecord).filter((w) => !w.destroyed || w.status === 'DESTROYING');
  const roots = worlds.filter((w) => !w.parent_world_id);

  // useTourStore must run before the early return below (mirrors
  // ExecutionScene's ordering) — this component stays mounted across mode
  // switches, so calling a hook only on the 'multiverse' branch varies the
  // hook count render-to-render and throws "Rendered fewer hooks than
  // expected" the moment the user switches tabs.
  const tourOn = useTourStore((s) => s.isTourSession && s.status === 'RUNNING');

  if (mode !== 'multiverse') return null;

  const stale = connection === 'DISCONNECTED';

  return (
    <group>
      {forks.map((fk) => {
        const parent = worlds.find((w) => w.id === fk.parent_world_id);
        const child = worlds.find((w) => w.id === fk.child_world_id);
        if (!parent || !child) return null;
        const parentPos: [number, number, number] = parent.parent_world_id
          ? selectWorldLayout(parent, 0)
          : [0, 0.15, 0];
        const siblings = worlds.filter((w) => w.parent_world_id === fk.parent_world_id);
        const childIdx = siblings.findIndex((w) => w.id === child.id);
        const childPos = selectWorldLayout(child, Math.max(0, childIdx), siblings.length);
        const progress = selectForkBranchProgress(child);
        return (
          <HypothesisBranch
            key={fk.id}
            from={parentPos}
            to={childPos}
            progress={progress}
            active={!child.destroyed}
          />
        );
      })}
      {roots.map((w) => (
        <SingleWorld key={w.id} worldId={w.id} position={[0, 0.15, 0]} />
      ))}
      <MultiverseOrbitField enabled={!stale}>
        {worlds
          .filter((w) => w.parent_world_id)
          .map((w) => {
            const siblings = worlds.filter((x) => x.parent_world_id === w.parent_world_id);
            const idx = siblings.findIndex((x) => x.id === w.id);
            return (
              <SingleWorld
                key={w.id}
                worldId={w.id}
                position={selectWorldLayout(w, idx, siblings.length)}
              />
            );
          })}
      </MultiverseOrbitField>
      {showShadow && (
        <ProductionShadow alignedComponentIds={['api-gateway', 'web-frontend']} changedComponentIds={['auth-service']} />
      )}
      {stale && (
        <mesh visible={false}>
          <boxGeometry args={[0.01, 0.01, 0.01]} />
        </mesh>
      )}
      {tourOn ? (
        <>
          <TourAnchorTracker anchorId="production-world" position={[0, 0.15, 0]} />
          <TourAnchorTracker anchorId="auth-service" position={[0.8, 0.2, 0]} />
          <TourAnchorTracker anchorId="attack-path" position={[0, 0.35, 0]} />
          <TourAnchorTracker anchorId="hypothesis-branch" position={[1.5, 0, 4]} />
        </>
      ) : null}
    </group>
  );
}
