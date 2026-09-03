import Image from "next/image";
import { cn } from "@/lib/utils/cn";

interface PompoMarkProps {
  className?: string;
  size?: number;
}

/** Official POMPO mark — blue P with green motion arrow. */
export function PompoMark({ className, size = 28 }: PompoMarkProps) {
  return (
    <Image
      src="/pompo-mark.png"
      alt=""
      width={size}
      height={size}
      unoptimized
      className={cn("shrink-0 rounded-lg", className)}
    />
  );
}
