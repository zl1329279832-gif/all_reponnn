import './style.css';
import * as THREE from 'three';
import type { AppConfig, LaneId, RenderMode } from './types';
import { SceneManager } from './scene/SceneManager';
import { RoadBuilder } from './scene/RoadBuilder';
import { TrafficSignal } from './simulation/TrafficSignal';
import { VehicleManager } from './simulation/VehicleManager';
import { InstancedVehicleRenderer } from './render/InstancedVehicle';
import { InputManager } from './input/InputManager';
import { MinimapRenderer } from './render/MinimapRenderer';
import { HudCanvas } from './render/HudCanvas';

const RENDER_MODE_LABELS: Record<RenderMode, string> = {
  solid: '实体',
  particle: '粒子',
  heat: '热力',
  wireframe: '线框'
};

export class App {
  private readonly container: HTMLElement;
  private config!: AppConfig;
  private sceneMgr!: SceneManager;
  private road!: RoadBuilder;
  private signal!: TrafficSignal;
  private vehicles!: VehicleManager;
  private vehicleRenderer!: InstancedVehicleRenderer;
  private input!: InputManager;
  private minimap!: MinimapRenderer;
  private hud!: HudCanvas;

  private paused = false;
  private tickCount = 0;
  private renderMode: RenderMode = 'solid';
  private selectedLane: LaneId = 'N_s';

  private readonly tickEl: HTMLElement;
  private readonly phaseEl: HTMLElement;
  private readonly stateEl: HTMLElement;
  private readonly modeEl: HTMLElement;
  private readonly carEl: HTMLElement;
  private readonly selEl: HTMLElement;

  private _rafId = 0;
  private _lastFrameTime = 0;

  constructor(container: HTMLElement) {
    this.container = container;
    this.tickEl = document.getElementById('tick-val')!;
    this.phaseEl = document.getElementById('phase-val')!;
    this.stateEl = document.getElementById('state-val')!;
    this.modeEl = document.getElementById('mode-val')!;
    this.carEl = document.getElementById('car-val')!;
    this.selEl = document.getElementById('sel-val')!;
  }

  async init(): Promise<void> {
    try {
      const cfgResp = await fetch('/config.json');
      this.config = (await cfgResp.json()) as AppConfig;
    } catch (e) {
      console.error('Failed to load config.json, using defaults', e);
      this.config = this._defaultConfig();
    }

    this.sceneMgr = new SceneManager(this.container);
    this.road = new RoadBuilder(this.config);
    this.sceneMgr.scene.add(this.road.group);

    this.signal = new TrafficSignal(this.config);
    this.vehicles = new VehicleManager(this.config, this.signal, this.road.laneInfos);

    this.vehicleRenderer = new InstancedVehicleRenderer(this.config.traffic.maxVehicles);
    this.sceneMgr.scene.add(this.vehicleRenderer.instancedMesh);
    this.sceneMgr.scene.add(this.vehicleRenderer.particlePoints);

    this._buildSignalBulbUpdater();

    const mmCanvas = document.getElementById('minimap') as HTMLCanvasElement;
    const mmHit = document.getElementById('mm-hit') as HTMLElement;
    this.minimap = new MinimapRenderer(mmCanvas, this.config);

    const chartCanvas = document.getElementById('chart') as HTMLCanvasElement;
    const chartTitle = document.getElementById('chart-title') as HTMLElement;
    this.hud = new HudCanvas(chartCanvas, chartTitle, this.config);

    this.input = new InputManager(
      this.sceneMgr,
      this.road,
      this.vehicleRenderer,
      {
        onPauseToggle: () => { this.paused = !this.paused; this._updateStatusText(); },
        onModeChange: (m) => { this.renderMode = m; this.vehicleRenderer.setRenderMode(m); this._updateStatusText(); },
        onLaneSelect: (l) => { this.selectedLane = l; this._updateStatusText(); },
        onResetCamera: () => this.sceneMgr.resetCamera(),
        onMinimapClickLane: (l) => { void l; }
      },
      mmCanvas,
      mmHit,
      this.config
    );

    window.addEventListener('resize', this._onResize);
    this._onResize();

    this._updateStatusText();
  }

  private _buildSignalBulbUpdater(): void {
    const bulbs = this.road.getSignalBulbMeshes();
    if (bulbs.length < 12) return;

    const apply = () => {
      const cornerOrder: LaneId[] = ['N_s', 'N_l', 'S_s', 'S_l', 'E_s', 'E_l', 'W_s', 'W_l'];
      const stateMap = this.signal.getState().laneStates;
      const colorToBulbIdx: Record<string, number> = { red: 0, yellow: 1, green: 2 };
      for (let ci = 0; ci < 4; ci++) {
        for (let colorIdx = 0; colorIdx < 3; colorIdx++) {
          const bulb = bulbs[ci * 3 + colorIdx];
          const mat = bulb.material as THREE.MeshStandardMaterial;
          mat.emissiveIntensity = 0.12;
          (mat as any)._baseEmissiveIntensity = 0.12;
        }
      }
      void cornerOrder; void stateMap; void colorToBulbIdx;
    };
    apply();
  }

