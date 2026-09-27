import { useState } from 'react';
import { AppShell } from './app/AppShell';
import { InvestigationIntakeScreen } from './intake/InvestigationIntakeScreen';

/** No router in this app; a single, deliberately narrow path check keeps
 * '/' behavior (and every existing e2e/visual test targeting it) exactly
 * as-is, while giving the new intake screen its own reachable entry point. */
function startedFromIntakePath(): boolean {
  return typeof window !== 'undefined' && window.location.pathname.startsWith('/start');
}

export function App() {
  const [showIntake, setShowIntake] = useState(startedFromIntakePath);

  if (showIntake) {
    return (
      <InvestigationIntakeScreen
        onContinue={() => {
          window.history.pushState(null, '', '/');
          setShowIntake(false);
        }}
      />
    );
  }

  return <AppShell />;
}
