import * as THREE from 'three';
import type { AppConfig, LaneId, LightState } from '../types';

export class MinimapRenderer {
  readonly canvas: HTMLCanvasElement;
  private readonly ctx: CanvasRenderingContext2D;
  private readonly config: AppConfig;

  constructor(canvas: HTMLCanvasElement, config: AppConfig) {
    this.canvas = canvas;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Canvas 2D not supported');
    this.ctx = ctx;
    this.config = config;
  }

  resize(w: number, h: number): void {
    this.canvas.width = w;
    this.canvas.height = h;
  }

  render(
    laneStates: Record<LaneId, LightState>,
    vehiclePositions: Array<{ x: number; z: number; lane: LaneId }>,
    selectedLane: LaneId | null,
    worldBounds: { minX: number; maxX: number; minZ: number; maxZ: number }
  ): void {
    const W = this.canvas.width;
    const H = this.canvas.height;
    const ctx = this.ctx;
    const pad = 14;
    const plotW = W - pad * 2;
    const plotH = H - pad * 2;

    const spanX = worldBounds.maxX - worldBounds.minX;
    const spanZ = worldBounds.maxZ - worldBounds.minZ;
    const span = Math.max(spanX, spanZ);
    const scale = Math.min(plotW, plotH) / span;
    const cx = W / 2;
    const cy = H / 2;

    const worldToScreen = (x: number, z: number): [number, number] => {
      return [cx + x * scale, cy + z * scale];
    };

    ctx.clearRect(0, 0, W, H);

    ctx.fillStyle = 'rgba(2, 6, 23, 0.85)';
    ctx.fillRect(0, 0, W, H);

    const border = 4;
    const { laneWidth, lanesPerDirection, roadLength, sidewalkWidth } = this.config.intersection;
    const half = laneWidth * lanesPerDirection;

    const rw = (half * 2 + sidewalkWidth * 2 + roadLength * 2) * scale;
    const rh = (laneWidth * lanesPerDirection * 2) * scale;

    ctx.fillStyle = '#2a2a2e';
    ctx.fillRect(cx - rw / 2, cy - rh / 2, rw, rh);
    ctx.fillRect(cx - rh / 2, cy - rw / 2, rh, rw);

    ctx.fillStyle = '#9ca3af';
    const sw = sidewalkWidth * scale;
    ctx.fillRect(cx - rw / 2, cy - rh / 2 - sw, rw, sw);
    ctx.fillRect(cx - rw / 2, cy + rh / 2, rw, sw);
    ctx.fillRect(cx - rh / 2 - sw, cy - rw / 2, sw, rw);
    ctx.fillRect(cx + rh / 2, cy - rw / 2, sw, rw);

    ctx.strokeStyle = '#eab308';
    ctx.lineWidth = 1.2;
    ctx.setLineDash([4, 3]);
    const laneScale = laneWidth * scale;
    for (let i = 1; i < lanesPerDirection * 2; i++) {
      if (i === lanesPerDirection) continue;
      const off = (i - lanesPerDirection) * laneScale;
      ctx.beginPath();
      ctx.moveTo(cx - rw / 2, cy + off);
      ctx.lineTo(cx + rw / 2, cy + off);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(cx + off, cy - rw / 2);
      ctx.lineTo(cx + off, cy + rw / 2);
      ctx.stroke();
    }
    ctx.setLineDash([]);

    const lightColor: Record<LightState, string> = {
      red: '#ef4444',
      yellow: '#eab308',
      green: '#22c55e'
    };

    const laneDraw: Array<{ lane: LaneId; draw: () => void }> = [
      { lane: 'N_s', draw: () => this._drawLightMarker(cx + laneScale * 0.5, cy - rh / 2 - 4, 3.5, lightColor[laneStates.N_s]) },
      { lane: 'N_l', draw: () => this._drawLightMarker(cx - laneScale * 0.5, cy - rh / 2 - 4, 3.5, lightColor[laneStates.N_l]) },
      { lane: 'S_s', draw: () => this._drawLightMarker(cx - laneScale * 0.5, cy + rh / 2 + 4, 3.5, lightColor[laneStates.S_s]) },
      { lane: 'S_l', draw: () => this._drawLightMarker(cx + laneScale * 0.5, cy + rh / 2 + 4, 3.5, lightColor[laneStates.S_l]) },
      { lane: 'E_s', draw: () => this._drawLightMarker(cx + rh / 2 + 4, cy - laneScale * 0.5, 3.5, lightColor[laneStates.E_s]) },
      { lane: 'E_l', draw: () => this._drawLightMarker(cx + rh / 2 + 4, cy + laneScale * 0.5, 3.5, lightColor[laneStates.E_l]) },
      { lane: 'W_s', draw: () => this._drawLightMarker(cx - rh / 2 - 4, cy + laneScale * 0.5, 3.5, lightColor[laneStates.W_s]) },
      { lane: 'W_l', draw: () => this._drawLightMarker(cx - rh / 2 - 4, cy - laneScale * 0.5, 3.5, lightColor[laneStates.W_l]) }
    ];
    for (const ld of laneDraw) ld.draw();

    if (selectedLane) {
      ctx.save();
      ctx.strokeStyle = 'rgba(96, 165, 250, 0.85)';
      ctx.lineWidth = 2;
      const hsz = laneScale;
      const sel: Record<LaneId, [number, number]> = {
        N_s: [cx + laneScale * 0.5, cy - (half * scale + 6)],
        N_l: [cx - laneScale * 0.5, cy - (half * scale + 6)],
        S_s: [cx - laneScale * 0.5, cy + (half * scale + 6)],
        S_l: [cx + laneScale * 0.5, cy + (half * scale + 6)],
        E_s: [cx + (half * scale + 6), cy - laneScale * 0.5],
        E_l: [cx + (half * scale + 6), cy + laneScale * 0.5],
        W_s: [cx - (half * scale + 6), cy + laneScale * 0.5],
        W_l: [cx - (half * scale + 6), cy - laneScale * 0.5]
      };
      const [sx, sy] = sel[selectedLane];
      ctx.strokeRect(sx - hsz, sy - hsz, hsz * 2, hsz * 2);
      ctx.restore();
    }

    ctx.fillStyle = 'rgba(248, 250, 252, 0.9)';
    for (const v of vehiclePositions) {
      const [sx, sy] = worldToScreen(v.x, v.z);
      if (sx < 0 || sx > W || sy < 0 || sy > H) continue;
      ctx.fillRect(sx - 1.5, sy - 1.5, 3, 3);
    }

    ctx.strokeStyle = 'rgba(148, 163, 184, 0.4)';
    ctx.lineWidth = 1;
    ctx.strokeRect(border, border, W - border * 2, H - border * 2);

    void worldToScreen; void border;
  }

  private _drawLightMarker(cx: number, cy: number, r: number, color: string): void {
    const ctx = this.ctx;
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.shadowColor = color;
    ctx.shadowBlur = 6;
    ctx.fill();
    ctx.restore();
  }
}
