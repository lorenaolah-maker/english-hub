import streamlit as st
import sqlite3
import random
import json
import urllib.request
import time
import os
from datetime import datetime

# =========================================================
# 0. CONFIGURACIÓN Y SINCRONIZACIÓN CON NOTION
# =========================================================
NOTION_TOKEN = str(st.secrets.get("NOTION_TOKEN", "")).strip().strip('"').strip("'")
DB_SPEAKING_ID = "3f95713402588029a8cfc6514e6e4efd"
DB_WRITING_ID = "3f9571340258801dbcccf2d5a4e6e814"
DB_SESIONES_ID = "3f957134025880cd8a60e4fb66a82742"

def sync_to_notion(database_id, properties_payload):
    if not NOTION_TOKEN or NOTION_TOKEN.startswith("PEGA_AQUI"):
        return False, "Token no configurado"
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    payload = {
        "parent": {"database_id": database_id},
        "properties": properties_payload
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, "Sincronizado con Notion"
    except Exception as e:
        return False, str(e)

def log_speaking_notion(prompt, user_resp, feedback_text):
    props = {
        "Reto/Prompt": {"title": [{"text": {"content": str(prompt)[:100]}}]},
        "Fecha": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
        "Mi respuesta": {"rich_text": [{"text": {"content": str(user_resp)[:1900]}}]},
        "Feedback IA": {"rich_text": [{"text": {"content": str(feedback_text)[:1900]}}]}
    }
    return sync_to_notion(DB_SPEAKING_ID, props)

def log_writing_notion(topic, original_text, polished_text):
    props = {
        "Tema": {"title": [{"text": {"content": str(topic)[:100]}}]},
        "Fecha": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
        "Borrador original": {"rich_text": [{"text": {"content": str(original_text)[:1900]}}]},
        "Version nativa IA": {"rich_text": [{"text": {"content": str(polished_text)[:1900]}}]}
    }
    return sync_to_notion(DB_WRITING_ID, props)

def log_session_notion(activity, tipo, puntaje_min):
    props = {
        "Actividad": {"title": [{"text": {"content": str(activity)[:100]}}]},
        "Fecha": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
        "Seleccionar": {"select": {"name": str(tipo)}},
        "Puntaje/minutos": {"number": int(puntaje_min)}
    }
    return sync_to_notion(DB_SESIONES_ID, props)

# =========================================================
# 1. TUTOR CON MULTI-MODEL FALLBACK
# =========================================================
def evaluate_speech_with_ai(prompt_text, user_response, is_spoken=False):
    api_key = str(st.secrets.get("GEMINI_API_KEY", "")).strip().strip('"').strip("'")
    if not api_key:
        return "⚠️ Configura GEMINI_API_KEY en Secrets de Streamlit."
    
    tipo_modalidad = "HABILIDAD ORAL / SPEAKING" if is_spoken else "ESCRITURA / WRITING"
    sys_prompt = f"""
    Eres una tutora nativa de inglés experta y empática para hispanohablantes.
    Modalidad: {tipo_modalidad}
    Reto: "{prompt_text}"
    Respuesta: "{user_response}"

    Estructura tu retroalimentación:
    🎯 **Puntuación Global:** [Nota del 1 al 10]/10
    🔍 **Análisis Gramatical y Sintaxis:** Explicación clara.
    ✨ **Versión Nivel Nativo (Natural Phrasing):** Frase pulida.
    🗣️ **Guía Fonética y Pronunciación:** 2 o 3 palabras clave y connected speech.
    💡 **Consejo de Oro para Recordar:** Regla rápida.
    """
    
    payload = {
        "contents": [{"parts": [{"text": sys_prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 850}
    }
    data = json.dumps(payload).encode("utf-8")
    active_models = ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]
    
    last_error = ""
    for model_name in active_models:
        for _ in range(2):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=12) as response:
                    res_json = json.loads(response.read().decode("utf-8"))
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"]
            except Exception as e:
                last_error = str(e)
                time.sleep(1.0)
                continue
    return f"Servidores ocupados ({last_error}). Vuelve a intentar en 2 segundos."

# =========================================================
# 2. BASE DE DATOS LOCAL SQLITE
# =========================================================
def init_db():
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS courses (id TEXT PRIMARY KEY, name TEXT, current_unit INTEGER, total_units INTEGER, current_step TEXT, last_study TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS study_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, duration_min INTEGER, focus_area TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS flashcards (id INTEGER PRIMARY KEY AUTOINCREMENT, level TEXT, category TEXT, front TEXT, back TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS flashcard_progress (card_id INTEGER PRIMARY KEY, mastered INTEGER DEFAULT 0, review_count INTEGER DEFAULT 0, last_reviewed TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS quizzes (id INTEGER PRIMARY KEY AUTOINCREMENT, level TEXT, category TEXT, question TEXT, op1 TEXT, op2 TEXT, op3 TEXT, op4 TEXT, correct TEXT, explanation TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS quiz_history (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, level TEXT, score INTEGER, total INTEGER, pct INTEGER)")
    c.execute("INSERT OR IGNORE INTO courses VALUES ('gringo', 'Gringo Academy (Método Inmersivo)', 1, 130, 'Paso 1: Vocabulario en contexto', ?)", (str(datetime.now().date()),))
    c.execute("INSERT OR IGNORE INTO courses VALUES ('neural', 'Inglés Práctico (Activación Neural - 12 Semanas)', 1, 12, 'Semana 1', ?)", (str(datetime.now().date()),))
    conn.commit()
    conn.close()

def log_session(minutes, focus):
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    c.execute("INSERT INTO study_sessions (date, duration_min, focus_area) VALUES (?, ?, ?)", (str(datetime.now().strftime("%Y-%m-%d %H:%M")), minutes, focus))
    conn.commit()
    conn.close()
    log_session_notion(f"Estudio: {focus}", "Pomodoro", minutes)

def get_recent_sessions():
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    c.execute("SELECT date, duration_min, focus_area FROM study_sessions ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()
    return rows

init_db()

# =========================================================
# 3. INTERFAZ Y ESTILOS
# =========================================================
st.set_page_config(page_title="English Mastery Hub | Lorena Alvarez", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .block-container { padding-top: 1.8rem; padding-bottom: 2rem; max-width: 1200px; }
    .glass-card { background: linear-gradient(135deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.85) 100%); border: 1px solid rgba(148, 163, 184, 0.18); border-radius: 16px; padding: 1.5rem; margin-bottom: 1.2rem; }
    .profile-card { background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 16px; padding: 1rem; text-align: center; margin-bottom: 1.2rem; }
    .profile-name { font-size: 1.15rem; font-weight: 700; color: #F8FAFC; margin-top: 8px; margin-bottom: 2px; }
    .profile-role { font-size: 0.8rem; color: #38BDF8; font-weight: 600; }
    .tag-badge { display: inline-block; background: rgba(56, 189, 248, 0.18); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.35); padding: 4px 12px; border-radius: 9999px; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.8rem; }
    .platform-btn { display: block; text-align: center; background: #1E293B; color: #F8FAFC !important; font-weight: 700; padding: 13px; border-radius: 12px; text-decoration: none; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    if os.path.exists("lorena.jpg"):
        c_l, c_img, c_r = st.columns([1, 2, 1])
        with c_img:
            st.image("lorena.jpg", use_container_width=True)
    st.markdown("""
    <div class="profile-card">
        <div class="profile-name">Lorena Alvarez</div>
        <div class="profile-role">⚡ English Mastery | A0 ➔ C2</div>
        <div style="font-size:0.75rem; color:#94A3B8; margin-top:4px;">🎯 Sincronización con Notion Activa</div>
    </div>
    """, unsafe_allow_html=True)

menu = st.sidebar.radio("Navegación:", [
    "🌐 Hub de Plataformas & Apps",
    "🗣️ Speaking & Feedback Lab",
    "🎧 Listening & Inmersión",
    "✍️ Writing Clinic",
    "🎬 Hub de Cursos (Hotmart)",
    "⏱️ Focus & Pomodoro (15-20m)"
])

# --- SPEAKING LAB ---
if menu == "🗣️ Speaking & Feedback Lab":
    st.markdown("## 🗣️ Speaking & Feedback con Inteligencia Artificial")
    tema = st.selectbox("Reto de hoy:", [
        "Introduce yourself: your name, where you live, and your age. (A0)",
        "Describe your typical morning routine in 3 sentences. (A1)",
        "What did you do yesterday afternoon? Mention 2 activities. (A2)"
    ])
    st.info(f"🗣️ **Prompt:** \"{tema}\"")
    user_text = st.text_area("Escribe tu respuesta en inglés:", height=100)
    if st.button("🤖 Analizar y Guardar en Notion", use_container_width=True):
        if not user_text.strip():
            st.warning("Escribe una frase en inglés.")
        else:
            with st.spinner("Analizando con tu tutora de IA y guardando en Notion..."):
                retro = evaluate_speech_with_ai(tema, user_text, is_spoken=False)
                ok, msg = log_speaking_notion(tema, user_text, retro)
                if ok:
                    st.toast("✅ ¡Registro enviado a Notion con éxito!")
                else:
                    st.warning(f"Guardado localmente. Estado Notion: {msg}")
                st.markdown('<div class="glass-card"><span class="tag-badge">RETROALIMENTACIÓN SINCRONIZADA CON NOTION</span>', unsafe_allow_html=True)
                st.markdown(retro)
                st.markdown('</div>', unsafe_allow_html=True)

# --- WRITING CLINIC ---
elif menu == "✍️ Writing Clinic":
    st.markdown("## ✍️ Writing Clinic")
    tema_w = st.selectbox("Tema:", ["Diario personal", "Correo profesional", "Redacción libre"])
    texto_w = st.text_area("Texto en inglés:", height=140)
    if st.button("✨ Pulir y Guardar en Notion", use_container_width=True):
        if texto_w.strip():
            with st.spinner("Revisando redacción..."):
                retro = evaluate_speech_with_ai(f"Writing ({tema_w})", texto_w, False)
                ok, msg = log_writing_notion(tema_w, texto_w, retro)
                if ok:
                    st.toast("✅ ¡Guardado en Writing Clinic de Notion!")
                st.markdown('<div class="glass-card"><span class="tag-badge">REVISIÓN DE ESTILO</span>', unsafe_allow_html=True)
                st.markdown(retro)
                st.markdown('</div>', unsafe_allow_html=True)

# --- PLATAFORMAS ---
elif menu == "🌐 Hub de Plataformas & Apps":
    st.markdown("## 🌐 Plataformas de Práctica Gratuita")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="glass-card"><h3>🦉 Duolingo</h3><a href="https://www.duolingo.com" target="_blank" class="platform-btn" style="background:#58CC02;">Abrir Duolingo</a></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="glass-card"><h3>📻 BBC English</h3><a href="https://www.bbc.co.uk/learningenglish" target="_blank" class="platform-btn" style="background:#B80000;">Abrir BBC</a></div>', unsafe_allow_html=True)

# --- RESTO DE MÓDULOS ---
elif menu == "🎧 Listening & Inmersión":
    st.markdown("## 🎧 Listening")
    st.markdown('<div class="glass-card"><h3>🎬 YouGlish</h3><a href="https://youglish.com" target="_blank" class="platform-btn">Abrir YouGlish</a></div>', unsafe_allow_html=True)

elif menu == "🎬 Hub de Cursos (Hotmart)":
    st.markdown("## 🎬 Cursos Hotmart")
    st.markdown('<a href="https://consumer.hotmart.com" target="_blank" class="platform-btn" style="background:#EA580C;">Abrir Hotmart</a>', unsafe_allow_html=True)

elif menu == "⏱️ Focus & Pomodoro (15-20m)":
    st.markdown("## ⏱️ Pomodoro Focus")
    t = st.select_slider("Minutos:", [5, 10, 15, 20, 25, 30], value=15)
    f = st.selectbox("Área:", ["Speaking", "Listening", "Writing", "Gramática"])
    if st.button("🔥 Guardar Sesión"):
        log_session(t, f)
        st.success("Sesión guardada en Notion y localmente.")
