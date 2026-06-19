import * as THREE from 'three';
import type { RenderMode, LaneId, Direction, TurnKind, AppConfig } from '../types';
import { SceneManager } from '../scene/SceneManager';
import { RoadBuilder } from '../scene/RoadBuilder';
import { InstancedVehicleRenderer } from '../render/InstancedVehicle';
import { TweenHandle, tweenVec3 } from '../utils/tween';

export interface InputCallbacks {
  onPauseToggle: () => void;
  onModeChange: (mode: RenderMode) => void;
  onLaneSelect: (laneId: LaneId) => void;
  onResetCamera: () => void;
  onMinimapClickLane: (laneId: LaneId) => void;
}

export class InputManager {
  private readonly sceneMgr: SceneManager;
  private readonly road: RoadBuilder;
  private readonly vehicles: InstancedVehicleRenderer;
  private readonly cb: InputCallbacks;
  private readonly minimapCanvas: HTMLCanvasElement;
  private readonly minimapHit: HTMLElement;
  private readonly config: AppConfig;

  private _tweens: TweenHandle[] = [];
  private _hoveredLane: LaneId | null = null;
  private _hoveredInstanceId: number = -1;

  paused = false;

  constructor(
    sceneMgr: SceneManager,
    road: RoadBuilder,
    vehicles: InstancedVehicleRenderer,
    callbacks: InputCallbacks,
    minimapCanvas: HTMLCanvasElement,
    minimapHitEl: HTMLElement,
    config: AppConfig
  ) {
    this.sceneMgr = sceneMgr;
    this.road = road;
    this.vehicles = vehicles;
    this.cb = callbacks;
    this.minimapCanvas = minimapCanvas;
    this.minimapHit = minimapHitEl;
    this.config = config;

    window.addEventListener('keydown', this._onKey);
    sceneMgr.renderer.domElement.addEventListener('mousemove', this._onMouseMove);
    sceneMgr.renderer.domElement.addEventListener('click', this._onClick);
    minimapCanvas.addEventListener('mousemove', this._onMinimapMove);
    minimapCanvas.addEventListener('click', this._onMinimapClick);
    minimapCanvas.addEventListener('mouseleave', this._onMinimapLeave);
  }

  private _onKey = (ev: KeyboardEvent): void => {
    if (ev.code === 'Space') {
      ev.preventDefault();
      this.cb.onPauseToggle();
      this.paused = !this.paused;
    } else if (ev.code === 'Digit1') {
      this.cb.onModeChange('particle');
    } else if (ev.code === 'Digit2') {
      this.cb.onModeChange('heat');
    } else if (ev.code === 'Digit3') {
      this.cb.onModeChange('wireframe');
    } else if (ev.code === 'Digit0' || ev.code === 'Escape') {
      this.cb.onResetCamera();
    }
  };

  private _onMouseMove = (ev: MouseEvent): void => {
    this.sceneMgr.updateMouseFromEvent(ev);
    this._doPick();
  };

  private _onClick = (): void => {
    const res = this._doPick(true);
    if (res?.lane) {
      this.cb.onLaneSelect(res.lane);
    }
  };

  private _doPick(click = false): { lane?: LaneId; instance?: number } | null {
    const { raycaster, mouseNDC, camera } = this.sceneMgr;
    raycaster.setFromCamera(mouseNDC, camera);

    const laneMeshes = Array.from(this.road.laneMeshes.values());
    const laneHits = raycaster.intersectObjects(laneMeshes, false);
    let pickedLane: LaneId | null = null;
    if (laneHits.length) {
      const ud = laneHits[0].object.userData as { kind?: string; laneId?: LaneId };
      if (ud?.laneId) pickedLane = ud.laneId;
    }

    if (pickedLane !== this._hoveredLane) {
      if (this._hoveredLane) this.road.setLaneHighlight(this._hoveredLane, false);
      if (pickedLane) this.road.setLaneHighlight(pickedLane, true);
      this._hoveredLane = pickedLane;
      if (click && pickedLane) return { lane: pickedLane };
    } else if (click && pickedLane) {
      return { lane: pickedLane };
    }

    const vehicleHits = raycaster.intersectObject(this.vehicles.instancedMesh, false);
    let instId = -1;
    if (vehicleHits.length && vehicleHits[0].instanceId !== undefined) {
      instId = vehicleHits[0].instanceId;
    }
    if (instId !== this._hoveredInstanceId) {
      this._hoveredInstanceId = instId;
      this.vehicles.setHoverInstanceId(instId);
    }
    return instId >= 0 ? { instance: instId } : null;
  }

