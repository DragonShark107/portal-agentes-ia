import type { APIRoute } from 'astro';
import { ADSENSE_PUB_ID } from '../config/adsense';

// Genera /ads.txt a partir del ID de editor configurado en src/config/adsense.ts
export const GET: APIRoute = () => {
  const body = ADSENSE_PUB_ID
    ? `google.com, ${ADSENSE_PUB_ID}, DIRECT, f08c47fec0942fa0\n`
    : '# ads.txt pendiente de configurar\n';
  return new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
