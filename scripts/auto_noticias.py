import os
import re
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

# Clave API gratuita de Google Gemini (la guardarás en GitHub Secrets)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Fuente RSS real de noticias de IA / Tecnología
RSS_URL = "https://huggingface.co/blog/feed.xml"

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[áàäâ]', 'a', text)
    text = re.sub(r'[éèëê]', 'e', text)
    text = re.sub(r'[íìïî]', 'i', text)
    text = re.sub(r'[óòöô]', 'o', text)
    text = re.sub(r'[úùüû]', 'u', text)
    text = re.sub(r'[ñ]', 'n', text)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    return re.sub(r'[\s-]+', '-', text)[:60]

def obtener_ultima_noticia_rss():
    req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as response:
        xml_data = response.read()
    root = ET.fromstring(xml_data)
    item = root.find(".//item")
    titulo = item.find("title").text
    descripcion = item.find("description").text or ""
    link = item.find("link").text
    return titulo, descripcion[:1000], link

def redactar_con_ia(titulo_orig, resumen_orig, link):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""
    Actúa como redactor técnico experto en Agentes de IA Autónomos y Modelos Locales.
    Basándote en esta novedad real:
    Título: {titulo_orig}
    Resumen: {resumen_orig}
    Fuente: {link}

    Redacta una noticia original, clara y bien estructurada en español (unos 400 palabras).
    Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta (sin bloques markdown ```json):
    {{
      "title": "Titular atractivo y SEO en español (sin comillas dobles internas)",
      "description": "Meta descripción SEO de 140 caracteres máximo",
      "category": "Una de estas: Agentes Autónomos | Modelos Locales | Automatización | Herramientas",
      "content": "Cuerpo del artículo en Markdown usando ## para subtítulos y listas con *"
    }}
    """
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        texto = re.sub(r'^```json\s*|\s*```$', '', texto)
        return json.loads(texto)

def main():
    if not GEMINI_API_KEY:
        print("Falta GEMINI_API_KEY")
        return

    titulo_orig, resumen_orig, link = obtener_ultima_noticia_rss()
    articulo = redactar_con_ia(titulo_orig, resumen_orig, link)

    slug = slugify(articulo["title"])
    ruta = os.path.join("src", "content", "noticias", f"{slug}.md")

    if os.path.exists(ruta):
        print("La noticia ya existe, no se duplica.")
        return

    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    md_final = f"""---
title: "{articulo['title'].replace('"', "'")}"
description: "{articulo['description'].replace('"', "'")}"
pubDate: {fecha_hoy}
category: "{articulo['category']}"
featured: false
affiliateTitle: "Despliega tus agentes de IA 24/7 en la nube"
affiliateDesc: "Ejecuta modelos open-source y flujos automatizados en servidores VPS de alto rendimiento."
affiliateUrl: "[https://tu-enlace-de-afiliado.com](https://tu-enlace-de-afiliado.com)"
affiliateCta: "Ver servidores recomendados"
---

{articulo['content']}
"""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(md_final)
    print(f"✅ Publicada automáticamente: {ruta}")

if __name__ == "__main__":
    main()