  private _laneFromMinimapPoint(px: number, py: number): LaneId | null {
    const rect = this.minimapCanvas.getBoundingClientRect();
    const u = (px - rect.left) / rect.width;
    const v = (py - rect.top) / rect.height;
    const cx = u - 0.5;
    const cy = v - 0.5;
    const absX = Math.abs(cx);
    const absY = Math.abs(cy);
    if (absX < 0.12 && absY < 0.12) return null;

    if (absY > absX) {
      if (cy < 0) {
        return cx < 0 ? 'N_l' : 'N_s';
      } else {
        return cx < 0 ? 'S_s' : 'S_l';
      }
    } else {
      if (cx < 0) {
        return cy < 0 ? 'W_s' : 'W_l';
      } else {
        return cy < 0 ? 'E_l' : 'E_s';
      }
    }
  }

  private _onMinimapMove = (ev: MouseEvent): void => {
    const lane = this._laneFromMinimapPoint(ev.clientX, ev.clientY);
    if (lane) {
      this.minimapHit.style.boxShadow = `inset 0 0 0 2px rgba(96, 165, 250, 0.85)`;
    } else {
      this.minimapHit.style.boxShadow = `inset 0 0 0 0 rgba(96, 165, 250, 0)`;
    }
  };

  private _onMinimapLeave = (): void => {
    this.minimapHit.style.boxShadow = `inset 0 0 0 0 rgba(96, 165, 250, 0)`;
  };

  private _onMinimapClick = (ev: MouseEvent): void => {
    const lane = this._laneFromMinimapPoint(ev.clientX, ev.clientY);
    if (!lane) return;
    this.cb.onLaneSelect(lane);
    this.cb.onMinimapClickLane(lane);
    this.flyCameraToLane(lane);
  };

  flyCameraToLane(laneId: LaneId): void {
    const dir = laneId[0] as Direction;
    const turn = laneId[2] as TurnKind;
    void turn;
    const { laneWidth, lanesPerDirection, roadLength } = this.config.intersection;
    const half = laneWidth * lanesPerDirection;
    void half;

    const offsets: Record<Direction, [number, number]> = {
      N: [0, -1],
      S: [0, 1],
      E: [1, 0],
      W: [-1, 0]
    };
    const [sx, sz] = offsets[dir];
    const camDist = roadLength * 0.45 + 20;
    const height = 42;
    const fromPos = this.sceneMgr.camera.position.clone();
    const fromTarget = this.sceneMgr.controls.target.clone();
    const toPos = new THREE.Vector3(-sx * camDist * 0.85 + sz * camDist * 0.15, height, -sz * camDist * 0.85 + sx * camDist * 0.15);
    const toTarget = new THREE.Vector3(sx * 6, 0, sz * 6);

    this._tweens.forEach(t => t.cancel());
    this._tweens = [];

    this._tweens.push(tweenVec3(fromPos, toPos, 850, v => {
      this.sceneMgr.camera.position.copy(v);
    }));
    this._tweens.push(tweenVec3(fromTarget, toTarget, 850, v => {
      this.sceneMgr.controls.target.copy(v);
    }));
  }

  update(dt: number): void {
    this._tweens = this._tweens.filter(t => t.update(dt));
  }

  dispose(): void {
    window.removeEventListener('keydown', this._onKey);
    this.sceneMgr.renderer.domElement.removeEventListener('mousemove', this._onMouseMove);
    this.sceneMgr.renderer.domElement.removeEventListener('click', this._onClick);
    this.minimapCanvas.removeEventListener('mousemove', this._onMinimapMove);
    this.minimapCanvas.removeEventListener('click', this._onMinimapClick);
    this.minimapCanvas.removeEventListener('mouseleave', this._onMinimapLeave);
  }
}
