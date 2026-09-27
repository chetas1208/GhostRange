import { ActionGate, type ActionGateState } from "./ActionGate";

export type InvariantBoundaryProps = {
  position?: [number, number, number];
  propertyId: string;
  assurance: string;
  lastVerdict?: ActionGateState;
};

/** Temporal invariant marker — subtle, not cybersecurity neon. */
export function InvariantBoundary({
  position = [0, 1.6, 0],
  propertyId,
  assurance,
  lastVerdict = "EVALUATING",
}: InvariantBoundaryProps) {
  return (
    <ActionGate
      position={position}
      state={lastVerdict}
      actionType={propertyId}
      reason={`Assurance: ${assurance}`}
    />
  );
}
