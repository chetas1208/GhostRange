import { useEffect, useRef, type RefObject } from 'react';
import demoFixtureUrl from '../fixtures/demo-auth-incident-031.jsonl?url';
import m2FixtureUrl from '../fixtures/m2-auth-lab-v1.jsonl?url';
import { fixtureReplayerRef } from '../state/fixtureReplayerRef';
import { FixtureReplayer, parseFixtureJsonl } from '../state/replay';
import { useGhostStore } from '../state/store';

const FIXTURE = import.meta.env.VITE_FIXTURE ?? 'm2';

function fixtureUrl() {
  return FIXTURE === 'm1' ? demoFixtureUrl : m2FixtureUrl;
}

export function useFixtureBootstrap(enabled = true) {
  const replayer = useRef<FixtureReplayer | null>(null);
  const reset = useGhostStore((s) => s.reset);
  const dispatchEvents = useGhostStore((s) => s.dispatchEvents);
  const setReplayTimeMs = useGhostStore((s) => s.setReplayTimeMs);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    (async () => {
      useGhostStore.setState({
        dataSource: 'fixture',
        streamConnected: false,
        live: false,
        activeProvider: null,
        replayScrubbing: false,
      });
      const res = await fetch(fixtureUrl());
      const text = await res.text();
      if (cancelled) return;
      const timed = parseFixtureJsonl(text);
      replayer.current = new FixtureReplayer(timed);
      fixtureReplayerRef.current = replayer.current;
      useGhostStore.setState({ replayMaxMs: replayer.current.maxMs });
      reset();
      replayer.current.seek(0, reset, (events, t) => {
        dispatchEvents(events);
        setReplayTimeMs(t);
      });
      let lastMs = -1;
      replayer.current.play((events, t) => {
        if (events.length) dispatchEvents(events);
        const ms = Math.floor(t);
        if (ms !== lastMs) {
          lastMs = ms;
          setReplayTimeMs(ms);
        }
      });
    })();
    return () => {
      cancelled = true;
      replayer.current?.destroy();
    };
  }, [dispatchEvents, enabled, reset, setReplayTimeMs]);

  return replayer;
}

export function useReplayControls(replayerRef: RefObject<FixtureReplayer | null>) {
  const reset = useGhostStore((s) => s.reset);
  const dispatchEvents = useGhostStore((s) => s.dispatchEvents);
  const setReplayTimeMs = useGhostStore((s) => s.setReplayTimeMs);

  return {
    seek(ms: number) {
      replayerRef.current?.seek(ms, reset, (events, t) => {
        dispatchEvents(events);
        setReplayTimeMs(t);
      });
    },
    play() {
      replayerRef.current?.play((events, t) => {
        if (events.length) dispatchEvents(events);
        setReplayTimeMs(t);
      });
    },
    pause() {
      replayerRef.current?.pause();
    },
  };
}
