import { normalizeEnvelope } from './normalizeEnvelope';
import type { GhostEvent } from './types';

export type TimedEvent = GhostEvent & { offsetMs: number };

export function parseFixtureJsonl(text: string): TimedEvent[] {
  return text
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line, i) => {
      const raw = JSON.parse(line) as Record<string, unknown>;
      const offsetMs = (raw.offset_ms as number) ?? i * 800;
      const seq = (raw.sequence as number) ?? i + 1;
      const event = raw.event_name
        ? normalizeEnvelope(raw, seq)
        : (raw as unknown as GhostEvent);
      return { ...event, offsetMs };
    })
    .sort((a, b) => a.offsetMs - b.offsetMs);
}

export function eventsUntilTime(all: TimedEvent[], timeMs: number): GhostEvent[] {
  return all.filter((e) => e.offsetMs <= timeMs).map(({ offsetMs: _, ...ev }) => ev);
}

export function maxReplayTime(all: TimedEvent[]): number {
  return all.reduce((m, e) => Math.max(m, e.offsetMs), 0);
}

export class FixtureReplayer {
  private events: TimedEvent[];
  private cursor = 0;
  private playing = false;
  private startWall = 0;
  private baseTimeMs = 0;
  private raf = 0;

  constructor(events: TimedEvent[]) {
    this.events = events;
  }

  get maxMs() {
    return maxReplayTime(this.events);
  }

  play(onBatch: (events: GhostEvent[], timeMs: number) => void) {
    if (this.playing) return;
    this.playing = true;
    this.startWall = performance.now();
    const tick = () => {
      if (!this.playing) return;
      const elapsed = this.baseTimeMs + (performance.now() - this.startWall);
      const batch: GhostEvent[] = [];
      while (this.cursor < this.events.length && this.events[this.cursor].offsetMs <= elapsed) {
        const { offsetMs: _, ...ev } = this.events[this.cursor];
        batch.push(ev);
        this.cursor++;
      }
      if (batch.length) onBatch(batch, elapsed);
      else onBatch([], elapsed);
      if (this.cursor >= this.events.length && elapsed > this.maxMs + 500) {
        this.playing = false;
        return;
      }
      this.raf = requestAnimationFrame(tick);
    };
    this.raf = requestAnimationFrame(tick);
  }

  pause() {
    this.playing = false;
    cancelAnimationFrame(this.raf);
    this.baseTimeMs += performance.now() - this.startWall;
  }

  seek(timeMs: number, onReset: () => void, onBatch: (events: GhostEvent[], timeMs: number) => void) {
    this.pause();
    this.cursor = 0;
    this.baseTimeMs = timeMs;
    onReset();
    const batch = eventsUntilTime(this.events, timeMs);
    onBatch(batch, timeMs);
    this.cursor = batch.length;
  }

  destroy() {
    this.pause();
  }
}
