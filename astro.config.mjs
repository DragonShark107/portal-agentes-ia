// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://labagentes.com', // Cámbialo cuando compres tu dominio propio
  vite: {
    plugins: [tailwindcss()]
  },
  integrations: [sitemap()]
});