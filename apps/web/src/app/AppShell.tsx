import { GhostCanvas } from '../ui/canvas/GhostCanvas';
import { DomHudLayer } from '../components/dom/hud/DomHudLayer';
import { InspectorShell } from '../components/dom/inspector/InspectorShell';
import { CommandSurface } from '../ui/overlay/CommandSurface';
import { TimelineBar } from '../ui/overlay/TimelineBar';
import { EmptyChamberHint } from '../components/dom/hud/EmptyChamberHint';
import { ErrorBanner } from '../components/dom/hud/ErrorBanner';
import { useRangeDataSource } from '../hooks/useRangeDataSource';
import { useKeyboardNavigation } from '../hooks/useKeyboardNavigation';
import { useReducedMotionGlobally } from '../hooks/useReducedMotionGlobally';
import { useM20CampaignBootstrap } from '../hooks/useM20CampaignBootstrap';
import { useTacticalSelectionUrl } from '../hooks/useTacticalSelectionUrl';
import { useCrossTabFocus } from '../hooks/useCrossTabFocus';
import '../styles/tokens.css';
import '../styles/tour.css';
import '../app.css';
import { TourProvider } from '../tour/TourProvider';

export function AppShell() {
  useRangeDataSource();
  useM20CampaignBootstrap();
  useTacticalSelectionUrl();
  useCrossTabFocus();
  useKeyboardNavigation();
  useReducedMotionGlobally();

  return (
    <TourProvider>
      <div className="app-shell">
        <GhostCanvas />
        <DomHudLayer />
        <ErrorBanner />
        <EmptyChamberHint />
        <TimelineBar />
        <InspectorShell />
        <CommandSurface />
      </div>
    </TourProvider>
  );
}
