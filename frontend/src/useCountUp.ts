import { useEffect, useRef, useState } from "react";

/** Animate a number from 0 to `target` with ease-out. Re-runs when target changes. */
export function useCountUp(target: number, duration = 900): number {
  const [value, setValue] = useState(0);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    const start = performance.now();
    const from = 0;
    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3); // easeOutCubic
      setValue(from + (target - from) * eased);
      if (t < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    // Guarantee the final value even if rAF is throttled (background tab,
    // headless virtual time, reduced-motion environments).
    const settle = window.setTimeout(() => setValue(target), duration + 50);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
      clearTimeout(settle);
    };
  }, [target, duration]);

  return value;
}
