"use client";

import { motion, useReducedMotion } from "motion/react";

/**
 * Scroll-triggered entrance.
 *
 * Deliberately small: 12px of travel over 600ms, once, never replayed. This is
 * a measurement instrument, so movement should feel like content settling into
 * place rather than a presentation. Anything showier competes with the data,
 * which is the only thing on the page worth looking at.
 *
 * `amount: 0.15` fires when a section is meaningfully on screen rather than the
 * instant its first pixel appears, which otherwise animates content the reader
 * cannot see yet.
 */
export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const reduce = useReducedMotion();

  if (reduce) return <div className={className}>{children}</div>;

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.15 }}
      transition={{ duration: 0.6, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
