import * as THREE from 'three';
import type { AppConfig, LaneId, Direction, TurnKind, Vehicle, RenderMode, DirectionMetrics, LaneWorldInfo } from '../types';
import { TrafficSignal } from './TrafficSignal';
import { pick, randRange, clamp } from '../utils/tween';

const LANE_DIR_SIGN: Record<Direction, { x: number; z: number }> = {
  N: { x: 0, z: -1 },
  S: { x: 0, z: 1 },
  E: { x: -1, z: 0 },
  W: { x: 1, z: 0 }
};

const TURN_TARGET_MAP: Record<LaneId, LaneId | null> = {
  N_s: null,
  S_s: null,
  E_s: null,
  W_s: null,
  N_l: 'E_s',
  S_l: 'W_s',
  E_l: 'S_s',
  W_l: 'N_s'
};

const CAR_COLORS = [
  0x2563eb, 0xdc2626, 0xd1d5db, 0x111827, 0xf8fafc,
  0x7c3aed, 0xea580c, 0x0891b2, 0x16a34a, 0xa855f7
];

export class VehicleManager {
  readonly vehicles: Vehicle[] = [];
  readonly history: Record<LaneId, DirectionMetrics> = {} as any;
  readonly laneQueues: Record<LaneId, Vehicle[]> = {} as any;

  private readonly cfg: AppConfig;
  private readonly signal: TrafficSignal;
  private readonly laneInfos: Map<LaneId, LaneWorldInfo>;
  private _nextId = 1;

  throughputThisTick: Record<LaneId, number> = {} as any;
  queueCountThisTick: Record<LaneId, number> = {} as any;

  constructor(config: AppConfig, signal: TrafficSignal, laneInfos: Map<LaneId, LaneWorldInfo>) {
    this.cfg = config;
    this.signal = signal;
    this.laneInfos = laneInfos;

    const allLanes: LaneId[] = ['N_s', 'N_l', 'S_s', 'S_l', 'E_s', 'E_l', 'W_s', 'W_l'];
    for (const lane of allLanes) {
      this.laneQueues[lane] = [];
      this.history[lane] = { throughput: [], queueLength: [] };
      this.throughputThisTick[lane] = 0;
      this.queueCountThisTick[lane] = 0;
    }
  }

  get aliveCount(): number {
    let n = 0;
    for (const v of this.vehicles) if (v.alive) n++;
    return n;
  }

  private _spawn(laneId: LaneId): Vehicle | null {
    const info = this.laneInfos.get(laneId);
    if (!info) return null;

    const x = info.centerX;
    const z = info.centerZ;

    const queue = this.laneQueues[laneId];
    if (queue.length) {
      const last = queue[queue.length - 1];
      const dx = last.x - x;
      const dz = last.z - z;
      if (Math.hypot(dx, dz) < this.cfg.traffic.minGap + 2) return null;
    }

    const heading = Math.atan2(info.dirZ, info.dirX) + Math.PI / 2;
    const color = new THREE.Color(pick(CAR_COLORS));

    const v: Vehicle = {
      id: this._nextId++,
      lane: laneId,
      x,
      z,
      heading,
      speed: this.cfg.traffic.cruiseSpeed * 0.7,
      targetSpeed: this.cfg.traffic.cruiseSpeed,
      color,
      queued: false,
      alive: true,
      turning: false,
      turningProgress: 0,
      turnFrom: null,
      length: 4.5 + Math.random() * 0.8,
      width: 1.8 + Math.random() * 0.3,
      progress: 0,
      crossedStop: false
    };

    this.vehicles.push(v);
    queue.push(v);
    return v;
  }

  private _carPositionAlongLane(v: Vehicle, info: LaneWorldInfo): number {
    const dx = v.x - info.stopX;
    const dz = v.z - info.stopZ;
    return dx * info.dirX + dz * info.dirZ;
  }

  private _setPosFromAlong(v: Vehicle, info: LaneWorldInfo, along: number): void {
    v.x = info.stopX + info.dirX * along;
    v.z = info.stopZ + info.dirZ * along;
  }

