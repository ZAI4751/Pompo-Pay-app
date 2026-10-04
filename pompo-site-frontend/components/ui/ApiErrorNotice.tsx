import Button from "@/components/ui/Button";
import Container from "@/components/ui/Container";

interface ApiErrorNoticeProps {
  title?: string;
  message?: string;
  status?: number;
  retryHref?: string;
}

export default function ApiErrorNotice({
  title = "Unable to load content",
  message = "We could not retrieve this content from the POMPO API. Please verify that the backend server is running and accessible.",
  status,
  retryHref,
}: ApiErrorNoticeProps) {
  return (
    <section className="py-20 sm:py-28">
      <Container className="max-w-2xl text-center">
        <div className="rounded-3xl border border-red-200 bg-red-50/50 p-8 sm:p-12 text-center">
          <div
            aria-hidden
            className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-600"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 18.75h.007v.008H12v-.008z"
              />
            </svg>
          </div>
          <p className="text-xs font-semibold uppercase tracking-wider text-red-600">
            {status ? `API Error ${status}` : "API Unavailable"}
          </p>
          <h2 className="mt-2 font-display text-2xl font-medium text-ink sm:text-3xl">
            {title}
          </h2>
          <p className="mx-auto mt-4 max-w-md text-[15px] leading-relaxed text-slate-soft">
            {message}
          </p>
          {retryHref && (
            <div className="mt-8 flex justify-center gap-4">
              <Button href={retryHref} variant="secondary">
                Retry
              </Button>
            </div>
          )}
        </div>
      </Container>
    </section>
  );
}
