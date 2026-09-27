import { getTourAnchorScreenPos } from '../anchorRegistry';
import type { TourAnchorId } from '../types';

export function TourSpotlight({ anchor }: { anchor?: TourAnchorId }) {
  if (!anchor) {
    return <div className="tour-spotlight tour-spotlight-dim" aria-hidden />;
  }
  const pos = getTourAnchorScreenPos(anchor);
  if (!pos?.visible) {
    return <div className="tour-spotlight tour-spotlight-dim" aria-hidden />;
  }
  return (
    <div className="tour-spotlight tour-spotlight-dim" aria-hidden>
      <div
        className="tour-spotlight-hole"
        style={{
          left: pos.x - 48,
          top: pos.y - 48,
          width: 96,
          height: 96,
        }}
      />
    </div>
  );
}
