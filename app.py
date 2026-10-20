import streamlit as st
import sqlite3
import random
import json
import urllib.request
import re
import time
import os
from datetime import datetime, timedelta

# =========================================================
# 0. CONEXIÓN Y NOTION API
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
            return True, "Sincronizado"
    except Exception as e:
        return False, str(e)

def extract_score(text):
    match = re.search(r'(\d{1,2})\s*/\s*10', text)
    if match:
        try:
            return int(match.group(1))
        except Exception:
            return 8
    return 8

def log_speaking_notion(prompt, user_resp, feedback_text):
    score = extract_score(feedback_text)
    props = {
        "Reto/Prompt": {"title": [{"text": {"content": str(prompt)[:100]}}]},
        "Fecha": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
        "Mi respuesta": {"rich_text": [{"text": {"content": str(user_resp)[:1900]}}]},
        "Puntuacion": {"number": score},
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
# 1. TUTORA INTELIGENTE
# =========================================================
def evaluate_speech_with_ai(prompt_text, user_response):
    api_key = str(st.secrets.get("GEMINI_API_KEY", "")).strip().strip('"').strip("'")
    if not api_key:
        return "⚠️ Configura GEMINI_API_KEY en Secrets de Streamlit."
    
    sys_prompt = f"""
    Eres una tutora nativa de inglés experta y empática para estudiantes hispanohablantes.
    Reto asignado: "{prompt_text}"
    Respuesta escrita por la alumna: "{user_response}"

    Estructura tu retroalimentación:
    🎯 **Puntuación Global:** [Nota del 1 al 10]/10
    🔍 **Análisis Gramatical y Sintaxis:** Explicación clara de errores y aciertos.
    ✨ **Versión Nivel Nativo (Natural Phrasing):** Frase pulida en lenguaje contemporáneo.
    🗣️ **Guía Fonética y Pronunciación:** 2 o 3 palabras clave con transcripción fonética fácil en español y connected speech.
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
    return f"Servidores ocupados ({last_error}). Intenta nuevamente."

# =========================================================
# 2. BASE DE DATOS LOCAL
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
    
    c.execute("DELETE FROM courses WHERE id = 'neural'")
    c.execute("INSERT OR IGNORE INTO courses VALUES ('ingles_practico', 'Inglés Práctico (App & Biblioteca)', 1, 12, 'Semana 1', ?)", (str(datetime.now().date()),))
    c.execute("INSERT OR IGNORE INTO courses VALUES ('gringo', 'Gringo Academy (Método Inmersivo)', 1, 130, 'Paso 1: Vocabulario en contexto', ?)", (str(datetime.now().date()),))
    
    cards_seed = [
        ("A0", "Saludos", "I am 38 years old", "Tengo 38 años (En inglés la edad se ES, no se 'tiene')"),
        ("A0", "Básicos", "Where are you from?", "¿De dónde eres?"),
        ("A1", "Rutina", "I wake up at 7:00 AM every morning", "Me despierto a las 7:00 AM todas las mañanas"),
        ("A1", "Verbos", "She doesn't like spicy food", "A ella no le gusta la comida picante (Uso de doesn't)"),
        ("A2", "Pasado", "I went to the salon yesterday afternoon", "Fui al salón ayer por la tarde (went = pasado de go)"),
        ("A2", "Planes", "We are going to travel next month", "Vamos a viajar el próximo mes"),
        ("B1", "Condicionales", "If I have time, I will finish the report", "Si tengo tiempo, terminaré el reporte (Primer condicional)"),
        ("B1", "Experiencias", "I have lived here for five years", "He vivido aquí durante cinco años (Present Perfect)"),
        ("B2", "Fluidez Profesional", "Despite the tight deadline, we managed to deliver", "A pesar de la fecha límite ajustada, logramos entregar"),
        ("B2", "Collocations", "To reach a compromise", "Llegar a un acuerdo mutuo"),
        ("C1", "Estructuras Avanzadas", "Seldom have I seen such dedication to mastery", "Rara vez he visto tal dedicación a la maestría (Inversión gramatical)"),
        ("C1", "Vocabulario Preciso", "The plan was thoroughly scrutinized", "El plan fue examinado minuciosamente"),
        ("C2", "Expresiones Idiomáticas", "To cut corners without compromising integrity", "Tomar atajos sin comprometer la integridad"),
        ("C2", "Maestría Nativa", "An unassuming yet quintessential approach", "Un enfoque sin pretensiones pero representativo")
    ]
    for lvl, cat, fr, bk in cards_seed:
        c.execute("INSERT OR IGNORE INTO flashcards (level, category, front, back) SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM flashcards WHERE front = ?)", (lvl, cat, fr, bk, fr))

    quiz_seed = [
        ("A0", "Edad", "Choose the correct sentence for age:", "I have 30 years", "I am 30 years old", "I am having 30 years", "I got 30 years", "I am 30 years old", "En inglés se utiliza el verbo To Be para la edad."),
        ("A0", "Origen", "How do you say 'Soy de México'?", "I am from Mexico", "I am of Mexico", "I have Mexico", "I live Mexico", "I am from Mexico", "Se usa 'from' para indicar procedencia."),
        ("A0", "Saludos", "Which greeting is used at night when arriving?", "Good night", "Good evening", "Goodbye", "See you", "Good evening", "'Good evening' se usa al llegar de noche; 'Good night' es despedida."),
        ("A0", "Pronombres", "What is the pronoun for 'ella'?", "He", "She", "It", "They", "She", "'She' corresponde a ella."),
        ("A0", "Posesivos", "This is _____ book (mi libro).", "my", "mine", "me", "I", "my", "El adjetivo posesivo es 'my'."),
        ("A0", "To Be", "They _____ students.", "is", "am", "are", "be", "are", "Con They se usa 'are'."),
        ("A0", "Números", "How do you write 15?", "Fifty", "Fifteen", "Fiveteen", "Fiftin", "Fifteen", "15 se escribe 'fifteen'."),
        ("A0", "Días", "What day comes after Monday?", "Sunday", "Wednesday", "Tuesday", "Thursday", "Tuesday", "El martes es 'Tuesday'."),
        ("A1", "Presente Simple", "He _____ coffee every morning.", "drink", "drinks", "drinking", "is drink", "drinks", "Con he/she/it en presente afirmativo se añade -s."),
        ("A1", "Negación", "I _____ like cold weather.", "doesn't", "don't", "not", "am not", "don't", "Con I se niega en presente con 'don't'."),
        ("A1", "Preposiciones", "The meeting is _____ 3:00 PM.", "in", "on", "at", "for", "at", "Para horas exactas se usa 'at'."),
        ("A1", "Días", "I play tennis _____ Saturdays.", "in", "on", "at", "by", "on", "Para días de la semana se usa 'on'."),
        ("A1", "Preguntas", "_____ do you live?", "When", "Where", "Who", "Why", "Where", "'Where' significa 'dónde'."),
        ("A1", "Plurales", "What is the plural of 'child'?", "Childs", "Children", "Childrens", "Childes", "Children", "Es un plural irregular."),
        ("A2", "Pasado Simple", "Yesterday, we _____ to a new restaurant.", "go", "gone", "went", "going", "went", "El pasado de 'go' es 'went'."),
        ("A2", "Negación Pasado", "She _____ come to the party last night.", "didn't", "doesn't", "wasn't", "not", "didn't", "El auxiliar de pasado negativo es 'didn't'."),
        ("A2", "Futuro", "Look at those dark clouds! It _____ rain.", "will", "is going to", "goes to", "shall", "is going to", "Para evidencia visual inmediata se prefiere 'going to'."),
        ("A2", "Comparativos", "My car is _____ than yours.", "fast", "faster", "more fast", "fastest", "faster", "Para adjetivos cortos se agrega -er."),
        ("A2", "Pasado Continuo", "I _____ when the phone rang.", "was cooking", "cooked", "am cooking", "were cooking", "was cooking", "Acción continua interrumpida en el pasado."),
        ("B1", "Present Perfect", "She has _____ in London since 2021.", "live", "lives", "lived", "living", "lived", "Present Perfect: has + participio."),
        ("B1", "For vs Since", "I haven't seen him _____ two years.", "since", "for", "during", "from", "for", "Se usa 'for' para duraciones de tiempo."),
        ("B1", "Condicional 1", "If it rains, we _____ stay at home.", "will", "would", "had", "did", "will", "Primer condicional: If + Present, Will + base."),
        ("B1", "Condicional 2", "If I won the lottery, I _____ travel the world.", "will", "would", "can", "am going to", "would", "Segundo condicional hipotético: If + Past, Would + base."),
        ("B1", "Modales", "You _____ wear a seatbelt mientras conduces.", "must", "might", "can", "may", "must", "Indica obligación legal estricta."),
        ("B2", "Voz Pasiva", "The new project _____ by the committee next week.", "will approve", "will be approved", "is approving", "approves", "will be approved", "Voz pasiva en futuro: will be + participio."),
        ("B2", "Condicional 3", "If I had known, I _____ you.", "would help", "would have helped", "will help", "had helped", "would have helped", "Tercer condicional para situaciones pasadas imposibles."),
        ("B2", "Modales Pasados", "He is not answering. He _____ have left already.", "must", "should", "ought", "would", "must", "'Must have' expresa deducción lógica con alta certeza."),
        ("B2", "Wish", "I wish I _____ more time to study.", "have", "had", "would have", "having", "had", "Wish para deseos presentes usa pasado simple."),
        ("C1", "Inversión", "Hardly _____ the house when the storm began.", "I had left", "had I left", "I did leave", "did I left", "had I left", "Adverbios negativos iniciales exigen inversión auxiliar-sujeto."),
        ("C1", "Cláusulas", "_____ the exam, she celebrated with her friends.", "Having passed", "Passed", "Have passed", "Passing by", "Having passed", "Participio perfecto para indicar acción previa."),
        ("C1", "Subjuntivo", "The manager insisted that he _____ on time.", "is", "be", "was", "would be", "be", "Estructura de subjuntivo formal en inglés (base form)."),
        ("C2", "Precisión Léxica", "His argument was so _____ that no one could refute it.", "persuasive", "cogent", "believable", "plausible", "cogent", "'Cogent' connota argumento lúcido e irrefutable."),
        ("C2", "Idioms", "She passed the exam with flying _____.", "flags", "colors", "marks", "scores", "colors", "'With flying colors' significa con honores/excelente nota.")
    ]
    for q_lvl, q_cat, q_txt, o1, o2, o3, o4, cor, exp in quiz_seed:
        c.execute("INSERT OR IGNORE INTO quizzes (level, category, question, op1, op2, op3, op4, correct, explanation) SELECT ?, ?, ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM quizzes WHERE question = ?)", (q_lvl, q_cat, q_txt, o1, o2, o3, o4, cor, exp, q_txt))

    conn.commit()
    conn.close()

def get_courses():
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    c.execute("SELECT id, name, current_unit, total_units, current_step, last_study FROM courses")
    data = c.fetchall()
    conn.close()
    return data

def update_course(cid, unit, step):
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    c.execute("UPDATE courses SET current_unit = ?, current_step = ?, last_study = ? WHERE id = ?",
              (unit, step, str(datetime.now().strftime("%Y-%m-%d %H:%M")), cid))
    conn.commit()
    conn.close()

def log_session(minutes, focus):
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    c.execute("INSERT INTO study_sessions (date, duration_min, focus_area) VALUES (?, ?, ?)",
              (str(datetime.now().strftime("%Y-%m-%d %H:%M")), minutes, focus))
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

def get_pomodoro_analytics():
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    c.execute("SELECT date, duration_min, focus_area FROM study_sessions")
    all_sessions = c.fetchall()
    conn.close()
    
    total_min = 0
    week_min = 0
    month_min = 0
    by_area = {}
    
    now = datetime.now()
    start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    current_year_month = now.strftime("%Y-%m")
    
    for dt_str, dur, area in all_sessions:
        total_min += dur
        by_area[area] = by_area.get(area, 0) + dur
        
        try:
            session_dt = datetime.strptime(dt_str[:16], "%Y-%m-%d %H:%M")
            if session_dt >= start_of_week:
                week_min += dur
            if dt_str.startswith(current_year_month):
                month_min += dur
        except Exception:
            if dt_str.startswith(current_year_month):
                month_min += dur

    total_xp = (total_min * 10) + 100
    level_tier = "Traveler (Nv 3)" if total_xp < 1000 else ("Talker (Nv 4)" if total_xp < 2500 else "Fluent (Nv 6)")

    return {
        "total_hours": round(total_min / 60, 1),
        "total_min": total_min,
        "week_hours": round(week_min / 60, 1),
        "week_min": week_min,
        "month_hours": round(month_min / 60, 1),
        "month_min": month_min,
        "total_xp": total_xp,
        "level_tier": level_tier,
        "by_area": sorted(by_area.items(), key=lambda x: x[1], reverse=True)
    }

def get_flashcards(level, filter_mode="Todas"):
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    if level == "Todos":
        c.execute("SELECT f.id, f.level, f.category, f.front, f.back, COALESCE(p.mastered, 0) FROM flashcards f LEFT JOIN flashcard_progress p ON f.id = p.card_id")
    else:
        c.execute("SELECT f.id, f.level, f.category, f.front, f.back, COALESCE(p.mastered, 0) FROM flashcards f LEFT JOIN flashcard_progress p ON f.id = p.card_id WHERE f.level = ?", (level,))
    rows = c.fetchall()
    conn.close()
    if filter_mode == "Solo Pendientes":
        return [r for r in rows if r[5] == 0]
    elif filter_mode == "Solo Dominadas":
        return [r for r in rows if r[5] == 1]
    return rows

def update_card_mastery(card_id, mastered):
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO flashcard_progress (card_id, mastered, review_count, last_reviewed)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(card_id) DO UPDATE SET
            mastered = excluded.mastered,
            review_count = review_count + 1,
            last_reviewed = excluded.last_reviewed
    """, (card_id, mastered, str(datetime.now().strftime("%Y-%m-%d %H:%M"))))
    conn.commit()
    conn.close()

