/** Shared motion tokens. Keep durations in the 140–300ms product range. */

export const duration = {
  instant: 0.14,
  fast: 0.18,
  base: 0.22,
  slow: 0.3,
} as const;

export const easeOut = [0.22, 1, 0.36, 1] as const;

export const pageTransition = {
  duration: duration.base,
  ease: easeOut,
};

export const pressSpring = {
  type: "spring" as const,
  stiffness: 400,
  damping: 20,
};

export const cardTransition = {
  duration: duration.fast,
  ease: easeOut,
};

export const buttonHover = { scale: 1.02 };
export const buttonTap = { scale: 0.98 };
export const cardHover = { scale: 1.015 };

export const staggerContainer = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.045,
      delayChildren: 0.04,
    },
  },
};

export const staggerItem = {
  hidden: { opacity: 0, y: 10 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: duration.base, ease: easeOut },
  },
};

export const fadeScale = {
  hidden: { opacity: 0, y: 10, scale: 0.985 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: pageTransition,
  },
};

export const messageIn = {
  initial: { opacity: 0, y: 6 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: 4 },
  transition: { duration: duration.instant, ease: easeOut },
};
