"use client";

import { OrbitControls, useGLTF } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense, useMemo } from "react";
import * as THREE from "three";
import { normalizePreviewModel, previewMargin } from "@/lib/previewModel";
import type { SlotId } from "@/lib/types";

interface ModelViewerProps {
  url: string;
  className?: string;
  interactive?: boolean;
  autoRotate?: boolean;
  slot?: SlotId | string;
}

function MeshModel({ url, margin }: { url: string; margin: number }) {
  const { scene } = useGLTF(url);
  const model = useMemo(() => normalizePreviewModel(scene, margin), [scene, margin]);
  return <primitive object={model} />;
}

function Scene({
  url,
  interactive,
  autoRotate,
  margin,
}: {
  url: string;
  interactive: boolean;
  autoRotate: boolean;
  margin: number;
}) {
  const boost = interactive ? 1.35 : 1.0;

  return (
    <>
      <color attach="background" args={["#000000"]} />
      <ambientLight intensity={0.72 * boost} />
      <hemisphereLight args={["#d8dce8", "#14141a", 0.55 * boost]} />
      <directionalLight position={[5, 7, 6]} intensity={2.4 * boost} color="#fff8f0" />
      <directionalLight position={[-6, 3, 5]} intensity={1.35 * boost} color="#e8eeff" />
      <directionalLight position={[0, 4, -7]} intensity={1.1 * boost} color="#c8d4ff" />
      <directionalLight position={[0, -3, 4]} intensity={0.55 * boost} />
      <pointLight position={[2.5, 1.5, 4]} intensity={1.6 * boost} distance={24} decay={2} color="#ffffff" />
      <pointLight position={[-3, 2, 3]} intensity={1.0 * boost} distance={20} decay={2} color="#f0f4ff" />
      <Suspense fallback={null}>
        <MeshModel url={url} margin={margin} />
      </Suspense>
      <OrbitControls
        makeDefault
        target={[0, 0, 0]}
        autoRotate={autoRotate}
        autoRotateSpeed={interactive ? 0.8 : 1.4}
        enablePan={interactive}
        enableZoom={interactive}
        minDistance={interactive ? 0.35 : 2.2}
        maxDistance={interactive ? 12 : 2.2}
        enabled={interactive || autoRotate}
      />
    </>
  );
}

export function ModelViewer({
  url,
  className = "",
  interactive = false,
  autoRotate = true,
  slot,
}: ModelViewerProps) {
  const margin = previewMargin(interactive, slot);

  return (
    <div className={className}>
      <Canvas
        camera={{ position: [0, 0.12, 3.05], fov: 38, near: 0.01, far: 100 }}
        gl={{ antialias: true, alpha: false }}
        dpr={[1, 2]}
        onCreated={({ gl }) => {
          gl.toneMapping = THREE.ACESFilmicToneMapping;
          gl.toneMappingExposure = interactive ? 1.45 : 1.25;
          gl.outputColorSpace = THREE.SRGBColorSpace;
        }}
      >
        <Scene url={url} interactive={interactive} autoRotate={autoRotate} margin={margin} />
      </Canvas>
    </div>
  );
}