  advance(): void {
    const tcfg = this.cfg.traffic;
    const allLanes: LaneId[] = ['N_s', 'N_l', 'S_s', 'S_l', 'E_s', 'E_l', 'W_s', 'W_l'];

    for (const lane of allLanes) this.throughputThisTick[lane] = 0;

    const spawnThreshold = Math.random();
    if (this.aliveCount < tcfg.maxVehicles) {
      if (spawnThreshold < tcfg.spawnRate) {
        const idx = Math.floor(Math.random() * allLanes.length);
        this._spawn(allLanes[idx]);
      }
    }

    for (const laneId of allLanes) {
      const queue = this.laneQueues[laneId];
      const info = this.laneInfos.get(laneId);
      if (!info) continue;

      const light = this.signal.laneState(laneId);
      const stopLineAlong = 0;

      for (let i = queue.length - 1; i >= 0; i--) {
        const v = queue[i];
        if (!v.alive) { queue.splice(i, 1); continue; }

        if (v.turning) {
          this._updateTurning(v);
          continue;
        }

        const along = this._carPositionAlongLane(v, info);

        let desiredSpeed = tcfg.cruiseSpeed;
        let mustStopAt: number | null = null;

        if (light !== 'green' && !v.crossedStop) {
          const stopPoint = stopLineAlong - 1.2;
          if (along > stopPoint) {
            mustStopAt = stopPoint;
          } else if (light === 'red') {
            mustStopAt = stopPoint;
          }
        }

        let frontAlong = Infinity;
        if (i > 0) {
          const front = queue[i - 1];
          if (!front.turning) {
            frontAlong = this._carPositionAlongLane(front, info);
          }
        }

        const frontCarStop = frontAlong - tcfg.minGap;
        if (mustStopAt !== null && !v.crossedStop) {
          const effStop = mustStopAt;
          const target = Math.max(effStop, frontCarStop);
          const distToStop = target - along;
          if (distToStop < 18) {
            const idealSpeed = Math.sqrt(2 * tcfg.decel * Math.max(0, distToStop));
            desiredSpeed = Math.min(desiredSpeed, idealSpeed);
          }
          if (along >= target - 0.3) {
            desiredSpeed = 0;
          }
        } else if (frontAlong !== Infinity) {
          const distToFront = frontAlong - along;
          if (distToFront < tcfg.minGap + 6) {
            const idealSpeed = Math.sqrt(2 * tcfg.decel * Math.max(0, distToFront - tcfg.queueGap));
            desiredSpeed = Math.min(desiredSpeed, idealSpeed);
          }
          if (distToFront <= tcfg.queueGap + 0.3) {
            desiredSpeed = 0;
          }
        }

        if (v.speed < desiredSpeed) {
          v.speed = Math.min(desiredSpeed, v.speed + tcfg.accel);
        } else {
          v.speed = Math.max(desiredSpeed, v.speed - tcfg.decel);
        }
        v.speed = clamp(v.speed, 0, tcfg.cruiseSpeed);

        v.queued = v.speed < 0.02;

        const newAlong = along + v.speed;
        if (!v.crossedStop && newAlong >= stopLineAlong) {
          v.crossedStop = true;
        }
        this._setPosFromAlong(v, info, newAlong);

        const exitAlong = (info.exitX - info.stopX) * info.dirX + (info.exitZ - info.stopZ) * info.dirZ + 1.5;
        if (newAlong >= exitAlong && !v.turning) {
          const turn = laneId[2] as TurnKind;
          if (turn === 'l') {
            this._startTurn(v, laneId);
          } else {
            v.alive = false;
            this.throughputThisTick[laneId]++;
          }
          queue.splice(i, 1);
        }
      }
    }

    for (let i = this.vehicles.length - 1; i >= 0; i--) {
      const v = this.vehicles[i];
      if (v.turning) {
        this._updateTurning(v);
      }
      if (!v.alive) this.vehicles.splice(i, 1);
    }

    for (const laneId of allLanes) {
      let qCount = 0;
      for (const v of this.laneQueues[laneId]) {
        if (v.queued) qCount++;
      }
      this.queueCountThisTick[laneId] = qCount;
      const hist = this.history[laneId];
      hist.throughput.push(this.throughputThisTick[laneId]);
      hist.queueLength.push(qCount);
      const max = this.cfg.hud.historyTicks;
      if (hist.throughput.length > max) hist.throughput.shift();
      if (hist.queueLength.length > max) hist.queueLength.shift();
    }
  }

  private _turnArcCenter(laneFrom: LaneId): { cx: number; cz: number; radius: number; startAngle: number; endAngle: number } | null {
    const info = this.laneInfos.get(laneFrom);
    const targetId = TURN_TARGET_MAP[laneFrom];
    if (!info || !targetId) return null;
    const tgt = this.laneInfos.get(targetId);
    if (!tgt) return null;
    const fromX = info.stopX - info.dirX * 1;
    const fromZ = info.stopZ - info.dirZ * 1;
    const toX = tgt.stopX + tgt.dirX * 1;
    const toZ = tgt.stopZ + tgt.dirZ * 1;
    const cx = (fromX + toX) / 2;
    const cz = (fromZ + toZ) / 2;
    const radius = Math.max(3.5, Math.hypot(toX - fromX, toZ - fromZ) / 2);
    const startAngle = Math.atan2(fromZ - cz, fromX - cx);
    const endAngle = Math.atan2(toZ - cz, toX - cx);
    return { cx, cz, radius, startAngle, endAngle };
  }

  private _startTurn(v: Vehicle, fromLane: LaneId): void {
    const arc = this._turnArcCenter(fromLane);
    if (!arc) { v.alive = false; return; }
    v.turning = true;
    v.turningProgress = 0;
    v.turnFrom = fromLane;
    (v as any)._arc = arc;
  }

  private _updateTurning(v: Vehicle): void {
    const arc = (v as any)._arc as ReturnType<typeof this._turnArcCenter>;
    if (!arc) { v.alive = false; return; }
    let start = arc.startAngle;
    let end = arc.endAngle;
    let diff = end - start;
    while (diff > Math.PI) diff -= Math.PI * 2;
    while (diff < -Math.PI) diff += Math.PI * 2;
    v.turningProgress += 0.014 + v.speed * 0.02;
    const p = clamp(v.turningProgress, 0, 1);
    const ang = start + diff * p;
    v.x = arc.cx + Math.cos(ang) * arc.radius;
    v.z = arc.cz + Math.sin(ang) * arc.radius;
    const tangent = ang + Math.PI / 2 * Math.sign(diff);
    v.heading = -tangent + Math.PI / 2;
    v.speed = Math.max(v.speed - 0.003, this.cfg.traffic.cruiseSpeed * 0.4);
    if (p >= 1) {
      const tgt = TURN_TARGET_MAP[v.turnFrom!];
      if (tgt) {
        v.lane = tgt;
        v.turning = false;
        v.turnFrom = null;
        v.crossedStop = true;
        (v as any)._arc = null;
        this.laneQueues[tgt].unshift(v);
        const tinfo = this.laneInfos.get(tgt);
        if (tinfo) {
          const along = 1.6;
          this._setPosFromAlong(v, tinfo, along);
          const heading = Math.atan2(tinfo.dirZ, tinfo.dirX) + Math.PI / 2;
          v.heading = heading;
        }
      } else {
        v.alive = false;
      }
    }
  }
}
