"use client";

/** Confetti only for genuine success moments. Never used for routine CRUD. */

const COLORS = ["#2e90e5", "#0b2545", "#ffffff", "#4fa3f2"];

export async function celebrateSuccess(): Promise<void> {
  if (typeof window === "undefined") return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const { default: confetti } = await import("canvas-confetti");
  await confetti({
    particleCount: 72,
    spread: 56,
    startVelocity: 28,
    gravity: 1.05,
    origin: { y: 0.72 },
    colors: COLORS,
    disableForReducedMotion: true,
  });
}
