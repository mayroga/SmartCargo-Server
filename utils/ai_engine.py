import os
import httpx

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

async def explicar_con_ia(error):

    prompt = f"""
Eres un agente profesional de counter de carga aérea.
Explica detalladamente este problema y cómo solucionarlo:

{error}

Incluye:
- Qué significa
- Riesgo operativo
- Riesgo legal
- Cómo corregirlo
- A dónde debe dirigirse el cliente
"""

    # Intento OpenAI
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=20
            )
            return r.json()["choices"][0]["message"]["content"]
    except:
        pass

    # Fallback Gemini
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}]
                },
                timeout=20
            )
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "No se pudo generar explicación IA."
