import demoFixtureUrl from '../fixtures/demo-auth-incident-031.jsonl?url';
import { fixtureReplayerRef } from '../state/fixtureReplayerRef';
import { FixtureReplayer, parseFixtureJsonl } from '../state/replay';
import { useGhostStore } from '../state/store';
import { TOUR_CAMPAIGN_ID } from './steps/guidedSteps';

let tourReplayer: FixtureReplayer | null = null;

export function getTourReplayer() {
  return tourReplayer;
}

export async function loadTourControlledReplay(): Promise<void> {
  const res = await fetch(demoFixtureUrl);
  const text = await res.text();
  const timed = parseFixtureJsonl(text);
  tourReplayer = new FixtureReplayer(timed);
  fixtureReplayerRef.current = tourReplayer;

  const reset = useGhostStore.getState().reset;
  reset();
  useGhostStore.setState({
    dataSource: 'fixture',
    streamConnected: false,
    live: false,
    replayScrubbing: false,
    range: {
      id: TOUR_CAMPAIGN_ID,
      slug: 'tour-auth-role-revocation',
      label: 'Tour · role revocation after refresh',
    },
    replayMaxMs: tourReplayer.maxMs,
  });

  tourReplayer.pause();
}

export function seekTourReplay(ms: number) {
  if (!tourReplayer) return;
  const reset = useGhostStore.getState().reset;
  const dispatchEvents = useGhostStore.getState().dispatchEvents;
  const setReplayTimeMs = useGhostStore.getState().setReplayTimeMs;
  useGhostStore.setState({ replayScrubbing: true });
  tourReplayer.seek(ms, reset, (events, t) => {
    dispatchEvents(events);
    setReplayTimeMs(t);
  });
}

export function pauseTourReplay() {
  tourReplayer?.pause();
}

export function destroyTourReplay() {
  tourReplayer?.destroy();
  tourReplayer = null;
}
