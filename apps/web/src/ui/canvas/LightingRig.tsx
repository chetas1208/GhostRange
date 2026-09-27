export function LightingRig() {
  return (
    <>
      <ambientLight intensity={0.35} />
      <directionalLight position={[4, 8, 6]} intensity={0.55} />
      <directionalLight position={[-6, 2, -4]} intensity={0.15} />
    </>
  );
}
