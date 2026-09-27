import { Line } from "@react-three/drei";

/** Shadow/challenger path — dashed, non-authoritative. */
export function ChallengerPolicy({
  from,
  to,
}: {
  from: [number, number, number];
  to: [number, number, number];
}) {
  return <Line points={[from, to]} color="#38bdf8" lineWidth={1} transparent opacity={0.45} dashed dashSize={0.15} gapSize={0.1} />;
}
