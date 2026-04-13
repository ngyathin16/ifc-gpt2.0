"use client";
import { useEffect, useRef, useState, useCallback } from "react";
import { motion } from "framer-motion";
import type { Group, PerspectiveCamera, Scene, WebGLRenderer, Mesh, Material, MeshStandardMaterial, Object3D } from "three";
import type { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import {
  RotateCcw,
  Maximize2,
  Box,
  Grid3X3,
  Eye,
} from "lucide-react";

type ViewMode = "solid" | "wireframe" | "xray";

interface Props {
  ifcUrl: string | null;
  onElementSelected?: (guids: string[]) => void;
}

const WEB_IFC_WASM_PATH = "/web-ifc.wasm";

const VIEW_MODES: { id: ViewMode; label: string; icon: React.ReactNode }[] = [
  { id: "solid", label: "Solid", icon: <Box className="h-3.5 w-3.5" /> },
  { id: "wireframe", label: "Wireframe", icon: <Grid3X3 className="h-3.5 w-3.5" /> },
  { id: "xray", label: "X-Ray", icon: <Eye className="h-3.5 w-3.5" /> },
];

export default function IFCViewer({ ifcUrl, onElementSelected }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const disposeRef = useRef<(() => void) | null>(null);
  const sceneRef = useRef<{
    root: Group;
    camera: PerspectiveCamera;
    controls: OrbitControls;
    scene: Scene;
    renderer: WebGLRenderer;
    originalMaterials: Map<Mesh, Material>;
  } | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("solid");

  const applyViewMode = useCallback((mode: ViewMode) => {
    const ctx = sceneRef.current;
    if (!ctx) return;
    const THREE = (window as any).__THREE__;
    if (!THREE) return;

    ctx.root.traverse((child: Object3D) => {
      if (!(child instanceof THREE.Mesh)) return;
      const m = child as Mesh;

      if (!ctx.originalMaterials.has(m)) {
        ctx.originalMaterials.set(m, (m.material as Material).clone());
      }
      const orig = ctx.originalMaterials.get(m)! as MeshStandardMaterial;

      switch (mode) {
        case "solid": {
          const mat = orig.clone();
          mat.wireframe = false;
          mat.transparent = false;
          mat.opacity = 1.0;
          mat.depthWrite = true;
          mat.needsUpdate = true;
          m.material = mat;
          break;
        }
        case "wireframe": {
          const mat = orig.clone();
          mat.wireframe = true;
          mat.transparent = false;
          mat.opacity = 1.0;
          mat.needsUpdate = true;
          m.material = mat;
          break;
        }
        case "xray": {
          m.material = new THREE.MeshStandardMaterial({
            color: orig.color ?? new THREE.Color(0xb8c4d6),
            metalness: 0.0,
            roughness: 0.6,
            transparent: true,
            opacity: 0.15,
            side: THREE.DoubleSide,
            depthWrite: false,
          });
          (m.material as MeshStandardMaterial).needsUpdate = true;
          break;
        }
      }
    });
  }, []);

  const handleViewModeChange = useCallback(
    (mode: ViewMode) => {
      setViewMode(mode);
      applyViewMode(mode);
    },
    [applyViewMode]
  );

  const handleResetView = useCallback(() => {
    const ctx = sceneRef.current;
    if (!ctx) return;
    const THREE = (window as any).__THREE__;
    if (!THREE) return;

    const bbox = new THREE.Box3().setFromObject(ctx.root);
    if (bbox.isEmpty()) return;
    const center = new THREE.Vector3();
    bbox.getCenter(center);
    const size = new THREE.Vector3();
    bbox.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z, 1);

    ctx.camera.position.set(
      center.x + maxDim * 1.5,
      center.y + maxDim * 1.2,
      center.z + maxDim * 1.5
    );
    ctx.camera.lookAt(center);
    ctx.camera.updateProjectionMatrix();
    if (ctx.controls) {
      ctx.controls.target.copy(center);
      ctx.controls.update();
    }
  }, []);

  const handleFitView = useCallback(() => {
    const ctx = sceneRef.current;
    if (!ctx) return;
    const THREE = (window as any).__THREE__;
    if (!THREE) return;

    const bbox = new THREE.Box3().setFromObject(ctx.root);
    if (bbox.isEmpty()) return;
    const center = new THREE.Vector3();
    bbox.getCenter(center);
    const size = new THREE.Vector3();
    bbox.getSize(size);
    const maxDim = Math.max(size.x, size.y, size.z, 1);
    const fov = ctx.camera.fov * (Math.PI / 180);
    const dist = maxDim / (2 * Math.tan(fov / 2)) * 1.3;

    const dir = new THREE.Vector3()
      .subVectors(ctx.camera.position, center)
      .normalize();
    ctx.camera.position.copy(center).addScaledVector(dir, dist);
    ctx.camera.lookAt(center);
    ctx.camera.updateProjectionMatrix();
    if (ctx.controls) {
      ctx.controls.target.copy(center);
      ctx.controls.update();
    }
  }, []);

  useEffect(() => {
    if (!containerRef.current || !ifcUrl) return;
    let cancelled = false;
    disposeRef.current?.();
    disposeRef.current = null;
    sceneRef.current = null;
    setStatus("loading");
    setErrorMsg("");
    setViewMode("solid");

    (async () => {
      try {
        const THREE = await import("three");
        const { OrbitControls } = await import("three/examples/jsm/controls/OrbitControls.js");
        const { IfcAPI } = await import("web-ifc");

        // Store THREE globally so callbacks can use it
        (window as any).__THREE__ = THREE;

        const container = containerRef.current!;
        const width = container.clientWidth || 800;
        const height = container.clientHeight || 600;

        const res = await fetch(ifcUrl);
        if (!res.ok) throw new Error(`Failed to fetch IFC: ${res.status}`);
        const bytes = new Uint8Array(await res.arrayBuffer());

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x202830);

        const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100000);
        camera.position.set(12, 10, 12);

        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
        renderer.setPixelRatio(window.devicePixelRatio || 1);
        renderer.setSize(width, height);
        container.replaceChildren(renderer.domElement);

        // OrbitControls for rotation, zoom, pan
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.08;
        controls.enablePan = true;
        controls.enableZoom = true;
        controls.enableRotate = true;
        controls.minDistance = 0.5;
        controls.maxDistance = 50000;
        controls.mouseButtons = {
          LEFT: THREE.MOUSE.ROTATE,
          MIDDLE: THREE.MOUSE.DOLLY,
          RIGHT: THREE.MOUSE.PAN,
        };

        const ambient = new THREE.AmbientLight(0xffffff, 1.1);
        scene.add(ambient);
        const directional = new THREE.DirectionalLight(0xffffff, 1.4);
        directional.position.set(10, 20, 10);
        scene.add(directional);
        const fillLight = new THREE.DirectionalLight(0xffffff, 0.4);
        fillLight.position.set(-10, 5, -10);
        scene.add(fillLight);

        const root = new THREE.Group();
        scene.add(root);

        const ifcApi = new IfcAPI();
        const wasmDir = new URL("/", window.location.origin).toString();
        ifcApi.SetWasmPath(wasmDir, true);
        await ifcApi.Init();
        const modelID = ifcApi.OpenModel(bytes, {
          COORDINATE_TO_ORIGIN: true,
        });
        if (modelID === -1) {
          throw new Error("web-ifc failed to open this IFC file — it may be corrupt or use an unsupported schema");
        }
        let meshCount = 0;
        let flatMeshCount = 0;

        const processFlatMesh = (flatMesh: any) => {
          flatMeshCount += 1;
          const placedGeometries = flatMesh.geometries;
          for (let j = 0; j < placedGeometries.size(); j += 1) {
            const pg = placedGeometries.get(j);
            const geo = ifcApi.GetGeometry(modelID, pg.geometryExpressID);
            const vPtr = geo.GetVertexData();
            const vSize = geo.GetVertexDataSize();
            const iPtr = geo.GetIndexData();
            const iSize = geo.GetIndexDataSize();

            if (vSize === 0 || iSize === 0) {
              try { geo.delete(); } catch { /* noop */ }
              continue;
            }

            const vertexData = ifcApi.GetVertexArray(vPtr, vSize);
            const indexData = ifcApi.GetIndexArray(iPtr, iSize);

            const positions: number[] = [];
            const normals: number[] = [];
            for (let k = 0; k < vertexData.length; k += 6) {
              positions.push(vertexData[k], vertexData[k + 1], vertexData[k + 2]);
              normals.push(vertexData[k + 3], vertexData[k + 4], vertexData[k + 5]);
            }

            const bufferGeometry = new THREE.BufferGeometry();
            bufferGeometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
            bufferGeometry.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
            bufferGeometry.setIndex(Array.from(indexData));
            bufferGeometry.computeBoundingBox();
            bufferGeometry.computeBoundingSphere();

            const c = pg.color;
            const color = new THREE.Color(c.x, c.y, c.z);
            const material = new THREE.MeshStandardMaterial({
              color,
              metalness: 0.05,
              roughness: 0.75,
              transparent: c.w < 1,
              opacity: c.w,
              side: THREE.DoubleSide,
            });

            const mesh = new THREE.Mesh(bufferGeometry, material);
            const transform = new THREE.Matrix4().fromArray(Array.from(pg.flatTransformation));
            mesh.applyMatrix4(transform);
            root.add(mesh);
            meshCount += 1;
            try { geo.delete(); } catch { /* noop */ }
          }
        };

        // StreamAllMeshes is more reliable than LoadAllGeometry in web-ifc 0.0.77+
        ifcApi.StreamAllMeshes(modelID, processFlatMesh);

        console.info(`[IFCViewer] flatMeshes=${flatMeshCount}, meshes=${meshCount}, allLines=${ifcApi.GetAllLines(modelID).size()}`);

        if (meshCount === 0) {
          const lineCount = ifcApi.GetAllLines(modelID).size();
          throw new Error(
            `IFC model has ${lineCount} entities but no extractable geometry. ` +
            `The file may lack 3D shape representations.`
          );
        }

        const bbox = new THREE.Box3().setFromObject(root);
        if (bbox.isEmpty()) {
          throw new Error("IFC loaded but no visible geometry was extracted");
        }

        const center = new THREE.Vector3();
        bbox.getCenter(center);
        const size = new THREE.Vector3();
        bbox.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z, 1);
        camera.position.set(center.x + maxDim * 1.5, center.y + maxDim * 1.2, center.z + maxDim * 1.5);
        camera.lookAt(center);
        camera.updateProjectionMatrix();
        controls.target.copy(center);
        controls.update();

        // Store scene refs for view mode controls
        sceneRef.current = {
          root,
          camera,
          controls,
          scene,
          renderer,
          originalMaterials: new Map(),
        };

        let animationFrame = 0;
        const renderLoop = () => {
          if (cancelled) return;
          controls.update();
          renderer.render(scene, camera);
          animationFrame = window.requestAnimationFrame(renderLoop);
        };
        renderLoop();

        if (cancelled) return;

        const ro = new ResizeObserver(() => {
          const w = container.clientWidth;
          const h = container.clientHeight;
          if (w > 0 && h > 0) {
            camera.aspect = w / h;
            camera.updateProjectionMatrix();
            renderer.setSize(w, h);
          }
        });
        ro.observe(container);

        if (!cancelled) setStatus("ready");

        disposeRef.current = () => {
          window.cancelAnimationFrame(animationFrame);
          ro.disconnect();
          controls.dispose();
          ifcApi?.CloseModel(modelID);
          ifcApi?.Dispose();
          root.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              child.geometry.dispose();
              const material = child.material;
              if (Array.isArray(material)) {
                material.forEach((item) => item.dispose());
              } else {
                material.dispose();
              }
            }
          });
          renderer.dispose();
          container.replaceChildren();
          sceneRef.current = null;
        };
      } catch (err: any) {
        console.error("IFCViewer error:", err);
        if (!cancelled) {
          setStatus("error");
          setErrorMsg(err instanceof Error ? err.message : "Unknown error");
        }
      }
    })();

    return () => {
      cancelled = true;
      disposeRef.current?.();
    };
  }, [ifcUrl]);

  return (
    <div className="relative w-full h-full">
      <div
        ref={containerRef}
        className="absolute inset-0"
      />

      {/* View controls toolbar — bottom-left */}
      {status === "ready" && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="absolute bottom-3 left-3 flex items-center gap-1.5 z-10"
        >
          {/* View mode switcher */}
          <div className="flex items-center rounded-lg bg-black/50 backdrop-blur border border-white/10 overflow-hidden">
            {VIEW_MODES.map((mode) => (
              <button
                key={mode.id}
                onClick={() => handleViewModeChange(mode.id)}
                title={mode.label}
                className={`flex items-center gap-1.5 px-2.5 py-2 text-xs transition-all ${
                  viewMode === mode.id
                    ? "bg-accent/30 text-white"
                    : "text-white/60 hover:text-white hover:bg-white/10"
                }`}
              >
                {mode.icon}
                <span className="hidden sm:inline">{mode.label}</span>
              </button>
            ))}
          </div>

          {/* Reset / Fit buttons */}
          <div className="flex items-center rounded-lg bg-black/50 backdrop-blur border border-white/10 overflow-hidden">
            <button
              onClick={handleResetView}
              title="Reset view"
              className="flex items-center gap-1.5 px-2.5 py-2 text-xs text-white/60 hover:text-white hover:bg-white/10 transition-all"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={handleFitView}
              title="Fit to view"
              className="flex items-center gap-1.5 px-2.5 py-2 text-xs text-white/60 hover:text-white hover:bg-white/10 transition-all"
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </motion.div>
      )}

      {/* Navigation hint — bottom-right */}
      {status === "ready" && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="absolute bottom-3 right-3 z-10 text-[10px] text-white/30 bg-black/30 backdrop-blur rounded px-2 py-1 pointer-events-none"
        >
          LMB: Rotate · MMB: Zoom · RMB: Pan
        </motion.div>
      )}

      {status === "loading" && (
        <div className="absolute inset-0 flex items-center justify-center bg-canvas/80 z-10 pointer-events-none">
          <div className="text-sm text-muted animate-pulse">Loading model…</div>
        </div>
      )}
      {status === "error" && (
        <div className="absolute inset-0 flex items-center justify-center bg-canvas/80 z-10">
          <div className="text-center">
            <p className="text-sm text-red-400">Failed to load model</p>
            <p className="text-xs text-muted/60 mt-1 max-w-xs">{errorMsg}</p>
          </div>
        </div>
      )}
    </div>
  );
}
