import { Line } from "@react-three/drei";

export function ChampionPolicy({
  from,
  to,
}: {
  from: [number, number, number];
  to: [number, number, number];
}) {
  return <Line points={[from, to]} color="#64748b" lineWidth={2} transparent opacity={0.7} />;
}
