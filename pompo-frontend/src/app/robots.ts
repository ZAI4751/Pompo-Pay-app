import type { MetadataRoute } from "next";

/** Payment pages, Admin, and Account must not be indexed. App Links files must stay crawlable. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/.well-known/"],
      disallow: ["/"],
    },
  };
}
