import os
import re
import json
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NOTICIAS_POR_EJECUCION = 3  # Número de noticias a generar por cada carga en Netlify

FEEDS_RSS = [
    "https://huggingface.co/blog/feed.xml",
    "https://simonwillison.net/atom/everything/",
    "https://openai.com/news/rss.xml",
    "https://blog.langchain.dev/rss/",
    "https://ollama.com/blog/rss.xml"
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

def obtener_urls_publicadas(carpeta):
    contenido_total = ""
    for archivo in os.listdir(carpeta):
        if archivo.endswith(".md"):
            with open(os.path.join(carpeta, archivo), "r", encoding="utf-8") as f:
                contenido_total += f.read() + "\n"
    return contenido_total

def obtener_candidatos_rss():
    candidatos = []
    for url in FEEDS_RSS:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as response:
                xml_data = response.read()
            root = ET.fromstring(xml_data)

            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            for item in items[:8]:
                title_el = item.find("title") if item.find("title") is not None else item.find("{http://www.w3.org/2005/Atom}title")
                desc_el = item.find("description") if item.find("description") is not None else item.find("{http://www.w3.org/2005/Atom}summary")
                link_el = item.find("link") if item.find("link") is not None else item.find("{http://www.w3.org/2005/Atom}link")

                titulo = title_el.text.strip() if (title_el is not None and title_el.text) else ""
                resumen = desc_el.text.strip() if (desc_el is not None and desc_el.text) else titulo
                if link_el is not None:
                    link = link_el.text.strip() if link_el.text else link_el.attrib.get("href", "")
                else:
                    link = url

                if titulo and link:
                    candidatos.append((titulo, resumen[:800], link))
        except Exception as e:
            print(f"Aviso leyendo {url}: {e}")
    return candidatos

def obtener_modelos_activos():
    base = "https://generativelanguage.googleapis.com/v1beta/models"
    url_models = f"{base}?key={GEMINI_API_KEY}"
    modelos_validos = []
    try:
        req = urllib.request.Request(url_models)
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for m in data.get("models", []):
                nombre = m.get("name", "")
                metodos = m.get("supportedGenerationMethods", [])
                if "generateContent" in metodos and ("flash" in nombre or "lite" in nombre):
                    if not any(v in nombre for v in ["1.5", "2.0", "2.5"]):
                        modelos_validos.append(nombre)
    except Exception as e:
        print(f"Aviso listando modelos: {e}")

    modelos_validos.sort(key=lambda x: (0 if "lite" in x else 1, x), reverse=False)
    if not modelos_validos:
        modelos_validos = ["models/gemini-3.8-flash-lite", "models/gemini-3.8-flash", "models/gemini-3.5-flash"]
    return modelos_validos

def redactar_con_ia(titulo_orig, resumen_orig, link):
    prompt = f"""
    Actúa como redactor técnico experto en Agentes de IA Autónomos, Modelos Locales y Automatización.
    Basándote en esta novedad real:
    Título: {titulo_orig}
    Contexto: {resumen_orig}
    Fuente: {link}

    Redacta una noticia clara, original y directa en español (entre 350 y 450 palabras) para posicionar bien en Google.
    Incluye al final: [Fuente oficial]({link}).
    Devuelve ÚNICAMENTE un JSON válido con esta estructura:
    {{
      "title": "Titular SEO en español sin comillas dobles",
      "description": "Meta descripción SEO de 140 caracteres máximo",
      "category": "Una de estas exactas: Agentes Autónomos | Modelos Locales | Automatización | Herramientas",
      "content": "Cuerpo en Markdown usando ## para subtítulos y listas con *"
    }}
    """
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "maxOutputTokens": 1500
        }
    }).encode("utf-8")

    modelos = obtener_modelos_activos()
    base = "https://generativelanguage.googleapis.com/v1beta/"
    for modelo in modelos:
        url = f"{base}{modelo}:generateContent?key={GEMINI_API_KEY}"
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                texto = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                texto = re.sub(r'^```json\s*|\s*```$', '', texto)
                return json.loads(texto)
        except Exception:
            time.sleep(2)
            continue

    raise RuntimeError("No se pudo generar la noticia con ninguno de los modelos disponibles.")

def main():
    if not GEMINI_API_KEY:
        print("Error: Falta la variable de entorno GEMINI_API_KEY")
        return

    carpeta = os.path.join("src", "content", "noticias")
    os.makedirs(carpeta, exist_ok=True)
    historial_publicado = obtener_urls_publicadas(carpeta)

    candidatos = obtener_candidatos_rss()
    if not candidatos:
        print("No se pudieron obtener noticias de los feeds.")
        return

    publicadas_hoy = 0

    for titulo_orig, resumen_orig, link in candidatos:
        if publicadas_hoy >= NOTICIAS_POR_EJECUCION:
            break

        palabra_clave = slugify(titulo_orig).split("-")[0]
        if link in historial_publicado or (len(palabra_clave) > 4 and palabra_clave in historial_publicado.lower()):
            continue

        print(f"[{publicadas_hoy + 1}/{NOTICIAS_POR_EJECUCION}] Procesando novedad: {titulo_orig}")
        try:
            articulo = redactar_con_ia(titulo_orig, resumen_orig, link)
        except Exception as e:
            print(f"Error generando artículo: {e}")
            continue

        slug_final = slugify(articulo["title"])
        ruta = os.path.join(carpeta, f"{slug_final}.md")

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
sourceUrl: "{link}"
affiliateTitle: "Despliega tus agentes de IA 24/7 en la nube"
affiliateDesc: "Ejecuta modelos open-source y flujos automatizados en servidores VPS de alto rendimiento."
affiliateUrl: "https://www.hostinger.es/vps-hosting"
affiliateCta: "Ver servidores recomendados"
---

{articulo['content']}
"""
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(md_final)

        # Actualizamos el historial en memoria para no repetir tema en la misma tanda
        historial_publicado += f"\n{link}\n{titulo_orig}\n{md_final}"
        publicadas_hoy += 1
        print(f"✅ Publicada ({publicadas_hoy}/{NOTICIAS_POR_EJECUCION}): {ruta}")
        time.sleep(3)

    if publicadas_hoy == 0:
        print("Todas las novedades recientes ya estaban publicadas.")
    else:
        print(f"🎉 Tanda completada: {publicadas_hoy} noticias nuevas generadas en una sola carga.")

if __name__ == "__main__":
    main()