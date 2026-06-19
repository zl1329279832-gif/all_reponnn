import * as THREE from 'three';

export type Direction = 'N' | 'S' | 'E' | 'W';
export type TurnKind = 's' | 'l';
export type LaneId = `${Direction}_${TurnKind}`;

export const ALL_LANES: LaneId[] = ['N_s', 'N_l', 'S_s', 'S_l', 'E_s', 'E_l', 'W_s', 'W_l'];

export interface PhaseConfig {
  name: string;
  directions: LaneId[];
  duration: number;
  yellow: number;
}

export interface SignalConfig {
  phases: PhaseConfig[];
  allRed: number;
}

export interface IntersectionConfig {
  laneWidth: number;
  lanesPerDirection: number;
  roadLength: number;
  sidewalkWidth: number;
}

export interface TrafficConfig {
  spawnRate: number;
  maxVehicles: number;
  cruiseSpeed: number;
  accel: number;
  decel: number;
  minGap: number;
  queueGap: number;
}

export interface HudConfig {
  historyTicks: number;
}

export interface AppConfig {
  intersection: IntersectionConfig;
  signal: SignalConfig;
  traffic: TrafficConfig;
  hud: HudConfig;
}

export type LightState = 'red' | 'yellow' | 'green';

export interface SignalState {
  phaseIndex: number;
  subTick: number;
  phaseName: string;
  laneStates: Record<LaneId, LightState>;
}

export interface Vehicle {
  id: number;
  lane: LaneId;
  x: number;
  z: number;
  heading: number;
  speed: number;
  targetSpeed: number;
  color: THREE.Color;
  queued: boolean;
  alive: boolean;
  turning: boolean;
  turningProgress: number;
  turnFrom: LaneId | null;
  length: number;
  width: number;
  progress: number;
  crossedStop: boolean;
}

export type RenderMode = 'solid' | 'particle' | 'heat' | 'wireframe';

export interface DirectionMetrics {
  throughput: number[];
  queueLength: number[];
}

export interface LaneWorldInfo {
  laneId: LaneId;
  stopX: number;
  stopZ: number;
  exitX: number;
  exitZ: number;
  dirX: number;
  dirZ: number;
  centerX: number;
  centerZ: number;
}
