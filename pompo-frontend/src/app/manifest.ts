import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "POMPO",
    short_name: "POMPO",
    description: "POMPO payments",
    start_url: "/",
    display: "standalone",
    background_color: "#f3f5fb",
    theme_color: "#0b468d",
    icons: [
      { src: "/favicon.png", sizes: "96x96", type: "image/png" },
      { src: "/pompo-icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/pompo-icon.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
