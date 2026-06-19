import * as THREE from 'three';

export function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

export function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

export function clamp(v: number, a: number, b: number): number {
  return Math.max(a, Math.min(b, v));
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function randRange(a: number, b: number): number {
  return a + Math.random() * (b - a);
}

export function pick<T>(arr: T[]): T {
  return arr[(Math.random() * arr.length) | 0];
}

export function viridis(t: number): [number, number, number] {
  const v = Math.max(0, Math.min(1, t));
  const stops: Array<[number, [number, number, number]]> = [
    [0.0, [0.267, 0.004, 0.329]],
    [0.25, [0.229, 0.322, 0.545]],
    [0.5, [0.127, 0.566, 0.550]],
    [0.75, [0.369, 0.788, 0.382]],
    [1.0, [0.993, 0.906, 0.144]]
  ];
  for (let i = 1; i < stops.length; i++) {
    if (v <= stops[i][0]) {
      const [x0, c0] = stops[i - 1];
      const [x1, c1] = stops[i];
      const k = (v - x0) / (x1 - x0);
      return [
        c0[0] + (c1[0] - c0[0]) * k,
        c0[1] + (c1[1] - c0[1]) * k,
        c0[2] + (c1[2] - c0[2]) * k
      ];
    }
  }
  return stops[stops.length - 1][1];
}

export interface TweenHandle {
  update(dt: number): boolean;
  cancel(): void;
}

export function tweenNumber(
  from: number,
  to: number,
  duration: number,
  onUpdate: (v: number) => void,
  easing: (t: number) => number = easeOutCubic
): TweenHandle {
  let elapsed = 0;
  let cancelled = false;
  return {
    update(dt: number): boolean {
      if (cancelled) return false;
      elapsed += dt;
      const t = Math.min(1, elapsed / duration);
      onUpdate(from + (to - from) * easing(t));
      return t < 1;
    },
    cancel() { cancelled = true; }
  };
}

export function tweenVec3(
  from: THREE.Vector3,
  to: THREE.Vector3,
  duration: number,
  onUpdate: (v: THREE.Vector3) => void,
  easing: (t: number) => number = easeOutCubic
): TweenHandle {
  let elapsed = 0;
  let cancelled = false;
  const tmp = new THREE.Vector3();
  return {
    update(dt: number): boolean {
      if (cancelled) return false;
      elapsed += dt;
      const t = Math.min(1, elapsed / duration);
      const k = easing(t);
      tmp.set(
        from.x + (to.x - from.x) * k,
        from.y + (to.y - from.y) * k,
        from.z + (to.z - from.z) * k
      );
      onUpdate(tmp);
      return t < 1;
    },
    cancel() { cancelled = true; }
  };
}
