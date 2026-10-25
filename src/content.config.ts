import { defineCollection, z } from "astro:content";
import { glob } from 'astro/loaders';

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

const pagesCollection = defineCollection({
  loader: glob({ pattern: '**.md', base: './src/content/pages' }), // or type: 'content'
  schema: z.object({
    title: z.string(),
    slug: z.string().optional(), // <--- Change this to .optional()
    eyebrow: z.string().optional(),
    headline: z.string().optional(),
    intro: z.string().optional(),
  }),
});

export const collections = { reviews, pages };
