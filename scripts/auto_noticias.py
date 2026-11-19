import os
import re
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

FEEDS_RSS = [
    "https://huggingface.co/blog/feed.xml",
    "https://simonwillison.net/atom/everything/",
    "https://openai.com/news/rss.xml"
]

MODELOS_GEMINI = [
    "models/gemini-3.8-flash",
    "models/gemini-3.5-flash",
    "models/gemini-3.0-flash"
]

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[áàäâ]', 'a', text)
    text = re.sub(r'[éèëê]', 'e', text)
    text = re.sub(r'[íìïî]', 'i', text)
    text = re.sub(r'[óòöô]', 'o', text)
    text = re.sub(r'[úùüû]', 'u', text)
    text = re.sub(r'[ñ]', 'n', text)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    return re.sub(r'[\s-]+', '-', text)[:60].strip('-')

def obtener_candidatos_rss():
    candidatos = []
    for url in FEEDS_RSS:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as response:
                xml_data = response.read()
            root = ET.fromstring(xml_data)

            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for item in items[:5]:
                title_el = item.find("title") if item.find("title") is not None else item.find("{http://www.w3.org/2005/Atom}title")
                desc_el = item.find("description") if item.find("description") is not None else item.find("{http://www.w3.org/2005/Atom}summary")
                link_el = item.find("link") if item.find("link") is not None else item.find("{http://www.w3.org/2005/Atom}link")

                titulo = title_el.text.strip() if (title_el is not None and title_el.text) else ""
                resumen = desc_el.text.strip() if (desc_el is not None and desc_el.text) else titulo
                if link_el is not None:
                    link = link_el.text.strip() if link_el.text else link_el.attrib.get("href", "")
                else:
                    link = url

                if titulo:
                    candidatos.append((titulo, resumen[:1000], link))
        except Exception as e:
            print(f"Aviso leyendo {url}: {e}")
    return candidatos

def redactar_con_ia(titulo_orig, resumen_orig, link):
    prompt = f"""
    Actúa como redactor técnico experto en Agentes de IA Autónomos, Modelos Locales y Automatización.
    Basándote en esta novedad real del sector:
    Título original: {titulo_orig}
    Contexto: {resumen_orig}
    Enlace de referencia: {link}

    Redacta una noticia original, técnica, útil y bien estructurada en español (entre 350 y 500 palabras).
    Incluye al final un enlace de referencia a la fuente original usando Markdown: [Fuente oficial]({link}).
    Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta (sin bloques ```json):
    {{
      "title": "Titular atractivo y optimizado para SEO en español (sin comillas dobles)",
      "description": "Meta descripción SEO clara de 140 caracteres máximo",
      "category": "Una de estas exactas: Agentes Autónomos | Modelos Locales | Automatización | Herramientas",
      "content": "Cuerpo del artículo en Markdown usando ## para subtítulos y listas con *"
    }}
    """
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": 0}
        }
    }).encode("utf-8")

    for modelo in MODELOS_GEMINI:
        url = f"[https://generativelanguage.googleapis.com/v1beta/](https://generativelanguage.googleapis.com/v1beta/){modelo}:generateContent?key={GEMINI_API_KEY}"
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            print(f"Probando modelo: {modelo}")
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                texto = re.sub(r'^```json\s*|\s*```$', '', texto)
                return json.loads(texto)
        except urllib.error.HTTPError as e:
            print(f"Aviso HTTP con {modelo}: {e.read().decode('utf-8')}")
            continue
        except Exception as e:
            print(f"Aviso con {modelo}: {e}")
            continue

    raise RuntimeError("No se pudo generar la noticia con ninguno de los modelos configurados.")

def main():
    if not GEMINI_API_KEY:
        print("Error: Falta la variable de entorno GEMINI_API_KEY")
        return

    os.makedirs(os.path.join("src", "content", "noticias"), exist_ok=True)
    archivos_existentes = os.listdir(os.path.join("src", "content", "noticias"))

    candidatos = obtener_candidatos_rss()
    if not candidatos:
        print("No se pudieron obtener noticias de los feeds.")
        return

    for titulo_orig, resumen_orig, link in candidatos:
        slug_base = slugify(titulo_orig)[:30]
        if any(slug_base in archivo for archivo in archivos_existentes):
            continue

        print(f"Procesando novedad: {titulo_orig}")
        articulo = redactar_con_ia(titulo_orig, resumen_orig, link)
        slug_final = slugify(articulo["title"])
        ruta = os.path.join("src", "content", "noticias", f"{slug_final}.md")

        if os.path.exists(ruta):
            continue

        categoria_valida = articulo.get("category", "Agentes Autónomos")
        if categoria_valida not in ["Agentes Autónomos", "Modelos Locales", "Automatización", "Herramientas"]:
            categoria_valida = "Agentes Autónomos"

        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        md_final = f"""---
title: "{articulo['title'].replace('"', "'")}"
description: "{articulo['description'].replace('"', "'")}"
pubDate: {fecha_hoy}
category: "{categoria_valida}"
featured: false
affiliateTitle: "Despliega tus agentes de IA 24/7 en la nube"
affiliateDesc: "Ejecuta modelos open-source y flujos automatizados en servidores VPS de alto rendimiento."
affiliateUrl: "[https://tu-enlace-de-afiliado.com](https://tu-enlace-de-afiliado.com)"
affiliateCta: "Ver servidores recomendados"
---

{articulo['content']}
"""
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(md_final)
        print(f"✅ Publicada automáticamente: {ruta}")
        return

    print("Todas las novedades recientes ya estaban publicadas.")

if __name__ == "__main__":
    main()