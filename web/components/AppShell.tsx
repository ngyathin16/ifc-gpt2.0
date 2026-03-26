"use client";
import { motion } from "framer-motion";

export default function AppShell({
  leftPanel,
  rightPanel,
}: {
  leftPanel: React.ReactNode;
  rightPanel: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden bg-canvas">
      {/* Left control panel */}
      <motion.aside
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="w-[380px] shrink-0 flex flex-col border-r border-border bg-panel overflow-y-auto"
      >
        {leftPanel}
      </motion.aside>

      {/* Right 3D canvas */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="flex-1 relative overflow-hidden"
      >
        {rightPanel}
      </motion.div>
    </div>
  );
}
