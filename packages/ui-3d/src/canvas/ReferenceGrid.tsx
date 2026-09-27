import { Grid } from '@react-three/drei';

export function ReferenceGrid() {
  return (
    <Grid
      position={[0, -3, 0]}
      args={[80, 80]}
      cellSize={1}
      cellThickness={0.4}
      sectionSize={5}
      sectionThickness={0.6}
      fadeDistance={45}
      fadeStrength={1.2}
      infiniteGrid
      cellColor="#1e1e26"
      sectionColor="#252530"
    />
  );
}
