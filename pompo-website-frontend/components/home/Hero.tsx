"use client";

import { motion } from "framer-motion";
import Container from "@/components/ui/Container";
import Button from "@/components/ui/Button";
import PaymentNetworkVisual from "@/components/home/PaymentNetworkVisual";

interface HeroProps {
  title: string;
  description: string;
}

export default function Hero({ title, description }: HeroProps) {
  const headlineWords = title.split(" ");

  return (
    <section className="relative overflow-hidden pb-20 pt-14 sm:pt-20 lg:pb-28 lg:pt-24">
      <Container>
        <div className="grid grid-cols-1 items-center gap-16 lg:grid-cols-[1.05fr_0.95fr] lg:gap-8">
          <div>
            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="text-sm font-medium text-indigo-500"
            >
              POMPO
            </motion.p>

            <h1 className="mt-4 max-w-lg font-display text-4xl font-medium leading-[1.1] text-ink sm:text-5xl lg:text-[3.4rem]">
              {headlineWords.map((word, i) => (
                <span key={`${word}-${i}`} className="inline-block overflow-hidden pb-1 align-bottom">
                  <motion.span
                    className="inline-block"
                    initial={{ y: "100%" }}
                    animate={{ y: 0 }}
                    transition={{ duration: 0.6, delay: 0.15 + i * 0.08, ease: [0.22, 1, 0.36, 1] }}
                  >
                    {word}&nbsp;
                  </motion.span>
                </span>
              ))}
            </h1>

            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.55 }}
              className="mt-6 max-w-md text-[17px] leading-relaxed text-slate-soft"
            >
              {description}
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.7 }}
              className="mt-9 flex flex-wrap items-center gap-4"
            >
              <Button href="/contact" variant="primary">
                Get in Touch
              </Button>
              <Button href="/how-it-works" variant="secondary">
                How POMPO Works
              </Button>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="relative mx-auto aspect-[13/10] w-full max-w-lg"
          >
            <PaymentNetworkVisual />
          </motion.div>
        </div>
      </Container>
    </section>
  );
}
