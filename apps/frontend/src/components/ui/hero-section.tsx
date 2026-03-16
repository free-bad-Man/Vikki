import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const Box = ({ position, rotation }) => {
    // Выносим создание геометрии из цикла рендера для производительности
    const shape = useMemo(() => {
        const s = new THREE.Shape();
        const radius = 1;
        s.absarc(2, 2, radius, 0, Math.PI * 0.5);
        s.absarc(-2, 2, radius, Math.PI * 0.5, Math.PI);
        s.absarc(-2, -2, radius, Math.PI, Math.PI * 1.5);
        s.absarc(2, -2, radius, Math.PI * 1.5, Math.PI * 2);
        return s;
    }, []);

    const extrudeSettings = useMemo(() => ({
        depth: 0.3,
        bevelEnabled: true,
        bevelThickness: 0.05,
        bevelSize: 0.05,
        bevelSegments: 15,
        curveSegments: 15
    }), []);

    return (
        <mesh position={position} rotation={rotation}>
            <extrudeGeometry args={[shape, extrudeSettings]} />
            <meshPhysicalMaterial 
                color="#1a1a1a"
                metalness={0.9}
                roughness={0.3}
                reflectivity={0.5}
                iridescence={1}
                iridescenceIOR={1.3}
            />
        </mesh>
    );
};

const AnimatedBoxes = () => {
    const groupRef = useRef<THREE.Group>(null);
    
    useFrame((state) => {
        if (groupRef.current) {
            // Математически точное вращение по времени, а не по кадрам
            const t = state.clock.getElapsedTime() * 0.08; 
            groupRef.current.rotation.x = t; 
        }
    });

    const boxes = useMemo(() => Array.from({ length: 46 }, (_, index) => ({
        position: [(index - 23) * 0.78, 0, 0] as [number, number, number],
        rotation: [(index - 10) * 0.12, Math.PI / 2, 0] as [number, number, number],
        id: index
    })), []);

    return (
        <group ref={groupRef}>
            {boxes.map((box) => (
                <Box key={box.id} position={box.position} rotation={box.rotation} />
            ))}
        </group>
    );
};

export const Scene = React.memo(() => {
    return (
        <div className="fixed inset-0 z-0 pointer-events-none opacity-40">
            <Canvas 
                camera={{ position: [5, 5, 20], fov: 40 }}
                gl={{ antialias: true, alpha: true }}
                dpr={[1, 2]}
            >
                <ambientLight intensity={10} />
                <directionalLight position={[10, 10, 5]} intensity={10} />
                <pointLight position={[-10, -10, -10]} color="#00d2ff" intensity={5} />
                <AnimatedBoxes />
            </Canvas>
        </div>
    );
});