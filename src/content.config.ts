import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const noticias = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/noticias' }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    category: z.enum(['Agentes Autónomos', 'Modelos Locales', 'Automatización', 'Herramientas']),
    featured: z.boolean().default(false),
    affiliateTitle: z.string().optional(),
    affiliateDesc: z.string().optional(),
    affiliateUrl: z.string().optional(),
    affiliateCta: z.string().optional(),
  }),
});

export const collections = { noticias };