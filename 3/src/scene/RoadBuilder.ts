import * as THREE from 'three';
import type { AppConfig, LaneId, Direction, LaneWorldInfo } from '../types';

export class RoadBuilder {
  readonly group = new THREE.Group();
  readonly laneMeshes: Map<LaneId, THREE.Mesh> = new Map();
  readonly laneInfos: Map<LaneId, LaneWorldInfo> = new Map();
  readonly stopLineMeshes: Map<LaneId, THREE.Mesh> = new Map();
  readonly signalLights: { mesh: THREE.Mesh; lane: LaneId; color: 'red' | 'yellow' | 'green' }[] = [];

  private readonly cfg: AppConfig['intersection'];
  private readonly totalHalfRoad: number;

  constructor(config: AppConfig) {
    this.cfg = config.intersection;
    this.totalHalfRoad = this.cfg.laneWidth * this.cfg.lanesPerDirection * 2 / 2;
    this._build();
  }

  private _build(): void {
    this._buildRoadSurfaces();
    this._buildLaneMarkings();
    this._buildStopLines();
    this._buildSidewalks();
    this._buildCurbs();
    this._buildSignalLights();
    this._buildCrosswalks();
  }

  private _buildRoadSurfaces(): void {
    const { roadLength, laneWidth, lanesPerDirection } = this.cfg;
    const roadWidth = laneWidth * lanesPerDirection * 2;

    const roadMat = new THREE.MeshStandardMaterial({
      color: 0x2a2a2e,
      roughness: 0.92,
      metalness: 0.02
    });

    const horiz = new THREE.Mesh(new THREE.PlaneGeometry(roadLength * 2 + roadWidth, roadWidth), roadMat);
    horiz.rotation.x = -Math.PI / 2;
    horiz.position.y = 0.01;
    horiz.receiveShadow = true;
    this.group.add(horiz);

    const vert = new THREE.Mesh(new THREE.PlaneGeometry(roadWidth, roadLength * 2 + roadWidth), roadMat);
    vert.rotation.x = -Math.PI / 2;
    vert.position.y = 0.011;
    vert.receiveShadow = true;
    this.group.add(vert);

    this._buildLaneSurfaces();
  }