  private _onResize = (): void => {
    const mmCanvas = this.minimap.canvas;
    const mmRect = mmCanvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.minimap.resize(Math.max(1, Math.floor(mmRect.width * dpr)), Math.max(1, Math.floor(mmRect.height * dpr)));

    const hudCanvas = this.hud.canvas;
    const hudRect = hudCanvas.getBoundingClientRect();
    this.hud.resize(Math.max(1, Math.floor(hudRect.width * dpr)), Math.max(1, Math.floor(hudRect.height * dpr)));
  };

  private _defaultConfig(): AppConfig {
    return {
      intersection: { laneWidth: 3.5, lanesPerDirection: 2, roadLength: 80, sidewalkWidth: 4 },
      signal: {
        phases: [
          { name: '南北直行', directions: ['N_s', 'S_s'], duration: 200, yellow: 30 },
          { name: '南北左转', directions: ['N_l', 'S_l'], duration: 120, yellow: 30 },
          { name: '东西直行', directions: ['E_s', 'W_s'], duration: 200, yellow: 30 },
          { name: '东西左转', directions: ['E_l', 'W_l'], duration: 120, yellow: 30 }
        ],
        allRed: 20
      },
      traffic: {
        spawnRate: 0.35, maxVehicles: 300,
        cruiseSpeed: 0.35, accel: 0.008, decel: 0.025,
        minGap: 4.5, queueGap: 2.2
      },
      hud: { historyTicks: 60 }
    };
  }

  private _updateSignalBulbs(): void {
    const bulbs = this.road.getSignalBulbMeshes();
    if (bulbs.length < 12) return;
    const stateMap = this.signal.getState().laneStates;
    const cornerLanes = this.road.getBulbCornerLaneMap();
    for (const { corner, lanes } of cornerLanes) {
      let anyGreen = false;
      let anyYellow = false;
      let anyRed = false;
      for (const lane of lanes) {
        const st = stateMap[lane];
        if (st === 'green') anyGreen = true;
        else if (st === 'yellow') anyYellow = true;
        else anyRed = true;
      }
      const states: boolean[] = [anyRed, anyYellow, anyGreen];
      let colorIdx = 0;
      if (anyGreen) colorIdx = 2;
      else if (anyYellow) colorIdx = 1;
      else colorIdx = 0;
      for (let c = 0; c < 3; c++) {
        const b = bulbs[corner * 3 + c];
        if (!b) continue;
        const mat = b.material as THREE.MeshStandardMaterial;
        mat.emissiveIntensity = c === colorIdx ? 1.8 : 0.12;
      }
      void states;
    }
  }

  private _updateStatusText(): void {
    this.tickEl.textContent = String(this.tickCount);
    this.phaseEl.textContent = this.signal.phaseName;
    this.stateEl.textContent = this.paused ? '⏸ 暂停' : '▶ 运行';
    this.stateEl.style.color = this.paused ? '#f59e0b' : '#22c55e';
    this.modeEl.textContent = RENDER_MODE_LABELS[this.renderMode];
    this.carEl.textContent = String(this.vehicles.aliveCount);
    const labels: Record<LaneId, string> = {
      N_s: '北·直', N_l: '北·左', S_s: '南·直', S_l: '南·左',
      E_s: '东·直', E_l: '东·左', W_s: '西·直', W_l: '西·左'
    };
    this.selEl.textContent = labels[this.selectedLane];
  }

  start(): void {
    const loop = () => {
      this._rafId = requestAnimationFrame(loop);
      const now = performance.now();
      const dt = this._lastFrameTime === 0 ? 0.016 : Math.min(0.05, (now - this._lastFrameTime) / 1000);
      this._lastFrameTime = now;
      this._step(dt);
    };
    loop();
  }

  private _step(dt: number): void {
    if (!this.paused) {
      this.signal.advance();
      this.vehicles.advance();
      this.tickCount++;
    }

    this.vehicleRenderer.update(this.vehicles.vehicles, this.config.traffic.cruiseSpeed);
    this._updateSignalBulbs();

    this.input.update(dt);
    this.sceneMgr.render();

    const laneStates = this.signal.getState().laneStates;
    const positions = this.vehicles.vehicles.map(v => ({ x: v.x, z: v.z, lane: v.lane }));
    const rl = this.config.intersection.roadLength + this.config.intersection.laneWidth * this.config.intersection.lanesPerDirection + this.config.intersection.sidewalkWidth + 10;
    this.minimap.render(laneStates, positions, this.selectedLane, {
      minX: -rl, maxX: rl, minZ: -rl, maxZ: rl
    });

    const metrics = this.vehicles.history[this.selectedLane];
    if (metrics) this.hud.render(this.selectedLane, metrics);

    this._updateStatusText();
  }

  destroy(): void {
    cancelAnimationFrame(this._rafId);
    window.removeEventListener('resize', this._onResize);
    this.input.dispose();
    this.vehicleRenderer.dispose();
    this.road.dispose();
    this.sceneMgr.dispose();
  }
}
