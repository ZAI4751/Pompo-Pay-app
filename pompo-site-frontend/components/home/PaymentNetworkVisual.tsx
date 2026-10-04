"use client";

import { motion, useReducedMotion } from "framer-motion";

const NODES = [
  { id: "customer", label: "Customer", x: 40, y: 200 },
  { id: "hub", label: "POMPO", x: 260, y: 200 },
  { id: "provider", label: "Provider", x: 470, y: 100 },
  { id: "merchant", label: "Merchant", x: 470, y: 300 },
];

const PATHS = [
  { from: "customer", to: "hub", d: "M 78 200 L 220 200" },
  { from: "hub", to: "provider", d: "M 296 188 C 360 150, 400 130, 434 106" },
  { from: "hub", to: "merchant", d: "M 296 212 C 360 250, 400 270, 434 294" },
];

export default function PaymentNetworkVisual() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <svg
      viewBox="0 0 520 400"
      fill="none"
      className="h-full w-full"
      role="img"
      aria-label="Diagram showing a payment flowing from a customer, through POMPO, to a payment provider and then to a merchant"
    >
      <defs>
        <linearGradient id="brandLine" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#4338F5" />
          <stop offset="100%" stopColor="#9333EA" />
        </linearGradient>
        <linearGradient id="hubFill" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#4338F5" />
          <stop offset="100%" stopColor="#9333EA" />
        </linearGradient>
        <radialGradient id="hubGlow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#4338F5" stopOpacity="0.18" />
          <stop offset="100%" stopColor="#4338F5" stopOpacity="0" />
        </radialGradient>
      </defs>

      <circle cx="260" cy="200" r="110" fill="url(#hubGlow)" />

      {PATHS.map((p, i) => (
        <g key={p.from + p.to}>
          <motion.path
            d={p.d}
            stroke="#E4E4F0"
            strokeWidth={2}
            initial={false}
          />
          <motion.path
            d={p.d}
            stroke="url(#brandLine)"
            strokeWidth={2}
            strokeLinecap="round"
            initial={{ pathLength: prefersReducedMotion ? 1 : 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.1, delay: 0.4 + i * 0.25, ease: [0.22, 1, 0.36, 1] }}
          />
          {!prefersReducedMotion && (
            <motion.path
              d={p.d}
              stroke="#22BFBF"
              strokeWidth={3}
              strokeLinecap="round"
              strokeDasharray="6 220"
              initial={{ opacity: 0 }}
              animate={{ opacity: [0, 1, 1, 0], strokeDashoffset: [0, -226] }}
              transition={{
                duration: 2.6,
                delay: 1.6 + i * 0.5,
                repeat: Infinity,
                repeatDelay: 1.4,
                ease: "linear",
              }}
            />
          )}
        </g>
      ))}

      {NODES.map((node, i) => (
        <motion.g
          key={node.id}
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: i * 0.12 }}
        >
          <circle
            cx={node.x}
            cy={node.y}
            r={node.id === "hub" ? 38 : 26}
            fill={node.id === "hub" ? "url(#hubFill)" : "#FFFFFF"}
            stroke={node.id === "hub" ? "none" : "#E4E4F0"}
            strokeWidth={1.5}
          />
          <text
            x={node.x}
            y={node.y + (node.id === "hub" ? 58 : 46)}
            textAnchor="middle"
            className="fill-ink font-body text-[13px] font-medium"
          >
            {node.label}
          </text>
          {node.id === "hub" && (
            <text
              x={node.x}
              y={node.y + 5}
              textAnchor="middle"
              className="fill-white font-display text-[11px] font-semibold tracking-wide"
            >
              POMPO
            </text>
          )}
        </motion.g>
      ))}
    </svg>
  );
}