  private _buildLaneSurfaces(): void {
    const { laneWidth, lanesPerDirection, roadLength } = this.cfg;
    const halfIntersectHalf = laneWidth * lanesPerDirection;

    const laneMatBase = new THREE.MeshStandardMaterial({
      color: 0x32343a,
      roughness: 0.9,
      metalness: 0.02,
      transparent: true,
      opacity: 0.0
    });

    const dirs: Array<{ dir: Direction; lane: 's' | 'l'; sx: number; sz: number; hx: number; hz: number; ex: number; ez: number; heading: number }> = [];

    for (let i = 0; i < lanesPerDirection; i++) {
      const isLeftMost = i === 0;
      const sOffset = laneWidth * (i + 0.5) - halfIntersectHalf;
      dirs.push({
        dir: 'N', lane: isLeftMost ? 'l' : 's',
        sx: sOffset, sz: roadLength + halfIntersectHalf,
        hx: sOffset, hz: halfIntersectHalf + 0.1,
        ex: sOffset, ez: -halfIntersectHalf - 0.1,
        heading: Math.PI
      });
      dirs.push({
        dir: 'S', lane: isLeftMost ? 'l' : 's',
        sx: -sOffset - 0.001, sz: -roadLength - halfIntersectHalf,
        hx: -sOffset - 0.001, hz: -halfIntersectHalf - 0.1,
        ex: -sOffset - 0.001, ez: halfIntersectHalf + 0.1,
        heading: 0
      });
      dirs.push({
        dir: 'E', lane: isLeftMost ? 'l' : 's',
        sx: roadLength + halfIntersectHalf, sz: -sOffset - 0.001,
        hx: halfIntersectHalf + 0.1, hz: -sOffset - 0.001,
        ex: -halfIntersectHalf - 0.1, ez: -sOffset - 0.001,
        heading: -Math.PI / 2
      });
      dirs.push({
        dir: 'W', lane: isLeftMost ? 'l' : 's',
        sx: -roadLength - halfIntersectHalf, sz: sOffset,
        hx: -halfIntersectHalf - 0.1, hz: sOffset,
        ex: halfIntersectHalf + 0.1, ez: sOffset,
        heading: Math.PI / 2
      });
    }

    for (const d of dirs) {
      const laneId = `${d.dir}_${d.lane}` as LaneId;
      if (this.laneMeshes.has(laneId)) continue;

      const dx = d.ex - d.sx;
      const dz = d.ez - d.sz;
      const len = Math.hypot(dx, dz) + 4;
      const laneGeo = new THREE.PlaneGeometry(laneWidth * 0.95, len);
      const laneMat = laneMatBase.clone();
      (laneMat as THREE.MeshStandardMaterial).opacity = 0.0;
      const mesh = new THREE.Mesh(laneGeo, laneMat);
      mesh.rotation.x = -Math.PI / 2;
      mesh.position.set(
        (d.sx + d.ex) / 2,
        0.02,
        (d.sz + d.ez) / 2
      );
      const heading = Math.atan2(dz, dx);
      mesh.rotation.z = -heading;
      mesh.receiveShadow = true;
      mesh.userData = { kind: 'lane', laneId };
      this.group.add(mesh);
      this.laneMeshes.set(laneId, mesh);

      const stopX = d.hx;
      const stopZ = d.hz;
      const ndx = (d.ex - d.hx);
      const ndz = (d.ez - d.hz);
      const nlen = Math.hypot(ndx, ndz) || 1;
      this.laneInfos.set(laneId, {
        laneId,
        stopX,
        stopZ,
        exitX: d.ex,
        exitZ: d.ez,
        dirX: ndx / nlen,
        dirZ: ndz / nlen,
        centerX: d.sx,
        centerZ: d.sz
      });
    }
  }

