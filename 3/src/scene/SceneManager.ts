import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { clamp } from '../utils/tween';

export class SceneManager {
  readonly renderer: THREE.WebGLRenderer;
  readonly scene: THREE.Scene;
  readonly camera: THREE.PerspectiveCamera;
  readonly controls: OrbitControls;
  readonly container: HTMLElement;
  readonly clock = new THREE.Clock();
  readonly raycaster = new THREE.Raycaster();
  readonly mouseNDC = new THREE.Vector2();

  readonly initialCamPos = new THREE.Vector3(50, 55, 70);
  readonly initialCamTarget = new THREE.Vector3(0, 0, 0);

  constructor(container: HTMLElement) {
    this.container = container;

    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x8b9bb4);
    this.scene.fog = new THREE.Fog(0x8b9bb4, 70, 260);

    this.camera = new THREE.PerspectiveCamera(
      55,
      window.innerWidth / window.innerHeight,
      0.1,
      800
    );
    this.camera.position.copy(this.initialCamPos);
    this.camera.lookAt(this.initialCamTarget);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.minDistance = 25;
    this.controls.maxDistance = 180;
    this.controls.minPolarAngle = Math.PI * 0.35;
    this.controls.maxPolarAngle = Math.PI * 0.48;
    this.controls.target.copy(this.initialCamTarget);
    this.controls.update();

    this._setupLights();
    this._setupGround();
    window.addEventListener('resize', this._onResize);
  }

  private _setupLights(): void {
    const hemi = new THREE.HemisphereLight(0xbfd4ff, 0x4a5568, 0.9);
    hemi.position.set(0, 80, 0);
    this.scene.add(hemi);

    const sun = new THREE.DirectionalLight(0xfff3e0, 1.05);
    sun.position.set(60, 90, 40);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.near = 1;
    sun.shadow.camera.far = 300;
    sun.shadow.camera.left = -140;
    sun.shadow.camera.right = 140;
    sun.shadow.camera.top = 140;
    sun.shadow.camera.bottom = -140;
    sun.shadow.bias = -0.0005;
    this.scene.add(sun);

    const fill = new THREE.DirectionalLight(0xa6c8ff, 0.25);
    fill.position.set(-50, 40, -60);
    this.scene.add(fill);
  }

  private _setupGround(): void {
    const size = 500;
    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(size, size),
      new THREE.MeshStandardMaterial({
        color: 0x3a4733,
        roughness: 1,
        metalness: 0
      })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.01;
    ground.receiveShadow = true;
    this.scene.add(ground);

    const grid = new THREE.GridHelper(size, 100, 0x2f3f2a, 0x2a3a27);
    (grid.material as THREE.Material).opacity = 0.35;
    (grid.material as THREE.Material).transparent = true;
    grid.position.y = 0.001;
    this.scene.add(grid);
  }

  resetCamera(): void {
    this.camera.position.copy(this.initialCamPos);
    this.controls.target.copy(this.initialCamTarget);
    this.controls.update();
  }

  updateMouseFromEvent(ev: MouseEvent): void {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.mouseNDC.x = (ev.clientX - rect.left) / rect.width * 2 - 1;
    this.mouseNDC.y = -((ev.clientY - rect.top) / rect.height * 2 - 1);
  }

  private _onResize = (): void => {
    const w = window.innerWidth;
    const h = window.innerHeight;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  };

  resizeForMinimap(width: number, height: number) {
    this._onResize();
    void width; void height;
  }

  render(): void {
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  dispose(): void {
    window.removeEventListener('resize', this._onResize);
    this.controls.dispose();
    this.renderer.dispose();
  }
}

export function clamp2(v: number, a: number, b: number) { return clamp(v, a, b); }
