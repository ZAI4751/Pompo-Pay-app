import Container from "@/components/ui/Container";
import Button from "@/components/ui/Button";
import Reveal from "@/components/ui/Reveal";

export default function ContactCTA() {
  return (
    <section className="border-t border-slate-line py-24 sm:py-32">
      <Container>
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="font-display text-3xl font-medium leading-tight text-ink sm:text-4xl">
            Let&apos;s talk about connecting your payments.
          </h2>
          <p className="mx-auto mt-4 max-w-md text-[17px] leading-relaxed text-slate-soft">
            Reach out and the POMPO team will get back to you.
          </p>
          <div className="mt-8 flex justify-center">
            <Button href="/contact" variant="primary">
              Get in Touch
            </Button>
          </div>
        </Reveal>
      </Container>
    </section>
  );
}
