import { Line } from "@react-three/drei";

export type ActionPermitProps = {
  from: [number, number, number];
  to: [number, number, number];
  active?: boolean;
  broken?: boolean;
};

/** Short-lived geometric link between decision and effect. */
export function ActionPermit({ from, to, active = true, broken = false }: ActionPermitProps) {
  const color = broken ? "#fbbf24" : active ? "#4ade80" : "#64748b";
  return (
    <Line
      points={[from, to]}
      color={color}
      lineWidth={1}
      transparent
      opacity={broken ? 0.9 : active ? 0.55 : 0.25}
    />
  );
}
