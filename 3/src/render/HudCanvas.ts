import type { LaneId, DirectionMetrics, AppConfig } from '../types';

const LANE_LABELS: Record<LaneId, string> = {
  N_s: '北进口 · 直行',
  N_l: '北进口 · 左转',
  S_s: '南进口 · 直行',
  S_l: '南进口 · 左转',
  E_s: '东进口 · 直行',
  E_l: '东进口 · 左转',
  W_s: '西进口 · 直行',
  W_l: '西进口 · 左转'
};

export class HudCanvas {
  readonly canvas: HTMLCanvasElement;
  private readonly ctx: CanvasRenderingContext2D;
  private readonly titleEl: HTMLElement;
  private readonly config: AppConfig;

  constructor(canvas: HTMLCanvasElement, titleEl: HTMLElement, config: AppConfig) {
    this.canvas = canvas;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Canvas 2D not supported');
    this.ctx = ctx;
    this.titleEl = titleEl;
    this.config = config;
  }

  resize(w: number, h: number): void {
    this.canvas.width = w;
    this.canvas.height = h;
  }

  render(laneId: LaneId, metrics: DirectionMetrics): void {
    this.titleEl.textContent = `${LANE_LABELS[laneId]} · 最近 ${this.config.hud.historyTicks} tick`;

    const W = this.canvas.width;
    const H = this.canvas.height;
    const ctx = this.ctx;
    const padL = 28;
    const padR = 8;
    const padB = 22;

    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = 'rgba(2, 6, 23, 0.92)';
    ctx.fillRect(0, 0, W, H);

    const { throughput, queueLength } = metrics;
    const N = this.config.hud.historyTicks;
    const throughputPadded: number[] = [];
    const queuePadded: number[] = [];
    for (let i = 0; i < N; i++) {
      const di = i - (N - throughput.length);
      throughputPadded.push(di < 0 ? 0 : throughput[di] ?? 0);
      queuePadded.push(di < 0 ? 0 : queueLength[di] ?? 0);
    }

    const maxV = Math.max(1, ...throughputPadded, ...queuePadded);
    const ceil = Math.max(4, Math.ceil(maxV / 2) * 2);

    const plotX = padL;
    const plotY = 10;
    const plotW = W - padL - padR;
    const plotH = H - 26 - 10;

    ctx.strokeStyle = 'rgba(148, 163, 184, 0.18)';
    ctx.lineWidth = 1;
    const gridLines = 4;
    ctx.font = '10px "JetBrains Mono", Consolas, monospace';
    ctx.fillStyle = '#64748b';
    for (let i = 0; i <= gridLines; i++) {
      const y = plotY + (plotH * i) / gridLines;
      ctx.beginPath();
      ctx.moveTo(plotX, y);
      ctx.lineTo(plotX + plotW, y);
      ctx.stroke();
      const val = Math.round(ceil * (1 - i / gridLines));
      ctx.fillText(String(val), 2, y + 3);
    }

    ctx.strokeStyle = 'rgba(148, 163, 184, 0.25)';
    for (let i = 0; i <= 6; i++) {
      const x = plotX + (plotW * i) / 6;
      ctx.beginPath();
      ctx.moveTo(x, plotY);
      ctx.lineTo(x, plotY + plotH);
      ctx.stroke();
    }

    this._drawAreaLine(ctx, throughputPadded, plotX, plotY, plotW, plotH, ceil,
      'rgba(56, 189, 248, 0.18)', '#38bdf8');

    this._drawLine(ctx, queuePadded, plotX, plotY, plotW, plotH, ceil, '#f59e0b');

    ctx.fillStyle = '#64748b';
    ctx.font = '10px "JetBrains Mono", Consolas, monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`tick -${N}`, plotX, H - 6);
    ctx.fillText('tick -0', plotX + plotW, H - 6);
    ctx.textAlign = 'start';
  }

  private _drawLine(
    ctx: CanvasRenderingContext2D,
    data: number[],
    x0: number, y0: number, w: number, h: number,
    max: number, color: string
  ): void {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    for (let i = 0; i < data.length; i++) {
      const x = x0 + (w * i) / (data.length - 1);
      const y = y0 + h - (h * data[i]) / max;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.restore();
  }

  private _drawAreaLine(
    ctx: CanvasRenderingContext2D,
    data: number[],
    x0: number, y0: number, w: number, h: number,
    max: number, fillColor: string, strokeColor: string
  ): void {
    ctx.save();
    ctx.beginPath();
    const stepX = w / (data.length - 1);
    for (let i = 0; i < data.length; i++) {
      const x = x0 + stepX * i;
      const y = y0 + h - (h * data[i]) / max;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.lineTo(x0 + w, y0 + h);
    ctx.lineTo(x0, y0 + h);
    ctx.closePath();
    ctx.fillStyle = fillColor;
    ctx.fill();

    ctx.beginPath();
    for (let i = 0; i < data.length; i++) {
      const x = x0 + stepX * i;
      const y = y0 + h - (h * data[i]) / max;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.restore();
  }
}
