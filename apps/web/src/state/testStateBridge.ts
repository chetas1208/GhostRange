import { selectConnectionStatus, selectHasActiveWorld, selectWorkerCount } from './selectors';
import { useGhostStore } from './store';

/** Test/capture hook — no secrets. */
export function installTestStateBridge() {
  if (typeof window === 'undefined') return;
  const read = () => {
    const s = useGhostStore.getState();
    let workerProvisioning = false;
    for (const id in s.workers) {
      if (s.workers[id].status === 'PROVISIONING') workerProvisioning = true;
    }
    return {
      campaignId: s.campaignId,
      streamRangeId: s.streamRangeId,
      campaignPhase: s.campaignPhase,
      mode: s.mode,
      connection: selectConnectionStatus(s),
      hasActiveWorld: selectHasActiveWorld(s),
      workerCount: selectWorkerCount(s),
      workerProvisioning,
      authorizationDenied: s.authorizationGate?.state === 'DENIED',
      hasCausal: Boolean(s.causal),
      attackCount: s.attacks.length,
      forkCount: s.forks.length,
      verificationRing: s.verificationRing,
      sequence: s.sequence,
      lastEventSeq: s.lastEventSeq,
      sseStatus: s.sseStatus,
      arenaQualification: s.arenaQualification,
      dataSource: s.dataSource,
      selection: s.selection,
      replayScrubbing: s.replayScrubbing,
      replayMaxMs: s.replayMaxMs,
      replayTimeMs: s.replayTimeMs,
    };
  };
  (window as unknown as { __GHOSTRANGE_TEST_STATE__?: () => ReturnType<typeof read> }).__GHOSTRANGE_TEST_STATE__ =
    read;
}
