import { TacticalHeader } from '../../tactical/TacticalHeader';
import { EventTicker } from '../../tactical/EventTicker';
import { DepthControls } from './DepthControls';
import { SelectionAnnouncer } from '../a11y/SelectionAnnouncer';

export function DomHudLayer() {
  return (
    <>
      <TacticalHeader />
      <EventTicker />
      <DepthControls />
      <SelectionAnnouncer />
    </>
  );
}
