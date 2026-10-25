import { defineCollection, z } from "astro:content";

const reviews = defineCollection({
  type: "content",
  schema: z.object({
    title: z.string(),
    director: z.string(),
    year: z.number(),
    rating: z.number().min(0).max(5),
    date: z.coerce.date(),
    summary: z.string().optional()
  })
});

const pages = defineCollection({
  type: "content",
  schema: z.object({
    slug: z.string(),
    title: z.string(),
    eyebrow: z.string().optional(),
    headline: z.string(),
    intro: z.string()
  })
});

export const collections = { reviews, pages };
