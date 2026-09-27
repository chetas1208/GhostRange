import { ActionGate, type ActionGateState } from "../shield/ActionGate";

export type EvolutionMarkerProps = {
  position?: [number, number, number];
  fromVersion: string;
  toVersion: string;
  state?: ActionGateState;
};

/** Policy version transition — not a primary tab. */
export function EvolutionMarker({
  position = [0, 2.5, 0],
  fromVersion,
  toVersion,
  state = "AUTHORIZED",
}: EvolutionMarkerProps) {
  return (
    <ActionGate
      position={position}
      state={state}
      actionType={`${fromVersion} → ${toVersion}`}
      reason="GhostEvolve promotion lineage"
    />
  );
}
