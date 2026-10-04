import Container from "@/components/ui/Container";
import Button from "@/components/ui/Button";

export default function NotFound() {
  return (
    <section className="flex min-h-[60vh] items-center py-24">
      <Container className="text-center">
        <p className="text-sm font-medium text-indigo-500">404</p>
        <h1 className="mt-4 font-display text-3xl font-medium text-ink sm:text-4xl">
          This page doesn&apos;t exist.
        </h1>
        <p className="mx-auto mt-3 max-w-sm text-[15px] leading-relaxed text-slate-soft">
          The page you&apos;re looking for may have moved or never existed.
        </p>
        <div className="mt-8 flex justify-center">
          <Button href="/" variant="primary">
            Back to home
          </Button>
        </div>
      </Container>
    </section>
  );
}
