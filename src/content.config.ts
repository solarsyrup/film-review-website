import { defineCollection, z } from 'astro:content';
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

const pages = defineCollection({
  loader: glob({ pattern: '**.md', base: './src/content/pages' }),
  schema: z.object({
    title: z.string().optional(),
    slug: z.string().optional(),
    eyebrow: z.string().optional(),
    headline: z.string().optional(),
    intro: z.string().optional(),
  }),
});

export const collections = { 
  pages: pages // or simply { pages }
};
