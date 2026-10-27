import type { APIRoute } from "astro";
import { getCollection } from "astro:content";

// Static allowlist updated whenever Pages builds from the latest CMS content.
// The Functions API checks this before accepting activity for an entry.
export const GET: APIRoute = async () => {
  const [reviews, projects] = await Promise.all([
    getCollection("reviews"),
    getCollection("projects"),
  ]);

  const manifest = {
    review: reviews.map((item) => item.data.slug || item.id),
    portfolio: projects.map((item) => item.data.slug || item.id),
  };
  return new Response(JSON.stringify(manifest), {
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=300" },
  });
};
