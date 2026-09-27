import { WebGLRenderer } from 'three';

/** Single swap point for WebGL2 vs future WebGPU (THREE_D §2). */
export function createRenderer(canvas: HTMLCanvasElement): WebGLRenderer {
  return new WebGLRenderer({
    canvas,
    antialias: true,
    alpha: false,
    powerPreference: 'high-performance',
  });
}
