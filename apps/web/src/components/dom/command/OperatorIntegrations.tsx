/** Transient operator actions (M11–M19) — only inside CommandSurface, not permanent HUD. */
import { PromotionPanel } from '../hud/PromotionPanel';
import { GhostWatchPanel } from '../hud/GhostWatchPanel';
import { MeshPanel } from '../hud/MeshPanel';
import { CausalPanel } from '../hud/CausalPanel';

export function OperatorIntegrations() {
  return (
    <div className="operator-integrations" aria-label="Subsystem operator actions">
      <p className="operator-integrations-note">
        Advanced integrations — evidence mode only. Not required for core investigation flow.
      </p>
      <PromotionPanel />
      <GhostWatchPanel />
      <MeshPanel />
      <CausalPanel />
    </div>
  );
}
