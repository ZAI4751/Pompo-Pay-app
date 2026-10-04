import Image from "next/image";
import Link from "next/link";

export default function Logo({ className = "" }: { className?: string }) {
  return (
    <Link href="/" className={`flex items-center gap-2.5 ${className}`} aria-label="POMPO home">
      <Image
        src="/pompo-mark.png"
        alt="POMPO"
        width={132}
        height={98}
        priority
        className="h-8 w-auto"
      />
      <span className="font-display text-lg font-medium tracking-tight text-ink">POMPO</span>
    </Link>
  );
}