def get_quiz_questions(level, requested_count=25):
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    if level == "Todos":
        c.execute("SELECT id, level, category, question, op1, op2, op3, op4, correct, explanation FROM quizzes")
    else:
        c.execute("SELECT id, level, category, question, op1, op2, op3, op4, correct, explanation FROM quizzes WHERE level = ?", (level,))
    base_rows = c.fetchall()
    conn.close()
    if not base_rows:
        return []
    
    selected = []
    pool = list(base_rows)
    random.shuffle(pool)
    while len(selected) < requested_count:
        for r in pool:
            selected.append(r)
            if len(selected) == requested_count:
                break
        random.shuffle(pool)
    return selected

def save_quiz_score(level, score, total):
    pct = int((score / total) * 100) if total > 0 else 0
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    c.execute("INSERT INTO quiz_history (date, level, score, total, pct) VALUES (?, ?, ?, ?, ?)",
              (str(datetime.now().strftime("%Y-%m-%d %H:%M")), level, score, total, pct))
    conn.commit()
    conn.close()
    log_session_notion(f"Quiz Nivel {level}", "Quiz", score)

init_db()

# =========================================================
# 3. INTERFAZ Y ESTILOS
# =========================================================
st.set_page_config(page_title="English Mastery Hub | Lorena Alvarez", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    header[data-testid="stHeader"] { visibility: hidden; height: 0%; }
    .block-container { padding-top: 1.8rem; padding-bottom: 2rem; max-width: 1200px; }
    .glass-card { background: linear-gradient(135deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.85) 100%); border: 1px solid rgba(148, 163, 184, 0.18); border-radius: 18px; padding: 1.5rem; margin-bottom: 1.2rem; }
    .stat-box { background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 14px; padding: 1rem; text-align: center; }
    .stat-number { font-size: 1.8rem; font-weight: 800; color: #38BDF8; line-height: 1.2; }
    .stat-label { font-size: 0.8rem; font-weight: 600; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }
    .profile-card { background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 16px; padding: 1rem; text-align: center; margin-bottom: 1.2rem; }
    .profile-name { font-size: 1.15rem; font-weight: 700; color: #F8FAFC; margin-top: 8px; margin-bottom: 2px; }
    .profile-role { font-size: 0.8rem; color: #38BDF8; font-weight: 600; }
    .tag-badge { display: inline-block; background: rgba(56, 189, 248, 0.18); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.35); padding: 4px 12px; border-radius: 9999px; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.8rem; }
    .flashcard-display { background: linear-gradient(145deg, #1E293B, #0F172A); border: 1px solid #38BDF8; border-radius: 20px; padding: 2.8rem 1.5rem; text-align: center; margin: 1.5rem 0; }
    .platform-btn { display: block; text-align: center; background: #1E293B; color: #F8FAFC !important; font-weight: 700; padding: 13px; border-radius: 12px; border: 1px solid rgba(148, 163, 184, 0.2); text-decoration: none; margin-top: 10px; }
    .btn-hotmart-link { display: inline-block; background: linear-gradient(135deg, #EA580C 0%, #C2410C 100%); color: white !important; font-weight: 700; padding: 10px 18px; border-radius: 10px; text-decoration: none; margin-bottom: 14px; }
    .badge-icon-box { width: 62px; height: 62px; border-radius: 18px; margin: 0 auto 8px auto; display: flex; align-items: center; justify-content: center; font-size: 1.7rem; }
    .badge-peach { background: #FFEDD5; }
    .badge-blue  { background: #E0F2FE; }
    .badge-pink  { background: #FFE4E6; }
    .badge-tan   { background: #FEF3C7; }
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
        <div style="font-size:0.75rem; color:#94A3B8; margin-top:4px;">🎯 Meta Activa: Fluidez Total</div>
    </div>
    """, unsafe_allow_html=True)

menu = st.sidebar.radio("Navegación:", [
    "⏱️ Focus & Pomodoro (15-20m)",
    "🗣️ Speaking & Feedback Lab",
    "📱 App Inglés Práctico (Biblioteca)",
    "🌐 Hub de Plataformas & Apps",
    "🎧 Listening & Inmersión",
    "✍️ Writing Clinic",
    "🗺️ Ruta de Hitos (A0 a C2)",
    "🗂️ Flashcards Activas",
    "📝 Quizzes & Evaluaciones"
])

st.sidebar.divider()
st.sidebar.markdown("### 📝 Cuaderno Digital")
st.sidebar.markdown(
    '<a href="goodnotes://" target="_blank" style="text-decoration:none;">'
    '<button style="width:100%; background:#0284C7; color:white; border:none; padding:12px; border-radius:10px; font-weight:700; cursor:pointer;">'
    '📖 Abrir Goodnotes'
    '</button></a>',
    unsafe_allow_html=True
)

# --- 1. FOCUS & POMODORO ---
if menu == "⏱️ Focus & Pomodoro (15-20m)":
    st.markdown("## ⏱️ Sesión de Estudio Focalizado & Métricas")
    analytics = get_pomodoro_analytics()
    
    c_st1, c_st2, c_st3, c_st4 = st.columns(4)
    with c_st1:
        st.markdown(f'<div class="stat-box"><div class="stat-number">{analytics["week_hours"]}h</div><div class="stat-label">Esta Semana</div><div style="font-size:0.75rem; color:#64748B;">{analytics["week_min"]} min</div></div>', unsafe_allow_html=True)
    with c_st2:
        st.markdown(f'<div class="stat-box"><div class="stat-number">{analytics["month_hours"]}h</div><div class="stat-label">Este Mes</div><div style="font-size:0.75rem; color:#64748B;">{analytics["month_min"]} min</div></div>', unsafe_allow_html=True)
    with c_st3:
        st.markdown(f'<div class="stat-box"><div class="stat-number">{analytics["total_hours"]}h</div><div class="stat-label">Total Acumulado</div><div style="font-size:0.75rem; color:#64748B;">{analytics["total_min"]} min</div></div>', unsafe_allow_html=True)
    with c_st4:
        top_area = analytics['by_area'][0][0] if analytics['by_area'] else "Sin registro"
        top_short = top_area.split(":")[0] if ":" in top_area else top_area
        st.markdown(f'<div class="stat-box"><div class="stat-number" style="font-size:1.2rem; color:#F59E0B; margin-top:6px;">{top_short}</div><div class="stat-label">Habilidad Líder</div><div style="font-size:0.75rem; color:#64748B;">Mayor tiempo</div></div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="glass-card" style="margin-top:1.2rem; padding:1.2rem;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <div style="font-size:1.15rem; font-weight:700; color:#F8FAFC;">{analytics['level_tier']}</div>
            <div style="font-size:1.15rem; font-weight:800; color:#38BDF8;">{analytics['total_xp']} XP</div>
        </div>
        <div style="background:rgba(255,255,255,0.1); border-radius:9999px; height:8px; overflow:hidden;">
            <div style="background:linear-gradient(90deg, #0284C7, #38BDF8); width:{min(int((analytics['total_xp']/3000)*100), 100)}%; height:100%;"></div>
        </div>
        <div style="font-size:0.75rem; color:#94A3B8; margin-top:6px;">Faltan {max(3000 - analytics['total_xp'], 100)} XP para el siguiente rango</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### 🏆 Logros de Consistencia")
    cb1, cb2, cb3, cb4 = st.columns(4)
    with cb1:
        st.markdown('<div style="text-align:center;"><div class="badge-icon-box badge-peach">☀️</div><div style="font-weight:700; font-size:0.85rem; color:#F8FAFC;">Early Bird</div></div>', unsafe_allow_html=True)
    with cb2:
        st.markdown('<div style="text-align:center;"><div class="badge-icon-box badge-blue">🌱</div><div style="font-weight:700; font-size:0.85rem; color:#F8FAFC;">First Step</div></div>', unsafe_allow_html=True)
    with cb3:
        st.markdown('<div style="text-align:center;"><div class="badge-icon-box badge-pink">🔥</div><div style="font-weight:700; font-size:0.85rem; color:#F8FAFC;">Warming Up</div></div>', unsafe_allow_html=True)
    with cb4:
        st.markdown('<div style="text-align:center;"><div class="badge-icon-box badge-tan">📖</div><div style="font-weight:700; font-size:0.85rem; color:#F8FAFC;">Module Down</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown('<div class="glass-card"><span class="tag-badge">TEMPORIZADOR</span><div style="font-size:1.2rem; font-weight:700; color:#F8FAFC;">Configurar bloque de hoy</div></div>', unsafe_allow_html=True)
        tiempo_foco = st.select_slider("Duración de la sesión:", options=[5, 10, 15, 20, 25, 30], value=15)
        enfoque = st.selectbox("Área a trabajar:", [
            "Speaking: Práctica con IA",
            "Speaking: Speak & Improve (Cambridge)",
            "Listening: BBC & YouGlish",
            "Writing: Taller de Redacción",
            "Práctica: Duolingo & Racha",
            "Inglés Práctico: App & Biblioteca",
            "Curso: Gringo Academy (Hotmart)",
            "Memoria: Flashcards (A0 a C2)",
            "Evaluación: Quizzes"
        ])
        if st.button("🔥 Iniciar y Registrar Sesión", use_container_width=True):
            log_session(tiempo_foco, enfoque)
            st.toast("✅ ¡Sesión guardada!")
            st.rerun()

    with c2:
        st.markdown('<div class="glass-card"><span class="tag-badge">HISTORIAL</span><div style="font-size:1.2rem; font-weight:700; color:#F8FAFC;">Últimas sesiones</div></div>', unsafe_allow_html=True)
        sesiones = get_recent_sessions()
        if sesiones:
            for s_date, s_min, s_focus in sesiones:
                st.markdown(f"• **{s_min} min** — {s_focus} <span style='color:#64748B; font-size:0.8rem;'>({s_date})</span>", unsafe_allow_html=True)

    if analytics["by_area"]:
        st.markdown("### 📊 Distribución de tiempo")
        total_time = analytics["total_min"] if analytics["total_min"] > 0 else 1
        for area_name, mins in analytics["by_area"]:
            pct_area = int((mins / total_time) * 100)
            hrs = round(mins / 60, 1)
            cl, cp = st.columns([3, 1])
            cl.markdown(f"**{area_name}** • {hrs} hrs ({mins} min)")
            cp.markdown(f"<div style='text-align:right; font-weight:700; color:#38BDF8;'>{pct_area}%</div>", unsafe_allow_html=True)
            st.progress(pct_area / 100)

# --- 2. SPEAKING LAB: SOLO CORRECCIÓN ESCRITA + CAMBRIDGE ---
elif menu == "🗣️ Speaking & Feedback Lab":
    st.markdown("## 🗣️ Speaking & Feedback Lab")
    
    st.markdown("""
    <div class="glass-card" style="display:flex; justify-content:space-between; align-items:center; border: 1px solid rgba(234, 88, 12, 0.4);">
        <div>
            <span class="tag-badge" style="background:rgba(234, 88, 12, 0.2); color:#FB923C;">EVALUACIÓN ORAL OFICIAL</span>
            <div style="font-size:1.05rem; font-weight:700; color:#F8FAFC;">¿Quieres hablar con Sandi de Cambridge?</div>
            <div style="font-size:0.85rem; color:#94A3B8;">Habla con el evaluador acústico oficial de Cambridge English para medir tu nivel oral (A1-C2).</div>
        </div>
        <a href="https://speakandimprove.com" target="_blank" style="text-decoration:none;">
            <button style="background:linear-gradient(135deg, #EA580C 0%, #C2410C 100%); color:white; border:none; padding:10px 18px; border-radius:10px; font-weight:700; cursor:pointer;">
                Abrir Speak & Improve
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)

    prompts = [
        "Introduce yourself: your name, where you live, and your age. (A0)",
        "Describe your typical morning routine in 3 sentences. (A1)",
        "What did you do yesterday afternoon? Mention 2 activities. (A2)",
        "Explain a difficult situation at work and how you handled it. (B1/B2)",
        "Why is continuous learning essential for professional development? (C1/C2)"
    ]
    tema = st.selectbox("Elige tu reto de hoy:", prompts)
    st.info(f"🗣️ **Prompt:** \"{tema}\"")

    user_text = st.text_area("Escribe tu respuesta en inglés para analizar:", placeholder="Escribe aquí tu texto en inglés...", height=120)
    if st.button("🤖 Analizar y Corregir con IA", use_container_width=True):
        if not user_text.strip():
            st.warning("Escribe al menos una frase antes de analizar.")
        else:
            with st.spinner("Tu tutora de IA está analizando tu gramática y estilo..."):
                retro = evaluate_speech_with_ai(tema, user_text)
                ok, msg = log_speaking_notion(tema, user_text, retro)
                if ok:
                    st.toast("✅ ¡Registro guardado en Notion!")
                st.markdown('<div class="glass-card"><span class="tag-badge">RETROALIMENTACIÓN SINCRONIZADA</span>', unsafe_allow_html=True)
                st.markdown(retro)
                st.markdown('</div>', unsafe_allow_html=True)

# --- 3. APP INGLÉS PRÁCTICO & GRINGO ACADEMY (ORDENADO) ---
elif menu == "📱 App Inglés Práctico (Biblioteca)":
    st.markdown("## 📱 App Inglés Práctico: Tu Nuevo Portal Dedicado")
    
    st.markdown("""
    <div class="glass-card" style="border: 1px solid rgba(249, 115, 22, 0.4); background: linear-gradient(135deg, rgba(30, 41, 59, 0.85) 0%, rgba(15, 23, 42, 0.95) 100%);">
        <span class="tag-badge" style="background:rgba(249, 115, 22, 0.18); color:#FB923C;">NUEVA APLICACIÓN OFICIAL</span>
        <h2 style="color:#F8FAFC; margin-top:8px;">📚 Biblioteca & Portal Inglés Práctico</h2>
        <p style="color:#CBD5E1; font-size:0.95rem;">Accede de inmediato a tus clases, descarga el material en PDF y consulta al asistente de IA.</p>
        <div style="display:flex; gap:12px; margin-top:14px; flex-wrap:wrap;">
            <a href="https://app.inglespractico.info" target="_blank" style="flex:1; min-width:200px; text-decoration:none;">
                <button style="width:100%; background:linear-gradient(135deg, #EA580C 0%, #C2410C 100%); color:white; border:none; padding:14px; border-radius:12px; font-weight:700; cursor:pointer;">
                    🚀 Abrir App Inglés Práctico
                </button>
            </a>
            <a href="https://app.inglespractico.info" target="_blank" style="flex:1; min-width:200px; text-decoration:none;">
                <button style="width:100%; background:#1E293B; color:#F8FAFC; border:1px solid rgba(148, 163, 184, 0.3); padding:14px; border-radius:12px; font-weight:700; cursor:pointer;">
                    📖 Ir a Biblioteca de PDFs
                </button>
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 1. Registro de Inglés Práctico con su botón directamente abajo
    st.markdown("### 🎯 Registro de Semanas: Inglés Práctico")
    courses = dict((r[0], r) for r in get_courses())
    
    if "ingles_practico" in courses:
        cid, name, unit, total, step, last = courses["ingles_practico"]
        st.markdown(f'<div class="glass-card"><span class="tag-badge">ACTIVACIÓN NEURAL</span><div style="font-size:1.2rem; font-weight:700; color:#F8FAFC;">{name}</div></div>', unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns([2, 1.2, 1])
        pct = int((unit / total) * 100) if total > 0 else 0
        col_a.progress(pct / 100)
        col_a.caption(f"Avance: **{unit} de {total} semanas** ({pct}%) | Última sesión: {last}")
        bloques = [f"Semana {i}" for i in range(1, 13)]
        idx_b = bloques.index(step) if step in bloques else 0
        nuevo_paso = col_b.selectbox("Semana actual:", bloques, index=idx_b, key="step_ip")
        nueva_unidad = col_c.number_input("Semana completada:", min_value=1, max_value=12, value=unit, key="unit_ip")
        if col_a.button("💾 Guardar Avance de Inglés Práctico", key="btn_ip"):
            update_course(cid, nueva_unidad, nuevo_paso)
            st.toast("✅ Progreso de Inglés Práctico guardado")
            st.rerun()

    st.markdown("---")

    # 2. Gringo Academy con su enlace directo a Hotmart y su propio botón abajo
    st.markdown("### 🎬 Gringo Academy (Método Inmersivo)")
    if "gringo" in courses:
        cid, name, unit, total, step, last = courses["gringo"]
        st.markdown(f"""
        <div class="glass-card">
            <span class="tag-badge">PLATAFORMA HOTMART</span>
            <div style="font-size:1.2rem; font-weight:700; color:#F8FAFC;">{name}</div>
            <p style="color:#94A3B8; font-size:0.85rem; margin:8px 0 12px 0;">Entra a ver tus telenovelas y episodios:</p>
            <a href="https://consumer.hotmart.com" target="_blank" class="btn-hotmart-link">
                🎬 Abrir Gringo Academy en Hotmart
            </a>
        </div>
        """, unsafe_allow_html=True)
        col_ga, col_gb, col_gc = st.columns([2, 1.2, 1])
        pct_g = int((unit / total) * 100) if total > 0 else 0
        col_ga.progress(pct_g / 100)
        col_ga.caption(f"Avance: **{unit} de {total} telenovelas** ({pct_g}%) | Última sesión: {last}")
        pasos = ["Paso 1: Vocabulario en contexto", "Paso 2: Gramática esencial", "Paso 3: Pronunciación nativa", "Paso 4: Examen de Listening", "Paso 5: Práctica de Speaking"]
        idx_p = pasos.index(step) if step in pasos else 0
        nuevo_paso_g = col_gb.selectbox("Fase actual:", pasos, index=idx_p, key="step_ga")
        nueva_unidad_g = col_gc.number_input("Telenovela / Bloque:", min_value=1, max_value=total, value=unit, key="unit_ga")
        if col_ga.button("💾 Guardar Avance de Gringo Academy", key="btn_ga"):
            update_course(cid, nueva_unidad_g, nuevo_paso_g)
            st.toast("✅ Progreso de Gringo Academy guardado")
            st.rerun()

# --- 4. HUB DE PLATAFORMAS & APPS ---
elif menu == "🌐 Hub de Plataformas & Apps":
    st.markdown("## 🌐 Centro de Plataformas & Práctica Gratuita")
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">OFICIAL CAMBRIDGE</span>
            <h3>🤖 Speak & Improve (Cambridge)</h3>
            <p style="color:#94A3B8;">Habla con Sandi el evaluador oficial de Cambridge para medir tu nivel oral exacto (A1 a C2).</p>
            <a href="https://speakandimprove.com" target="_blank" class="platform-btn" style="background: linear-gradient(135deg, #EA580C 0%, #C2410C 100%); color:white !important; border:none;">Abrir Speak & Improve</a>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">GAMIFICACIÓN & RACHA</span>
            <h3>🦉 Duolingo Web</h3>
            <p style="color:#94A3B8;">Vocabulario ágil y gramática intuitiva para mantener tu racha activa.</p>
            <a href="https://www.duolingo.com" target="_blank" class="platform-btn" style="background:#58CC02; color:white !important;">Abrir Duolingo</a>
        </div>
        """, unsafe_allow_html=True)
    with c_p2:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">PRONUNCIACIÓN REAL</span>
            <h3>🎬 YouGlish: Contexto en Video</h3>
            <p style="color:#94A3B8;">Escribe cualquier palabra o expresión y escúchala dicha por personas en YouTube.</p>
            <a href="https://youglish.com/pronounce/english" target="_blank" class="platform-btn" style="background:#E11D48; color:white !important;">Abrir YouGlish</a>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">AUDIO & NOTICIAS</span>
            <h3>📻 BBC Learning English</h3>
            <p style="color:#94A3B8;">Episodios de 6 minutos (*6 Minute English*) y pronunciación clara.</p>
            <a href="https://www.bbc.co.uk/learningenglish" target="_blank" class="platform-btn" style="background:#B80000; color:white !important;">Abrir BBC Learning English</a>
        </div>
        """, unsafe_allow_html=True)

# --- 5. LISTENING & INMERSIÓN ---
elif menu == "🎧 Listening & Inmersión":
    st.markdown("## 🎧 Listening & Gimnasio Auditivo")
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">MÉTODO AUDITIVO</span>
            <h3>1. El Filtro YouGlish (Connected Speech)</h3>
            <p style="color:#94A3B8;">Entrena cómo se enlazan las palabras en inglés hablado a velocidad normal.</p>
            <a href="https://youglish.com" target="_blank" class="platform-btn">Entrenar en YouGlish</a>
        </div>
        """, unsafe_allow_html=True)
    with col_l2:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">MICRO-INMERSIÓN</span>
            <h3>2. BBC 6 Minute English</h3>
            <p style="color:#94A3B8;">Historias breves de 6 minutos con transcripción completa.</p>
            <a href="https://www.bbc.co.uk/learningenglish/english/features/6-minute-english" target="_blank" class="platform-btn">Escuchar 6 Minute English</a>
        </div>
        """, unsafe_allow_html=True)

# --- 6. WRITING CLINIC ---
elif menu == "✍️ Writing Clinic":
    st.markdown("## ✍️ Writing Clinic: Taller de Redacción Profesional")
    w_topic = st.selectbox("Tipo de texto:", ["Diario personal / Reflexión del día", "Correo electrónico profesional", "Resumen de lo aprendido", "Redacción libre"])
    w_input = st.text_area("Tu borrador en inglés:", height=160, placeholder="Escribe aquí tu texto...")
    if st.button("✨ Analizar y Guardar en Notion", use_container_width=True):
        if not w_input.strip():
            st.warning("Escribe algo de texto antes de enviar.")
        else:
            with st.spinner("Examinando redacción..."):
                retro = evaluate_speech_with_ai(f"Writing Clinic ({w_topic})", w_input)
                ok, msg = log_writing_notion(w_topic, w_input, retro)
                if ok:
                    st.toast("✅ ¡Guardado en tu Notion!")
                st.markdown('<div class="glass-card"><span class="tag-badge">CORRECCIÓN EDITORIAL</span>', unsafe_allow_html=True)
                st.markdown(retro)
                st.markdown("</div>", unsafe_allow_html=True)

# --- 7. RUTA DE HITOS (A0 A C2) ---
elif menu == "🗺️ Ruta de Hitos (A0 a C2)":
    st.markdown("## 🗺️ Mapa Curricular: Del Nivel 0 a Nativo")
    tabs = st.tabs(["🟢 A0: Starter", "🌱 A1: Elemental", "🌿 A2: Pre-Intermedio", "🔷 B1: Intermedio", "💎 B2: Avanzado", "🏆 C1: Profesional", "👑 C2: Nativo"])
    with tabs[0]:
        st.markdown('<div class="glass-card"><span class="tag-badge">A0</span><h3>Fundamentos Absolutos</h3><p>Verbo To Be, pronombres, edad y presentación personal fluida.</p></div>', unsafe_allow_html=True)
    with tabs[1]:
        st.markdown('<div class="glass-card"><span class="tag-badge">A1</span><h3>Rutinas y Cotidiano</h3><p>Presente Simple, auxiliares do/does, preposiciones in/on/at.</p></div>', unsafe_allow_html=True)
    with tabs[2]:
        st.markdown('<div class="glass-card"><span class="tag-badge">A2</span><h3>Pasado y Planes</h3><p>Pasado Simple regular e irregular, continuo, going to vs will.</p></div>', unsafe_allow_html=True)
    with tabs[3]:
        st.markdown('<div class="glass-card"><span class="tag-badge">B1</span><h3>Autonomía Intermedia</h3><p>Present Perfect, condicionales 1 y 2, modales must/should.</p></div>', unsafe_allow_html=True)
    with tabs[4]:
        st.markdown('<div class="glass-card"><span class="tag-badge">B2</span><h3>Fluidez Profesional</h3><p>Voz pasiva, modales de deducción, condicional 3 y reuniones.</p></div>', unsafe_allow_html=True)
    with tabs[5]:
        st.markdown('<div class="glass-card"><span class="tag-badge">C1</span><h3>Dominio Técnico</h3><p>Inversiones gramaticales, subjuntivo y vocabulario avanzado.</p></div>', unsafe_allow_html=True)
    with tabs[6]:
        st.markdown('<div class="glass-card"><span class="tag-badge">C2</span><h3>Maestría Nativa</h3><p>Espontaneidad, modismos idiomáticos y control estilístico total.</p></div>', unsafe_allow_html=True)

# --- 8. SMART FLASHCARDS ---
elif menu == "🗂️ Flashcards Activas":
    st.markdown("## 🗂️ Smart Flashcards & Retención Activa")
    c_lvl, c_flt = st.columns([2, 2])
    with c_lvl:
        nivel_sel = st.selectbox("Nivel:", ["A0", "A1", "A2", "B1", "B2", "C1", "C2", "Todos"], index=0)
    with c_flt:
        filtro_vista = st.selectbox("Filtro:", ["Todas", "Solo Pendientes", "Solo Dominadas"], index=0)
    deck = get_flashcards(nivel_sel, filtro_vista)
    total_nivel = len(get_flashcards(nivel_sel, "Todas"))
    dominadas_nivel = len(get_flashcards(nivel_sel, "Solo Dominadas"))
    pct = int((dominadas_nivel / total_nivel) * 100) if total_nivel > 0 else 0
    st.progress(pct / 100)
    st.caption(f"🏆 Dominadas en **{nivel_sel}**: {dominadas_nivel} de {total_nivel} ({pct}%)")
    if deck:
        if "f_idx" not in st.session_state:
            st.session_state.f_idx = 0
        if "f_flip" not in st.session_state:
            st.session_state.f_flip = False
        card = deck[st.session_state.f_idx % len(deck)]
        card_id, card_lvl, card_cat, card_front, card_back, is_mastered = card
        st.markdown(f'<div class="flashcard-display"><span class="tag-badge">{card_lvl} • {card_cat}</span><h2 style="color:#38BDF8; font-size:2.1rem; margin:15px 0 0 0;">{card_front}</h2></div>', unsafe_allow_html=True)
        if st.session_state.f_flip:
            st.success(f"💡 {card_back}")
        b1, b2 = st.columns(2)
        if b1.button("👁️ Revelar Significado", use_container_width=True):
            st.session_state.f_flip = True
            st.rerun()
        if b2.button("➡️ Siguiente", use_container_width=True):
            st.session_state.f_idx += 1
            st.session_state.f_flip = False
            st.rerun()
        cf, cp = st.columns(2)
        if cf.button("❌ Repasar más", use_container_width=True):
            update_card_mastery(card_id, 0)
            st.session_state.f_idx += 1
            st.session_state.f_flip = False
            st.rerun()
        if cp.button("✅ ¡Dominada!", use_container_width=True):
            update_card_mastery(card_id, 1)
            st.session_state.f_idx += 1
            st.session_state.f_flip = False
            st.rerun()

# --- 9. QUIZZES & EVALUACIONES ---
elif menu == "📝 Quizzes & Evaluaciones":
    st.markdown("## 📝 Evaluaciones de Nivel")
    col1, col2 = st.columns([1.5, 1])
    with col1:
        nivel_q = col1.selectbox("Nivel a evaluar:", ["A0", "A1", "A2", "B1", "B2", "C1", "C2", "Todos"], index=0)
    with col2:
        cant_q = col2.selectbox("Preguntas:", [10, 25, 50, 100], index=1)
    if st.button(f"🚀 Iniciar Test ({cant_q} Preguntas)", use_container_width=True):
        st.session_state.preguntas_activas = get_quiz_questions(nivel_q, cant_q)
        st.session_state.quiz_evaluado = False
        st.rerun()
    if "preguntas_activas" in st.session_state and st.session_state.preguntas_activas:
        with st.form("quiz_form"):
            user_answers = {}
            for i, item in enumerate(st.session_state.preguntas_activas):
                qid, qlvl, qcat, qtext, op1, op2, op3, op4, corr, expl = item
                st.markdown(f"**{i+1}. {qtext}** ({qlvl})")
                user_answers[i] = st.radio(f"P_{i}", [op1, op2, op3, op4], key=f"ans_{i}", label_visibility="collapsed", index=None)
                st.markdown("---")
            if st.form_submit_button("🏁 Calificar"):
                aciertos = sum(1 for idx, item in enumerate(st.session_state.preguntas_activas) if user_answers.get(idx) == item[8])
                save_quiz_score(nivel_q, aciertos, len(st.session_state.preguntas_activas))
                st.session_state.quiz_evaluado = True
                st.session_state.ultimo_score = (aciertos, len(st.session_state.preguntas_activas), nivel_q)
                st.rerun()
    if st.session_state.get("quiz_evaluado", False):
        p, t, lvl = st.session_state.ultimo_score
        porcentaje = int((p/t)*100)
        st.markdown(f'<div class="glass-card"><span class="tag-badge">TEST COMPLETADO</span><div style="font-size:1.3rem; font-weight:700; color:#F8FAFC;">Puntaje: {p} de {t} ({porcentaje}%)</div></div>', unsafe_allow_html=True)
