import { useMemo } from "react";
import { Html } from "@react-three/drei";

export type ActionGateState =
  | "EVALUATING"
  | "AUTHORIZED"
  | "DENIED"
  | "STALE"
  | "HUMAN_REQUIRED";

export type ActionGateProps = {
  position?: [number, number, number];
  state: ActionGateState;
  actionType?: string;
  reason?: string;
};

const STATE_COLOR: Record<ActionGateState, string> = {
  EVALUATING: "#94a3b8",
  AUTHORIZED: "#4ade80",
  DENIED: "#f87171",
  STALE: "#fbbf24",
  HUMAN_REQUIRED: "#c084fc",
};

/** Restrained authorization gate — not a primary nav tab. */
export function ActionGate({ position = [0, 2.2, 0], state, actionType, reason }: ActionGateProps) {
  const color = STATE_COLOR[state];
  const label = useMemo(() => actionType ?? "ACTION", [actionType]);
  return (
    <group position={position}>
      <mesh>
        <boxGeometry args={[1.4, 0.12, 0.08]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.35} />
      </mesh>
      <Html center distanceFactor={8} style={{ pointerEvents: "none", userSelect: "none" }}>
        <div
          style={{
            fontFamily: "ui-monospace, monospace",
            fontSize: 10,
            color: "#e2e8f0",
            background: "rgba(15,23,42,0.85)",
            padding: "4px 8px",
            borderRadius: 4,
            border: `1px solid ${color}`,
            maxWidth: 220,
          }}
        >
          <div>{label}</div>
          <div style={{ opacity: 0.85 }}>{state}</div>
          {reason ? <div style={{ fontSize: 9, marginTop: 4, opacity: 0.75 }}>{reason}</div> : null}
        </div>
      </Html>
    </group>
  );
}
