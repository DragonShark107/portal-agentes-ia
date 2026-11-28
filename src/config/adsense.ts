// Configuración central de Google AdSense.
//
// 1) Al darte de alta en AdSense, pega aquí tu ID de editor (formato "pub-1234567890123456").
//    Con solo esto se añade el script de verificación al <head> y se genera /ads.txt.
// 2) Cuando Google apruebe la web, cambia ADSENSE_ACTIVO a true para mostrar los bloques <AdSlot>.
export const ADSENSE_PUB_ID = '';

export const ADSENSE_ACTIVO = false;

export const ADSENSE_CLIENT = ADSENSE_PUB_ID ? `ca-${ADSENSE_PUB_ID}` : '';

// Google Search Console (método "Etiqueta HTML"): pega solo el valor de content="..."
export const GOOGLE_SITE_VERIFICATION = '';

// Bing Webmaster Tools (método "Meta etiqueta"): pega solo el valor de content="..."
export const BING_SITE_VERIFICATION = '';
