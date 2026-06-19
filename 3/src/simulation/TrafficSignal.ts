import type { AppConfig, LaneId, SignalState, LightState } from '../types';

export class TrafficSignal {
  private readonly cfg: AppConfig['signal'];
  private _tick = 0;
  private _phaseIndex = 0;
  private _subTick = 0;
  private _phaseLaneStates: Record<LaneId, LightState> = {
    N_s: 'red', N_l: 'red', S_s: 'red', S_l: 'red',
    E_s: 'red', E_l: 'red', W_s: 'red', W_l: 'red'
  };

  private _inYellow = false;
  private _inAllRed = false;

  constructor(config: AppConfig) {
    this.cfg = config.signal;
    this._updateLaneStates();
  }

  get tick(): number { return this._tick; }
  get phaseIndex(): number { return this._phaseIndex; }
  get phaseName(): string { return this.cfg.phases[this._phaseIndex].name; }
  get subTick(): number { return this._subTick; }
  get inYellow(): boolean { return this._inYellow; }
  get inAllRed(): boolean { return this._inAllRed; }
  get phase(): AppConfig['signal']['phases'][number] { return this.cfg.phases[this._phaseIndex]; }

  laneState(laneId: LaneId): LightState {
    return this._phaseLaneStates[laneId];
  }

  isGreen(laneId: LaneId): boolean {
    return this._phaseLaneStates[laneId] === 'green';
  }

  getState(): SignalState {
    return {
      phaseIndex: this._phaseIndex,
      subTick: this._subTick,
      phaseName: this.phaseName,
      laneStates: { ...this._phaseLaneStates }
    };
  }

  advance(): void {
    this._tick++;
    this._subTick++;

    const phase = this.cfg.phases[this._phaseIndex];
    const greenEnds = phase.duration;
    const yellowEnds = phase.duration + phase.yellow;
    const allRedEnds = yellowEnds + this.cfg.allRed;

    if (this._subTick <= greenEnds) {
      if (this._inYellow || this._inAllRed) {
        this._inYellow = false;
        this._inAllRed = false;
        this._updateLaneStates();
      }
    } else if (this._subTick <= yellowEnds) {
      if (!this._inYellow) {
        this._inYellow = true;
        this._updateLaneStates();
      }
    } else if (this._subTick < allRedEnds) {
      if (!this._inAllRed) {
        this._inAllRed = true;
        this._inYellow = false;
        this._updateLaneStates();
      }
    } else {
      this._phaseIndex = (this._phaseIndex + 1) % this.cfg.phases.length;
      this._subTick = 0;
      this._inYellow = false;
      this._inAllRed = false;
      this._updateLaneStates();
    }
  }

  private _updateLaneStates(): void {
    const phase = this.cfg.phases[this._phaseIndex];
    const all: LaneId[] = ['N_s', 'N_l', 'S_s', 'S_l', 'E_s', 'E_l', 'W_s', 'W_l'];
    for (const lane of all) {
      if (this._inAllRed) {
        this._phaseLaneStates[lane] = 'red';
      } else if (this._inYellow) {
        if (phase.directions.includes(lane)) {
          this._phaseLaneStates[lane] = 'yellow';
        } else {
          this._phaseLaneStates[lane] = 'red';
        }
      } else {
        this._phaseLaneStates[lane] = phase.directions.includes(lane) ? 'green' : 'red';
      }
    }
  }
}
