import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const reviews = defineCollection({
  loader: glob({ pattern: '**.md', base: './src/content/reviews' }),
  schema: z.object({
    title: z.string(),
    director: z.string().optional(),
    year: z.number().optional(),
    slug: z.string().optional(),
    date: z.coerce.date().optional(), // <--- z.coerce.date automatically parses "2026-10-24" strings into Date objects
    rating: z.number().optional(),
  }),
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

export const collections = { reviews, pages };
