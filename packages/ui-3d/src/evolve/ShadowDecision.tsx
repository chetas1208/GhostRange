import { Html } from "@react-three/drei";

export type ShadowDecisionProps = {
  position?: [number, number, number];
  championLabel: string;
  challengerLabel: string;
  disagree?: boolean;
};

export function ShadowDecision({
  position = [0, 1.2, 0],
  championLabel,
  challengerLabel,
  disagree = false,
}: ShadowDecisionProps) {
  return (
    <Html center distanceFactor={10} position={position} style={{ pointerEvents: "none" }}>
      <div
        style={{
          fontSize: 9,
          fontFamily: "ui-monospace, monospace",
          background: "rgba(15,23,42,0.9)",
          padding: 6,
          borderRadius: 4,
          color: "#e2e8f0",
          border: disagree ? "1px solid #fbbf24" : "1px solid #334155",
        }}
      >
        <div>CHAMPION: {championLabel}</div>
        <div style={{ opacity: 0.85 }}>CHALLENGER (shadow): {challengerLabel}</div>
        <div style={{ marginTop: 4, opacity: 0.7 }}>Challenger does not control effects</div>
      </div>
    </Html>
  );
}
