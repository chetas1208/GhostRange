import { applyEvents, createInitialState } from '../../state/eventReducer';
import { fixtureReplayerRef } from '../../state/fixtureReplayerRef';
import { useGhostStore } from '../../state/store';

export function TimelineBar() {
  const replayTimeMs = useGhostStore((s) => s.replayTimeMs);
  const replayMaxMs = useGhostStore((s) => s.replayMaxMs);
  const eventLog = useGhostStore((s) => s.eventLog);
  const reset = useGhostStore((s) => s.reset);
  const dispatchEvents = useGhostStore((s) => s.dispatchEvents);
  const setReplayTimeMs = useGhostStore((s) => s.setReplayTimeMs);

  const pct = replayMaxMs > 0 ? (replayTimeMs / replayMaxMs) * 100 : 0;

  const seek = (ms: number) => {
    const st = useGhostStore.getState();
    if (st.dataSource === 'live' && st.liveEventBuffer.length > 0) {
      const ratio = st.replayMaxMs > 0 ? ms / st.replayMaxMs : 0;
      const count = Math.max(1, Math.ceil(ratio * st.liveEventBuffer.length));
      const base = createInitialState();
      base.range = st.range;
      base.campaignId = st.campaignId;
      base.campaignPhase = st.campaignPhase;
      base.streamRangeId = st.streamRangeId;
      base.dataSource = 'live';
      base.streamConnected = st.streamConnected;
      base.sseStatus = st.sseStatus;
      base.replayMaxMs = st.replayMaxMs;
      const replayed = applyEvents(base, st.liveEventBuffer.slice(0, count));
      useGhostStore.setState({
        ...replayed,
        liveEventBuffer: st.liveEventBuffer,
        replayTimeMs: ms,
        replayScrubbing: ms < st.replayMaxMs - 100,
      });
      return;
    }
    useGhostStore.setState({ replayScrubbing: true });
    fixtureReplayerRef.current?.seek(ms, reset, (events, t) => {
      dispatchEvents(events);
      setReplayTimeMs(t);
    });
  };

  return (
    <div className="timeline-bar">
      <div className="timeline-markers" aria-hidden>
        {eventLog.slice(-12).map((e, i) => (
          <span
            key={e.id}
            className="timeline-marker-dot"
            style={{ left: `${((i + 1) / 13) * 100}%` }}
            title={e.label}
          />
        ))}
      </div>
      <input
        type="range"
        min={0}
        max={replayMaxMs}
        value={replayTimeMs}
        onChange={(e) => seek(Number(e.target.value))}
        aria-label="Temporal rail"
        aria-valuetext={`${Math.round(replayTimeMs / 1000)}s`}
      />
      <div className="timeline-hint" style={{ left: `${pct}%` }}>
        {replayTimeMs >= replayMaxMs - 100 ? 'LIVE' : 'SCRUB'}
      </div>
    </div>
  );
}
