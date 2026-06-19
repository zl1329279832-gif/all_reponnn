import * as THREE from 'three';
import type { Vehicle, RenderMode } from '../types';
import { viridis } from '../utils/tween';

export class InstancedVehicleRenderer {
  readonly instancedMesh: THREE.InstancedMesh;
  readonly particlePoints: THREE.Points;
  readonly baseGeometry: THREE.BufferGeometry;
  readonly baseMaterial: THREE.MeshStandardMaterial;
  readonly heatMaterial: THREE.MeshStandardMaterial;
  readonly wireframeMaterial: THREE.MeshStandardMaterial;

  readonly particleGeometry: THREE.BufferGeometry;
  readonly particleMaterial: THREE.PointsMaterial;

  private readonly _dummy = new THREE.Object3D();
  private readonly _color = new THREE.Color();
  private readonly _highlightColor = new THREE.Color(0x60a5fa);

  private _capacity: number;
  private _renderMode: RenderMode = 'solid';
  private _hoverInstanceId: number = -1;
  private _instanceIdMap: Map<number, number> = new Map();

  constructor(capacity: number) {
    this._capacity = capacity;

    this.baseGeometry = this._buildCarGeometry();

    this.baseMaterial = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.55,
      metalness: 0.25,
      wireframe: false
    });

    this.heatMaterial = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.4,
      metalness: 0.2,
      wireframe: false,
      emissiveIntensity: 0.6
    });

    this.wireframeMaterial = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.8,
      metalness: 0,
      wireframe: true
    });

    this.instancedMesh = new THREE.InstancedMesh(
      this.baseGeometry,
      this.baseMaterial,
      capacity
    );
    this.instancedMesh.castShadow = true;
    this.instancedMesh.receiveShadow = true;
    this.instancedMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    if (!this.instancedMesh.instanceColor) {
      this.instancedMesh.instanceColor = new THREE.InstancedBufferAttribute(
        new Float32Array(capacity * 3), 3
      );
    }
    this.instancedMesh.count = 0;

    this.particleGeometry = new THREE.BufferGeometry();
    this.particleGeometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(capacity * 3), 3));
    this.particleGeometry.setAttribute('color', new THREE.BufferAttribute(new Float32Array(capacity * 3), 3));

    this.particleMaterial = new THREE.PointsMaterial({
      size: 0.5,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      depthWrite: false,
      sizeAttenuation: true
    });

    this.particlePoints = new THREE.Points(this.particleGeometry, this.particleMaterial);
    this.particlePoints.visible = false;
  }

  private _buildCarGeometry(): THREE.BufferGeometry {
    const group = new THREE.Group();

    const body = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.55, 4.4));
    body.position.y = 0.55;
    body.castShadow = true;

    const cabin = new THREE.Mesh(new THREE.BoxGeometry(1.55, 0.5, 2.2));
    cabin.position.set(0, 1.0, -0.15);
    cabin.castShadow = true;

    const windshield = new THREE.Mesh(new THREE.BoxGeometry(1.45, 0.42, 0.08));
    windshield.position.set(0, 1.0, 0.92);
    windshield.rotation.x = -0.35;

    const rearWindow = windshield.clone();
    rearWindow.position.set(0, 1.0, -1.25);
    rearWindow.rotation.x = 0.35;

    group.add(body, cabin, windshield, rearWindow);

    const wheelGeo = new THREE.CylinderGeometry(0.33, 0.33, 0.24, 12);
    const wheelPositions = [
      [-0.82, 0.33, 1.45],
      [0.82, 0.33, 1.45],
      [-0.82, 0.33, -1.45],
      [0.82, 0.33, -1.45]
    ];
    for (const p of wheelPositions) {
      const w = new THREE.Mesh(wheelGeo);
      w.rotation.z = Math.PI / 2;
      w.position.set(p[0], p[1], p[2]);
      w.castShadow = true;
      group.add(w);
    }

    const headlight = new THREE.Mesh(new THREE.SphereGeometry(0.08, 8, 6));
    headlight.position.set(-0.55, 0.58, 2.2);
    (headlight.material as THREE.MeshStandardMaterial) = new THREE.MeshStandardMaterial({ color: 0xffffcc, emissive: 0xffffcc, emissiveIntensity: 0.6 });
    const h2 = headlight.clone();
    h2.position.x = 0.55;
    group.add(headlight, h2);

    const merged = new THREE.BufferGeometry();
    const matrices: THREE.Matrix4[] = [];
    const colorsAttr = new Float32Array(0);
    void colorsAttr;
    const allPositions: number[] = [];
    const allNormals: number[] = [];
    const allColors: number[] = [];
    const allIndices: number[] = [];
    let baseIndex = 0;

    const palettes: Record<string, [number, number, number]> = {
      body: [0.5, 0.5, 0.5],
      cabin: [0.35, 0.45, 0.6],
      glass: [0.15, 0.2, 0.28],
      wheel: [0.08, 0.08, 0.08],
      light: [0.9, 0.9, 0.4]
    };

    group.updateMatrixWorld(true);
    group.traverse(obj => {
      const m = obj as THREE.Mesh;
      if (!m.isMesh || !m.geometry) return;
      const geo = m.geometry;
      let tag = 'body';
      if (m === cabin) tag = 'cabin';
      else if (m === windshield || m === rearWindow) tag = 'glass';
      else if (m.geometry === wheelGeo) tag = 'wheel';
      else if (m === headlight || m === h2) tag = 'light';

      const pos = geo.getAttribute('position');
      const nrm = geo.getAttribute('normal');
      const idx = geo.getIndex();
      const palette = palettes[tag];

      const mtx = m.matrixWorld;
      const mArr = mtx.elements;

      if (idx) {
        for (let i = 0; i < idx.count; i++) {
          allIndices.push(baseIndex + idx.getX(i));
        }
      } else {
        for (let i = 0; i < pos.count; i++) allIndices.push(baseIndex + i);
      }

      for (let i = 0; i < pos.count; i++) {
        const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
        const tx = mArr[0] * x + mArr[4] * y + mArr[8] * z + mArr[12];
        const ty = mArr[1] * x + mArr[5] * y + mArr[9] * z + mArr[13];
        const tz = mArr[2] * x + mArr[6] * y + mArr[10] * z + mArr[14];
        allPositions.push(tx, ty, tz);

        const nx = nrm.getX(i), ny = nrm.getY(i), nz = nrm.getZ(i);
        const nnx = mArr[0] * nx + mArr[4] * ny + mArr[8] * nz;
        const nny = mArr[1] * nx + mArr[5] * ny + mArr[9] * nz;
        const nnz = mArr[2] * nx + mArr[6] * ny + mArr[10] * nz;
        allNormals.push(nnx, nny, nnz);

        allColors.push(palette[0], palette[1], palette[2]);
      }
      baseIndex += pos.count;
    });

    merged.setAttribute('position', new THREE.Float32BufferAttribute(allPositions, 3));
    merged.setAttribute('normal', new THREE.Float32BufferAttribute(allNormals, 3));
    merged.setAttribute('color', new THREE.Float32BufferAttribute(allColors, 3));
    merged.setIndex(allIndices);
    merged.computeVertexNormals();
    matrices;
    return merged;
  }

  setRenderMode(mode: RenderMode): void {
    this._renderMode = mode;
    switch (mode) {
      case 'solid':
        this.instancedMesh.material = this.baseMaterial;
        this.wireframeMaterial.wireframe = false;
        this.particlePoints.visible = false;
        break;
      case 'particle':
        this.instancedMesh.material = this.baseMaterial;
        this.particlePoints.visible = true;
        break;
      case 'heat':
        this.instancedMesh.material = this.heatMaterial;
        this.particlePoints.visible = false;
        break;
      case 'wireframe':
        this.instancedMesh.material = this.wireframeMaterial;
        this.wireframeMaterial.wireframe = true;
        this.particlePoints.visible = false;
        break;
    }
  }

  get renderMode(): RenderMode { return this._renderMode; }

  setHoverInstanceId(id: number): void {
    this._hoverInstanceId = id;
  }

  update(vehicles: Vehicle[], maxSpeed: number): void {
    const count = Math.min(vehicles.length, this._capacity);
    this.instancedMesh.count = count;
    this._instanceIdMap.clear();

    const posAttr = this.particleGeometry.getAttribute('position') as THREE.BufferAttribute;
    const colAttr = this.particleGeometry.getAttribute('color') as THREE.BufferAttribute;

    for (let i = 0; i < count; i++) {
      const v = vehicles[i];
      this._instanceIdMap.set(v.id, i);

      const d = this._dummy;
      d.position.set(v.x, 0, v.z);
      d.rotation.y = v.heading;
      const scale = 1;
      d.scale.set(scale, scale, scale);
      d.updateMatrix();
      this.instancedMesh.setMatrixAt(i, d.matrix);

      let r = v.color.r, g = v.color.g, b = v.color.b;

      if (this._renderMode === 'heat') {
        const t = Math.min(1, v.speed / Math.max(0.0001, maxSpeed));
        const [hr, hg, hb] = viridis(t);
        r = hr; g = hg; b = hb;
      }

      if (i === this._hoverInstanceId) {
        const k = 0.55;
        r = r * (1 - k) + this._highlightColor.r * k;
        g = g * (1 - k) + this._highlightColor.g * k;
        b = b * (1 - k) + this._highlightColor.b * k;
      }

      this._color.setRGB(r, g, b);
      this.instancedMesh.setColorAt(i, this._color);

      (posAttr.array as Float32Array)[i * 3] = v.x;
      (posAttr.array as Float32Array)[i * 3 + 1] = 1.0;
      (posAttr.array as Float32Array)[i * 3 + 2] = v.z;

      (colAttr.array as Float32Array)[i * 3] = r;
      (colAttr.array as Float32Array)[i * 3 + 1] = g;
      (colAttr.array as Float32Array)[i * 3 + 2] = b;
    }

    this.instancedMesh.instanceMatrix.needsUpdate = true;
    if (this.instancedMesh.instanceColor) {
      (this.instancedMesh.instanceColor as THREE.BufferAttribute).needsUpdate = true;
    }
    posAttr.needsUpdate = true;
    colAttr.needsUpdate = true;
    this.particleGeometry.setDrawRange(0, count);
  }

  dispose(): void {
    this.baseGeometry.dispose();
    this.baseMaterial.dispose();
    this.heatMaterial.dispose();
    this.wireframeMaterial.dispose();
    this.particleGeometry.dispose();
    this.particleMaterial.dispose();
    this.instancedMesh.dispose();
  }
}
