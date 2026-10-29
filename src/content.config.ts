import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const reviews = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/reviews" }),
  schema: z.object({
    title: z.string(),
    director: z.string().optional(),
    year: z.number().optional(),
    slug: z.string().optional(),
    date: z.coerce.date().optional(),
    rating: z.number().min(0).max(5).optional(),
    summary: z.string().optional(),
    medium: z.enum(["Film", "TV", "Music", "Game", "Book", "Other"]).optional(),
    cover: z.string().optional(),
    tmdbId: z.number().optional(),
    autoPoster: z.boolean().optional(),
    spoilerHeading: z.string().optional(),
    spoilerText: z.string().optional(),
  }),
});

const pages = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/pages" }),
  schema: z.object({
    title: z.string().optional(),
    slug: z.string().optional(),
    eyebrow: z.string().optional(),
    headline: z.string().optional(),
    intro: z.string().optional(),
    sectionHeading: z.string().optional(),
    closingNote: z.string().optional(),
    currentlyWatching: z.string().optional(),
    currentlyReading: z.string().optional(),
    currentlyListening: z.string().optional(),
    currentlyPlaying: z.string().optional(),
    currentlyWatchingCover: z.string().optional(),
    currentlyReadingCover: z.string().optional(),
    currentlyListeningCover: z.string().optional(),
    currentlyPlayingCover: z.string().optional(),
  }),
});


const projects = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/projects" }),
  schema: z.object({
    title: z.string(),
    slug: z.string().nullish(),
    category: z.enum(["Film", "Writing", "Photography", "Music", "Other"]).nullish(),
    year: z.preprocess((value) => value === "" ? undefined : value, z.number().nullish()),
    date: z.preprocess((value) => value === "" ? undefined : value, z.coerce.date().nullish()),
    role: z.string().nullish(),
    description: z.string().nullish(),
    cover: z.string().nullish(),
    coverAlt: z.string().nullish(),
    gallery: z.array(z.string()).nullish(),
    mediaFile: z.string().nullish(),
    link: z.string().nullish(),
    embedLink: z.string().nullish(),
  }),
});

const diary = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/diary" }),
  schema: z.object({
    title: z.string(),
    slug: z.string().optional(),
    medium: z.enum(["Film", "TV", "Music", "Game", "Book", "Other"]),
    date: z.coerce.date(),
    year: z.number().optional(),
    rating: z.number().min(0).max(5).optional(),
    creator: z.string().optional(),
    cover: z.string().optional(),
    tmdbId: z.number().optional(),
    autoPoster: z.boolean().optional(),
    note: z.string().optional(),
    reviewUrl: z.string().optional(),
  }),
});

export const collections = { reviews, pages, projects, diary };
