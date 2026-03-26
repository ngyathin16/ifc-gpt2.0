"use client";
import { useEffect, useRef } from "react";

interface Props {
  ifcUrl: string | null;
  onElementSelected?: (guids: string[]) => void;
}

export default function IFCViewer({ ifcUrl, onElementSelected }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const disposeRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (!containerRef.current || !ifcUrl) return;
    let cancelled = false;

    (async () => {
      const OBC  = await import("@thatopen/components");
      const OBCF = await import("@thatopen/components-front");

      const components = new OBC.Components();
      const worlds     = components.get(OBC.Worlds);
      const world      = worlds.create<
        OBC.SimpleScene,
        OBC.SimpleRenderer,
        OBC.SimpleCamera
      >();

      world.scene    = new OBC.SimpleScene(components);
      world.renderer = new OBC.SimpleRenderer(components, containerRef.current!);
      world.camera   = new OBC.SimpleCamera(components);
      (world.scene as any).setup?.();
      components.init();

      // Load IFC
      const loader = components.get(OBC.IfcLoader);
      await loader.setup();
      const res    = await fetch(ifcUrl);
      const buf    = await res.arrayBuffer();
      const model  = await loader.load(new Uint8Array(buf));

      // Fit camera
      const bbox   = components.get(OBC.BoundingBoxer);
      bbox.add(model);
      const sphere = bbox.getSphere();
      (world.camera as any).controls?.fitToSphere(sphere, true);
      bbox.reset();

      // Highlighter → GUID extraction
      if (onElementSelected && !cancelled) {
        const highlighter = components.get(OBCF.Highlighter);
        highlighter.setup({ world });
        highlighter.events.select.onHighlight.add((fragmentIdMap: Record<string, Set<number>>) => {
          const frags  = components.get(OBC.FragmentsManager);
          const guids: string[] = [];
          for (const [fragId, ids] of Object.entries(fragmentIdMap)) {
            const frag = frags.list.get(fragId);
            if (!frag) continue;
            for (const id of ids) {
              const guid = (frag as any).getItemGuid?.(id);
              if (guid) guids.push(guid);
            }
          }
          onElementSelected(guids);
        });
        highlighter.events.select.onClear.add(() => onElementSelected([]));
      }

      disposeRef.current = () => { try { components.dispose(); } catch {} };
    })();

    return () => {
      cancelled = true;
      disposeRef.current?.();
    };
  }, [ifcUrl]);

  return (
    <div
      ref={containerRef}
      className="w-full h-full bg-canvas"
      style={{ minHeight: "100%" }}
    />
  );
}
