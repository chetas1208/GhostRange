import { ProductIdentity } from '../dom/hud/ProductIdentity';
import { ModeSelector } from '../dom/hud/ModeSelector';
import { SystemStatus } from '../dom/hud/SystemStatus';
import { MissionStatus } from './MissionStatus';
import { StageTimer } from './StageTimer';

/** Shared tactical shell — three tabs + mission strip + timing. */
export function TacticalHeader() {
  return (
    <>
      <ProductIdentity />
      <ModeSelector />
      <MissionStatus />
      <StageTimer />
      <SystemStatus />
    </>
  );
}