  private _buildLaneMarkings(): void {
    const { laneWidth, lanesPerDirection, roadLength } = this.cfg;
    const halfIntersectHalf = laneWidth * lanesPerDirection;
    const white = 0xffffff;
    const yellow = 0xfacc15;

    const mkLine = (w: number, l: number, color: number, dashed = false) => {
      const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.95 });
      if (dashed) {
        return new THREE.Mesh(new THREE.PlaneGeometry(w, l), mat);
      }
      return new THREE.Mesh(new THREE.PlaneGeometry(w, l), mat);
    };

    for (let i = 1; i < lanesPerDirection * 2; i++) {
      if (i === lanesPerDirection) continue;
      const offset = i * laneWidth - halfIntersectHalf;
      const isCenter = i === lanesPerDirection;
      void isCenter;

      const g1 = mkLine(0.12, roadLength * 2, i === lanesPerDirection ? yellow : white, false);
      g1.rotation.x = -Math.PI / 2;
      g1.position.set(offset, 0.04, 0);
      this.group.add(g1);

      const g2 = mkLine(roadLength * 2, 0.12, i === lanesPerDirection ? yellow : white);
      g2.rotation.x = -Math.PI / 2;
      g2.position.set(0, 0.04, offset);
      this.group.add(g2);
    }

    for (let axis of ['x', 'z'] as const) {
      for (let sign of [-1, 1]) {
        for (let i = 0; i < lanesPerDirection; i++) {
          const base = sign * (i + 0.5) * laneWidth + sign * (sign > 0 ? 0 : -laneWidth * lanesPerDirection);
          void base;
        }
        void axis;
        void sign;
      }
    }

    const buildDashedAlong = (orientation: 'x' | 'z', laneIndex: number, sideMultiplier: number) => {
      const dashLen = 2;
      const gap = 2;
      const start = halfIntersectHalf + 3;
      const end = roadLength + halfIntersectHalf - 2;
      const pos = laneIndex * laneWidth - halfIntersectHalf + laneWidth / 2;
      for (let s = start; s < end; s += dashLen + gap) {
        if (orientation === 'x') {
          const d = mkLine(0.12, dashLen, white);
          d.rotation.x = -Math.PI / 2;
          d.position.set(pos, 0.045, s * sideMultiplier);
          this.group.add(d);
        } else {
          const d = mkLine(dashLen, 0.12, white);
          d.rotation.x = -Math.PI / 2;
          d.position.set(s * sideMultiplier, 0.045, pos);
          this.group.add(d);
        }
      }
    };

    for (let side of [-1, 1]) {
      for (let i = 0; i < lanesPerDirection * 2; i++) {
        if (i === lanesPerDirection) continue;
        buildDashedAlong('x', i, side);
        buildDashedAlong('z', i, side);
      }
    }
  }

  private _buildStopLines(): void {
    const { laneWidth, lanesPerDirection } = this.cfg;
    const halfIntersectHalf = laneWidth * lanesPerDirection;
    const stopDist = halfIntersectHalf + 0.4;
    const stopMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.95 });

    const builds: Array<{ lane: LaneId; x: number; z: number; rx: number; rz: number; heading: number }> = [
      { lane: 'N_s', x: laneWidth * 0.5 - halfIntersectHalf + laneWidth, z: stopDist, rx: laneWidth, rz: 0.35, heading: 0 },
      { lane: 'N_l', x: laneWidth * 0.5 - halfIntersectHalf, z: stopDist, rx: laneWidth, rz: 0.35, heading: 0 },
      { lane: 'S_s', x: -(laneWidth * 0.5 - halfIntersectHalf + laneWidth), z: -stopDist, rx: laneWidth, rz: 0.35, heading: 0 },
      { lane: 'S_l', x: -(laneWidth * 0.5 - halfIntersectHalf), z: -stopDist, rx: laneWidth, rz: 0.35, heading: 0 },
      { lane: 'E_s', x: stopDist, z: -(laneWidth * 0.5 - halfIntersectHalf + laneWidth), rx: 0.35, rz: laneWidth, heading: 0 },
      { lane: 'E_l', x: stopDist, z: -(laneWidth * 0.5 - halfIntersectHalf), rx: 0.35, rz: laneWidth, heading: 0 },
      { lane: 'W_s', x: -stopDist, z: laneWidth * 0.5 - halfIntersectHalf + laneWidth, rx: 0.35, rz: laneWidth, heading: 0 },
      { lane: 'W_l', x: -stopDist, z: laneWidth * 0.5 - halfIntersectHalf, rx: 0.35, rz: laneWidth, heading: 0 }
    ];

    for (const b of builds) {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(b.rx, b.rz), stopMat);
      m.rotation.x = -Math.PI / 2;
      m.position.set(b.x, 0.05, b.z);
      m.userData = { kind: 'stopline', laneId: b.lane };
      this.group.add(m);
      this.stopLineMeshes.set(b.lane, m);
    }
  }

  private _buildCrosswalks(): void {
    const { laneWidth, lanesPerDirection, sidewalkWidth } = this.cfg;
    const halfIntersectHalf = laneWidth * lanesPerDirection;
    const stripeMat = new THREE.MeshBasicMaterial({ color: 0xf4f4f4, transparent: true, opacity: 0.9 });
    const cwOffset = halfIntersectHalf + sidewalkWidth + 0.2;
    const cwLen = laneWidth * lanesPerDirection * 2;
    const stripeW = 0.4;
    const stripeGap = 0.55;
    for (let s = -cwLen / 2; s < cwLen / 2; s += stripeW + stripeGap) {
      for (let side of [-1, 1]) {
        const cx1 = new THREE.Mesh(new THREE.PlaneGeometry(cwOffset * 2 - 0.8, stripeW), stripeMat);
        cx1.rotation.x = -Math.PI / 2;
        cx1.position.set(s, 0.048, side * (halfIntersectHalf + sidewalkWidth / 2 + 0.1));
        this.group.add(cx1);
        const cz1 = new THREE.Mesh(new THREE.PlaneGeometry(stripeW, cwOffset * 2 - 0.8), stripeMat);
        cz1.rotation.x = -Math.PI / 2;
        cz1.position.set(side * (halfIntersectHalf + sidewalkWidth / 2 + 0.1), 0.048, s);
        this.group.add(cz1);
      }
    }
  }

  private _buildSidewalks(): void {
    const { laneWidth, lanesPerDirection, roadLength, sidewalkWidth } = this.cfg;
    const halfIntersectHalf = laneWidth * lanesPerDirection;
    const swMat = new THREE.MeshStandardMaterial({
      color: 0x9ca3af,
      roughness: 0.95
    });
    const inner = halfIntersectHalf;
    const outer = halfIntersectHalf + sidewalkWidth;
    const roadExt = roadLength + outer;
    const fullLen = roadExt * 2;

    const mkSidewalk = (w: number, l: number, px: number, pz: number) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, 0.18, l), swMat);
      m.position.set(px, 0.09, pz);
      m.receiveShadow = true;
      m.castShadow = true;
      this.group.add(m);
      return m;
    };

    mkSidewalk(sidewalkWidth, fullLen, -(inner + sidewalkWidth / 2), 0);
    mkSidewalk(sidewalkWidth, fullLen, (inner + sidewalkWidth / 2), 0);
    mkSidewalk(fullLen, sidewalkWidth, 0, -(inner + sidewalkWidth / 2));
    mkSidewalk(fullLen, sidewalkWidth, 0, (inner + sidewalkWidth / 2));

    void mkSidewalk;
  }

  private _buildCurbs(): void {
    const { laneWidth, lanesPerDirection, sidewalkWidth, roadLength } = this.cfg;
    const halfIntersectHalf = laneWidth * lanesPerDirection;
    const curbMat = new THREE.MeshStandardMaterial({ color: 0x5a6470, roughness: 0.9 });
    const inner = halfIntersectHalf;
    const outer = halfIntersectHalf + sidewalkWidth;
    void inner; void outer; void roadLength; void curbMat;
  }

  private _buildSignalLights(): void {
    const { laneWidth, lanesPerDirection, sidewalkWidth } = this.cfg;
    const halfIntersectHalf = laneWidth * lanesPerDirection;
    const poleMat = new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.7, metalness: 0.3 });
    const poleH = 6;
    const armLen = laneWidth * lanesPerDirection + 1;

    const corners = [
      { x: halfIntersectHalf + sidewalkWidth, z: halfIntersectHalf + sidewalkWidth, dir: 'NW', rotY: Math.PI },
      { x: -(halfIntersectHalf + sidewalkWidth), z: halfIntersectHalf + sidewalkWidth, dir: 'NE', rotY: -Math.PI / 2 },
      { x: halfIntersectHalf + sidewalkWidth, z: -(halfIntersectHalf + sidewalkWidth), dir: 'SW', rotY: Math.PI / 2 },
      { x: -(halfIntersectHalf + sidewalkWidth), z: -(halfIntersectHalf + sidewalkWidth), dir: 'SE', rotY: 0 }
    ];

    for (const c of corners) {
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.18, poleH, 8), poleMat);
      pole.position.set(c.x, poleH / 2, c.z);
      pole.castShadow = true;
      this.group.add(pole);

      const arm = new THREE.Mesh(new THREE.BoxGeometry(armLen, 0.12, 0.12), poleMat);
      const armDx = c.rotY === 0 ? -1 : c.rotY === Math.PI ? 1 : 0;
      const armDz = c.rotY === -Math.PI / 2 ? -1 : c.rotY === Math.PI / 2 ? 1 : 0;
      arm.position.set(c.x + armDx * armLen / 2, poleH - 0.5, c.z + armDz * armLen / 2);
      arm.rotation.y = c.rotY;
      this.group.add(arm);

      const lampGeo = new THREE.BoxGeometry(0.8, 0.9, 0.35);
      const lampBodyMat = new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.8 });
      const lamp = new THREE.Mesh(lampGeo, lampBodyMat);
      lamp.position.set(c.x + armDx * armLen, poleH - 0.5, c.z + armDz * armLen);
      this.group.add(lamp);

      const colors = [
        { name: 'red', y: 0.28, mat: new THREE.MeshStandardMaterial({ color: 0xef4444, emissive: 0x330000, emissiveIntensity: 0.2 }) },
        { name: 'yellow', y: 0, mat: new THREE.MeshStandardMaterial({ color: 0xeab308, emissive: 0x332900, emissiveIntensity: 0.2 }) },
        { name: 'green', y: -0.28, mat: new THREE.MeshStandardMaterial({ color: 0x22c55e, emissive: 0x003311, emissiveIntensity: 0.2 }) }
      ] as const;

      for (const col of colors) {
        const bulb = new THREE.Mesh(
          new THREE.SphereGeometry(0.13, 12, 10),
          col.mat
        );
        bulb.position.set(
          lamp.position.x,
          lamp.position.y + col.y,
          lamp.position.z + 0.18
        );
        (bulb.material as THREE.MeshStandardMaterial).emissiveIntensity = 0.15;
        this.group.add(bulb);
      }
    }

    this._bulbCornerOrder = corners.map(c => ({ x: c.x, z: c.z, rotY: c.rotY }));
  }

  private _bulbCornerOrder: Array<{ x: number; z: number; rotY: number }> = [];
  private _laneBulbIndex: Partial<Record<LaneId, { corner: number; light: 0 | 1 | 2 }>> = {
    N_s: { corner: 0, light: 0 },
    N_l: { corner: 0, light: 0 },
    S_s: { corner: 3, light: 0 },
    S_l: { corner: 3, light: 0 },
    E_s: { corner: 1, light: 0 },
    E_l: { corner: 1, light: 0 },
    W_s: { corner: 2, light: 0 },
    W_l: { corner: 2, light: 0 }
  };

  getBulbCornerLaneMap(): { corner: number; lanes: LaneId[] }[] {
    return [
      { corner: 0, lanes: ['N_s', 'N_l'] },
      { corner: 1, lanes: ['E_s', 'E_l'] },
      { corner: 2, lanes: ['W_s', 'W_l'] },
      { corner: 3, lanes: ['S_s', 'S_l'] }
    ];
  }

  getSignalBulbMeshes(): THREE.Mesh[] {
    return this.group.children.filter(c => {
      const m = c as THREE.Mesh;
      return m.geometry instanceof THREE.SphereGeometry && (m.material as THREE.MeshStandardMaterial)?.emissive !== undefined;
    }) as THREE.Mesh[];
  }

  setLaneHighlight(laneId: LaneId, highlight: boolean): void {
    const mesh = this.laneMeshes.get(laneId);
    if (!mesh) return;
    const mat = mesh.material as THREE.MeshStandardMaterial;
    mat.opacity = highlight ? 0.35 : 0.0;
    mat.color.set(highlight ? 0x60a5fa : 0x32343a);
    mat.needsUpdate = true;
  }

  dispose(): void {
    this.group.traverse(obj => {
      const m = obj as THREE.Mesh;
      if (m.geometry) m.geometry.dispose();
      if (m.material) {
        const mats = Array.isArray(m.material) ? m.material : [m.material];
        mats.forEach(mat => mat.dispose());
      }
    });
  }
}
