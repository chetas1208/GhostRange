import { useTourStore } from '../tour/tourStore';
import { useFixtureBootstrap } from './useFixtureBootstrap';
import { useLiveBootstrap } from './useLiveBootstrap';

const SOURCE = (
  import.meta.env.VITE_DATA_SOURCE ?? (import.meta.env.PROD ? 'live' : 'fixture')
) as 'fixture' | 'live';

export function useRangeDataSource() {
  const blockFixture = useTourStore(
    (s) => s.showWelcome || s.isTourSession || s.status === 'RUNNING' || s.status === 'PAUSED',
  );
  const fixtureRef = useFixtureBootstrap(SOURCE === 'fixture' && !blockFixture);
  useLiveBootstrap(SOURCE === 'live' && !blockFixture);
  return { dataSource: SOURCE, fixtureRef };
}
