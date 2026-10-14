import streamlit as st
import sqlite3
import random
import json
import urllib.request
import time
import os
from datetime import datetime

# =========================================================
# 0. TUTOR INTELIGENTE CON MULTI-FALLBACK Y ROBUSTEZ TOTAL
# =========================================================
def evaluate_speech_with_ai(prompt_text, user_response, is_spoken=False):
    api_key = str(st.secrets.get("GEMINI_API_KEY", "")).strip().strip('"').strip("'")
    if not api_key:
        return "⚠️ Configura GEMINI_API_KEY en Secrets de Streamlit para activar la retroalimentación."
    
    tipo_modalidad = "HABILIDAD ORAL / SPEAKING" if is_spoken else "ESCRITURA / WRITING"
    
    sys_prompt = f"""
    Eres una tutora nativa de inglés experta, empática y rigurosa para estudiantes hispanohablantes.
    Modalidad evaluada: {tipo_modalidad}.
    Reto o contexto asignado: "{prompt_text}"
    Respuesta entregada por la alumna: "{user_response}"

    Estructura tu retroalimentación exactamente con estas secciones:
    
    🎯 **Puntuación Global:** [Nota del 1 al 10]/10
    
    🔍 **Análisis Gramatical y Sintaxis:**
    - Identifica cada detalle de concordancia, tiempos verbales y puntuación.
    - Si detectas errores típicos de hispanohablantes (usar 'have' en vez de 'to be' para la edad, omisión de pronombres, preposiciones in/on/at), explica el porqué de forma clara y amable.
    
    ✨ **Versión Nivel Nativo (Natural Phrasing):**
    - Entrega la versión pulida exactamente como la diría un nativo contemporáneo en una conversación fluida.
    
    🗣️ **Guía Fonética y Pronunciación:**
    - Señala las 2 o 3 palabras clave con su pronunciación fonética simplificada en español (ej. comfortable -> KÖMF-ter-buhl) y consejos para enlazar sonidos (connected speech).
    
    💡 **Consejo de Oro para Recordar:**
    - Un truco o regla mnemotécnica rápida para fijar este aprendizaje.
    """
    
    payload = {
        "contents": [{"parts": [{"text": sys_prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 850}
    }
    data = json.dumps(payload).encode("utf-8")
    
    active_models = [
        "gemini-3.5-flash",
        "gemini-3.8-flash",
        "gemini-3.1-flash-lite",
        "gemini-flash-latest"
    ]
    
    last_error = ""
    for model_name in active_models:
        for _ in range(2):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"}
            )
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
                
    return f"Servidores momentáneamente ocupados ({last_error}). Vuelve a presionar el botón en unos segundos."

# =========================================================
# 1. BASE DE DATOS Y BANCO COMPLETO DE REACTIVOS
# =========================================================
def init_db():
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id TEXT PRIMARY KEY,
            name TEXT,
            current_unit INTEGER,
            total_units INTEGER,
            current_step TEXT,
            last_study TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            duration_min INTEGER,
            focus_area TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS flashcards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT,
            category TEXT,
            front TEXT,
            back TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS flashcard_progress (
            card_id INTEGER PRIMARY KEY,
            mastered INTEGER DEFAULT 0,
            review_count INTEGER DEFAULT 0,
            last_reviewed TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT,
            category TEXT,
            question TEXT,
            op1 TEXT,
            op2 TEXT,
            op3 TEXT,
            op4 TEXT,
            correct TEXT,
            explanation TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS quiz_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            level TEXT,
            score INTEGER,
            total INTEGER,
            pct INTEGER
        )
    """)
    
    c.execute("INSERT OR IGNORE INTO courses VALUES ('gringo', 'Gringo Academy (Método Inmersivo)', 1, 130, 'Paso 1: Vocabulario en contexto', ?)", (str(datetime.now().date()),))
    c.execute("INSERT OR IGNORE INTO courses VALUES ('neural', 'Inglés Práctico (Activación Neural - 12 Semanas)', 1, 12, 'Semana 1', ?)", (str(datetime.now().date()),))
    
    # Semillas de Flashcards (A0 a C2)
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
        ("C2", "Expresiones Idiomáticas y Matices", "To cut corners without compromising integrity", "Tomar atajos sin comprometer la integridad"),
        ("C2", "Maestría Nativa", "An unassuming yet quintessential approach", "Un enfoque sin pretensiones pero esencialmente representativo")
    ]
    for lvl, cat, fr, bk in cards_seed:
        c.execute("""
            INSERT OR IGNORE INTO flashcards (level, category, front, back)
            SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM flashcards WHERE front = ?)
        """, (lvl, cat, fr, bk, fr))

    # Semillas de Quizzes (A0 a C2)
    quiz_seed = [
        ("A0", "Edad", "Choose the correct sentence for age:", "I have 30 years", "I am 30 years old", "I am having 30 years", "I got 30 years", "I am 30 years old", "En inglés se utiliza el verbo To Be para la edad."),
        ("A0", "Origen", "How do you say 'Soy de México'?", "I am from Mexico", "I am of Mexico", "I have Mexico", "I live Mexico", "I am from Mexico", "Se usa 'from' para indicar procedencia."),
        ("A0", "Saludos", "Which greeting is used at night when arriving?", "Good night", "Good evening", "Goodbye", "See you", "Good evening", "'Good evening' se usa al llegar de noche; 'Good night' es para despedirse."),
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
        ("B1", "Modales", "You _____ wear a seatbelt while driving.", "must", "might", "can", "may", "must", "Indica obligación legal estricta."),
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
        c.execute("""
            INSERT OR IGNORE INTO quizzes (level, category, question, op1, op2, op3, op4, correct, explanation)
            SELECT ?, ?, ?, ?, ?, ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM quizzes WHERE question = ?)
        """, (q_lvl, q_cat, q_txt, o1, o2, o3, o4, cor, exp, q_txt))

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

def get_recent_sessions():
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    c.execute("SELECT date, duration_min, focus_area FROM study_sessions ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()
    return rows

def get_flashcards(level, filter_mode="Todas"):
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    if level == "Todos":
        c.execute("""
            SELECT f.id, f.level, f.category, f.front, f.back, COALESCE(p.mastered, 0)
            FROM flashcards f
            LEFT JOIN flashcard_progress p ON f.id = p.card_id
        """)
    else:
        c.execute("""
            SELECT f.id, f.level, f.category, f.front, f.back, COALESCE(p.mastered, 0)
            FROM flashcards f
            LEFT JOIN flashcard_progress p ON f.id = p.card_id
            WHERE f.level = ?
        """, (level,))
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

init_db()

# =========================================================
# 2. CONFIGURACIÓN Y ESTILOS MODERNOS
# =========================================================
st.set_page_config(
    page_title="English Mastery Hub | Lorena Alvarez",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<head>
    <meta name="google" content="notranslate">
</head>
<style>
    .block-container { padding-top: 1.8rem; padding-bottom: 2rem; max-width: 1200px; }
    .glass-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.85) 100%);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.35);
        backdrop-filter: blur(10px);
    }
    .profile-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 16px;
        padding: 1rem;
        text-align: center;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    .profile-name { font-size: 1.15rem; font-weight: 700; color: #F8FAFC; margin-top: 8px; margin-bottom: 2px; }
    .profile-role { font-size: 0.8rem; color: #38BDF8; font-weight: 600; letter-spacing: 0.5px; }
    .card-title { font-size: 1.25rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.5rem; }
    .tag-badge {
        display: inline-block;
        background: rgba(56, 189, 248, 0.18);
        color: #38BDF8;
        border: 1px solid rgba(56, 189, 248, 0.35);
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
    }
    .flashcard-display {
        background: linear-gradient(145deg, #1E293B, #0F172A);
        border: 1px solid #38BDF8;
        border-radius: 20px;
        padding: 2.8rem 1.5rem;
        text-align: center;
        margin: 1.5rem 0;
        box-shadow: 0 15px 35px rgba(56, 189, 248, 0.15);
    }
    div.stButton > button:first-child {
        border-radius: 10px;
        font-weight: 600;
        border: none;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(56, 189, 248, 0.3);
    }
    .platform-btn {
        display: block;
        text-align: center;
        background: #1E293B;
        color: #F8FAFC !important;
        font-weight: 700;
        padding: 13px;
        border-radius: 12px;
        border: 1px solid rgba(148, 163, 184, 0.2);
        text-decoration: none;
        margin-top: 10px;
        transition: all 0.2s;
    }
    .platform-btn:hover {
        background: #334155;
        border-color: #38BDF8;
        transform: translateY(-2px);
    }
    .btn-hotmart {
        display: inline-block;
        width: 100%;
        text-align: center;
        background: linear-gradient(135deg, #F97316 0%, #EA580C 100%);
        color: white !important;
        font-weight: 700;
        padding: 12px 16px;
        border-radius: 10px;
        text-decoration: none;
        box-shadow: 0 4px 12px rgba(234, 88, 12, 0.35);
        margin-top: 8px;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. NAVEGACIÓN LATERAL Y PERFIL PERSONALIZADO
# =========================================================
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

menu = st.sidebar.radio(
    "Navegación:",
    [
        "🌐 Hub de Plataformas & Apps",
        "🗣️ Speaking & Feedback Lab",
        "🎧 Listening & Inmersión",
        "✍️ Writing Clinic",
        "🎬 Hub de Cursos (Hotmart)",
        "🗺️ Ruta de Hitos (A0 a C2)",
        "🗂️ Flashcards Activas",
        "📝 Quizzes & Evaluaciones",
        "⏱️ Focus & Pomodoro (15-20m)"
    ]
)

st.sidebar.divider()
st.sidebar.markdown("### 📝 Cuaderno Digital")
st.sidebar.markdown(
    '<a href="goodnotes://" target="_blank" style="text-decoration:none;">'
    '<button style="width:100%; background:#0284C7; color:white; border:none; padding:12px; border-radius:10px; font-weight:700; cursor:pointer; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3);">'
    '📖 Abrir Goodnotes'
    '</button></a>',
    unsafe_allow_html=True
)

# =========================================================
# 4. MÓDULOS DE LA APLICACIÓN
# =========================================================

# --- 1. HUB DE PLATAFORMAS & APPS ---
if menu == "🌐 Hub de Plataformas & Apps":
    st.markdown("## 🌐 Centro de Plataformas & Práctica Gratuita")
    st.caption("Herramientas interactivas seleccionadas para practicar cada destreza sin costo.")
    
    c_p1, c_p2 = st.columns(2)
    with c_p1:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">GAMIFICACIÓN & RACHA</span>
            <h3>🦉 Duolingo Web</h3>
            <p style="color:#94A3B8;">Práctica de vocabulario ágil, ejercicios diarios y gramática intuitiva para no perder el hábito.</p>
            <a href="https://www.duolingo.com" target="_blank" class="platform-btn" style="background:#58CC02; color:white !important;">Abrir Duolingo</a>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">AUDIO & NOTICIAS NATIVAS</span>
            <h3>📻 BBC Learning English</h3>
            <p style="color:#94A3B8;">Episodios de 6 minutos (*6 Minute English*), noticias del mundo explicadas y pronunciación limpia.</p>
            <a href="https://www.bbc.co.uk/learningenglish" target="_blank" class="platform-btn" style="background:#B80000; color:white !important;">Abrir BBC Learning English</a>
        </div>
        """, unsafe_allow_html=True)
        
    with c_p2:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">OÍDO & MÚSICA</span>
            <h3>🎵 LingoClip (LyricsTraining)</h3>
            <p style="color:#94A3B8;">Entrena tu comprensión auditiva rellenando la letra de tus canciones en inglés en tiempo real.</p>
            <a href="https://lingoclip.com" target="_blank" class="platform-btn" style="background:#0284C7; color:white !important;">Abrir LingoClip</a>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">PRONUNCIACIÓN REAL EN VIDEO</span>
            <h3>🎬 YouGlish: Contexto en Video</h3>
            <p style="color:#94A3B8;">Escribe cualquier palabra o frase y YouGlish te muestra miles de videos de YouTube con personas reales pronunciándola.</p>
            <a href="https://youglish.com/pronounce/english" target="_blank" class="platform-btn" style="background:#E11D48; color:white !important;">Abrir YouGlish</a>
        </div>
        """, unsafe_allow_html=True)

# --- 2. SPEAKING & FEEDBACK LAB ---
elif menu == "🗣️ Speaking & Feedback Lab":
    st.markdown("## 🗣️ Speaking & Feedback con Inteligencia Artificial")
    st.caption("Practica respuestas orales o escritas y recibe corrección instantánea de pronunciación, gramática y estilo nativo.")

    prompts = [
        "Introduce yourself: your name, where you live, and your age. (A0)",
        "Describe your typical morning routine in 3 sentences. (A1)",
        "What did you do yesterday afternoon? Mention 2 activities. (A2)",
        "Explain a difficult situation at work and how you handled it. (B1/B2)",
        "Why is continuous learning essential for professional development? (C1/C2)"
    ]
    tema = st.selectbox("Elige tu reto de hoy:", prompts)
    st.info(f"🗣️ **Prompt de práctica:** \"{tema}\"")

    modo = st.radio("Modalidad de práctica:", ["✍️ Escrito (Corrección Inmediata con IA)", "🎙️ Hablado (Grabación y Práctica de Voz)"], horizontal=True)

    if modo == "✍️ Escrito (Corrección Inmediata con IA)":
        user_text = st.text_area("Escribe tu respuesta en inglés:", placeholder="Escribe aquí tu frase...", height=120)
        if st.button("🤖 Analizar y Corregir con IA", use_container_width=True):
            if not user_text.strip():
                st.warning("Escribe al menos una frase en inglés antes de analizar.")
            else:
                with st.spinner("Tu tutora de IA está analizando tu respuesta..."):
                    retro = evaluate_speech_with_ai(tema, user_text, is_spoken=False)
                    st.markdown("""
                    <div class="glass-card">
                        <span class="tag-badge">RETROALIMENTACIÓN PERSONALIZADA</span>
                    """, unsafe_allow_html=True)
                    st.markdown(retro)
                    st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("#### 🎧 Grabación de Audio Directa")
        audio_grabado = st.audio_input("Presiona para grabar tu pronunciación:")
        if audio_grabado:
            st.audio(audio_grabado)
            st.success("¡Audio grabado! Escucha tu entonación.")
            
        speech_text = st.text_area("Borrador o transcripción de lo que hablaste en voz alta:", placeholder="Escribe aquí lo que dijiste para que la IA evalúe la fonética y el contenido...", height=100)
        if st.button("🤖 Evaluar Pronunciación y Contenido con IA", use_container_width=True):
            if not speech_text.strip():
                st.warning("Escribe el texto de lo que hablaste para que la IA pueda darte la corrección fonética y gramatical.")
            else:
                with st.spinner("Tu tutora de IA está evaluando tu respuesta oral y fonética..."):
                    retro = evaluate_speech_with_ai(tema, speech_text, is_spoken=True)
                    st.markdown("""
                    <div class="glass-card">
                        <span class="tag-badge">ANÁLISIS DE SPEAKING Y FONÉTICA</span>
                    """, unsafe_allow_html=True)
                    st.markdown(retro)
                    st.markdown("</div>", unsafe_allow_html=True)

# --- 3. LISTENING & INMERSIÓN ---
elif menu == "🎧 Listening & Inmersión":
    st.markdown("## 🎧 Listening & Gimnasio Auditivo")
    st.caption("Estrategias y herramientas para afinar el oído al inglés de velocidad natural.")
    
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">MÉTODO AUDITIVO</span>
            <h3>1. El Filtro YouGlish (Connected Speech)</h3>
            <p style="color:#94A3B8;">Los nativos no hablan palabra por palabra; enlazan sonidos (ejemplo: <em>'going to'</em> suena <em>'gonna'</em>, <em>'did you'</em> suena <em>'didya'</em>). Busca estas contracciones en YouGlish para escucharlas en cientos de charlas reales.</p>
            <a href="https://youglish.com" target="_blank" class="platform-btn">Entrenar en YouGlish</a>
        </div>
        """, unsafe_allow_html=True)
    with col_l2:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">MICRO-INMERSIÓN</span>
            <h3>2. BBC 6 Minute English</h3>
            <p style="color:#94A3B8;">Historias breves de 6 minutos con transcripción completa. Escucha primero sin leer y en la segunda vuelta revisa el texto para identificar las palabras que se te escaparon.</p>
            <a href="https://www.bbc.co.uk/learningenglish/english/features/6-minute-english" target="_blank" class="platform-btn">Escuchar 6 Minute English</a>
        </div>
        """, unsafe_allow_html=True)

# --- 4. WRITING CLINIC ---
elif menu == "✍️ Writing Clinic":
    st.markdown("## ✍️ Writing Clinic: Taller de Redacción Profesional")
    st.caption("Escribe tus correos, notas de estudio, diarios o pensamientos y recibe pulido de estilo.")
    
    w_topic = st.selectbox("Tipo de texto a redactar:", [
        "Diario personal / Reflexión del día",
        "Correo electrónico profesional o de negocios",
        "Resumen de lo aprendido hoy",
        "Redacción libre"
    ])
    w_input = st.text_area("Tu borrador en inglés:", height=160, placeholder="Escribe aquí tu texto en inglés tal como te salga de la mente...")
    if st.button("✨ Analizar y Pulir con IA", use_container_width=True):
        if not w_input.strip():
            st.warning("Escribe algo de texto antes de enviar a corrección.")
        else:
            with st.spinner("Tu tutora de IA está examinando tu redacción..."):
                retro = evaluate_speech_with_ai(f"Writing Clinic ({w_topic})", w_input, is_spoken=False)
                st.markdown("""
                <div class="glass-card">
                    <span class="tag-badge">CORRECCIÓN Y ESTILO EDITORIAL</span>
                """, unsafe_allow_html=True)
                st.markdown(retro)
                st.markdown("</div>", unsafe_allow_html=True)

# --- 5. HUB DE CURSOS (HOTMART) ---
elif menu == "🎬 Hub de Cursos (Hotmart)":
    st.markdown("## 🎬 Centro de Mando: Hotmart")
    st.caption("Gestiona tu avance y entra directamente a ver tus lecciones en la plataforma oficial.")
    
    col_cta1, col_cta2 = st.columns([1, 1])
    with col_cta1:
        st.markdown('<a href="https://consumer.hotmart.com" target="_blank" class="btn-hotmart">🚀 Abrir Mis Cursos en Hotmart</a>', unsafe_allow_html=True)
    with col_cta2:
        st.markdown('<a href="https://app.hotmart.com" target="_blank" class="btn-hotmart" style="background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%); box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35);">📱 Hotmart Club Directo</a>', unsafe_allow_html=True)
    
    st.divider()
    courses = get_courses()
    for row in courses:
        cid, name, unit, total, step, last = row[0], row[1], row[2], row[3], row[4], row[5]
        st.markdown(f"""
        <div class="glass-card">
            <span class="tag-badge">CURSO ACTIVO</span>
            <div class="card-title">{name}</div>
        </div>
        """, unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns([2, 1.2, 1])
        pct = int((unit / total) * 100) if total > 0 else 0
        col_a.progress(pct / 100)
        col_a.caption(f"Avance: **{unit} de {total}** ({pct}%) | Última sesión: {last}")
        if cid == "gringo":
            pasos = ["Paso 1: Vocabulario en contexto", "Paso 2: Gramática esencial", "Paso 3: Pronunciación nativa", "Paso 4: Examen de Listening", "Paso 5: Práctica de Speaking"]
            idx_p = pasos.index(step) if step in pasos else 0
            nuevo_paso = col_b.selectbox("Fase actual:", pasos, index=idx_p, key=f"step_{cid}")
            nueva_unidad = col_c.number_input("Telenovela / Bloque:", min_value=1, max_value=total, value=unit, key=f"unit_{cid}")
        else:
            bloques = [f"Semana {i}" for i in range(1, 13)]
            idx_b = bloques.index(step) if step in bloques else 0
            nuevo_paso = col_b.selectbox("Semana actual:", bloques, index=idx_b, key=f"step_{cid}")
            nueva_unidad = col_c.number_input("Unidad completada:", min_value=1, max_value=12, value=unit, key=f"unit_{cid}")
        if col_a.button(f"💾 Guardar {cid.capitalize()}", key=f"btn_{cid}"):
            update_course(cid, nueva_unidad, nuevo_paso)
            st.toast("Progreso actualizado")
            st.rerun()

# --- 6. RUTA DE HITOS (A0 A C2) ---
elif menu == "🗺️ Ruta de Hitos (A0 a C2)":
    st.markdown("## 🗺️ Mapa Curricular y Temario: Del Nivel 0 a Nativo")
    st.caption("Guía de objetivos, gramática y vocabulario indispensable en cada escalón del Marco Común Europeo.")

    tabs = st.tabs([
        "🟢 A0: Starter",
        "🌱 A1: Elemental",
        "🌿 A2: Pre-Intermedio",
        "🔷 B1: Intermedio",
        "💎 B2: Avanzado Fluido",
        "🏆 C1: Profesional",
        "👑 C2: Maestría Nativa"
    ])

    with tabs[0]:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">NIVEL A0: PRIMEROS PASOS</span>
            <div class="card-title">Fundamentos Absolutos</div>
            <p><strong>Meta:</strong> Eliminar el bloqueo inicial y pronunciar frases clave sin traducir mentalmente.</p>
            <ul>
                <li><strong>Gramática clave:</strong> Verbo To Be (afirmación, negación, pregunta), pronombres personales, adjetivos posesivos (my, your, her, his).</li>
                <li><strong>Expresiones fijas:</strong> Edad (I am ... years old), presentación (I am from...), números y alfabeto en deletreo.</li>
                <li><strong>Hito evaluable:</strong> Presentarte a ti misma, decir tu profesión, origen y edad con pronunciación fluida.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with tabs[1]:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">NIVEL A1: ELEMENTAL</span>
            <div class="card-title">Rutinas y Entorno Cotidiano</div>
            <p><strong>Meta:</strong> Hablar sobre hábitos diarios, gustos, familia y ubicaciones básicas.</p>
            <ul>
                <li><strong>Gramática clave:</strong> Presente Simple (regla de tercera persona -s/-es), auxiliares <em>do / does / don't / doesn't</em>, preposiciones de tiempo y lugar (in, on, at).</li>
                <li><strong>Vocabulario:</strong> Comida, compras, horas, miembros de la familia y actividades de ocio.</li>
                <li><strong>Hito evaluable:</strong> Describir tu día típico de la mañana a la noche sin titubeos gramaticales.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with tabs[2]:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">NIVEL A2: PRE-INTERMEDIO</span>
            <div class="card-title">Pasado, Planes y Experiencias Inmediatas</div>
            <p><strong>Meta:</strong> Narrar eventos del día anterior o vacaciones y coordinar citas o viajes.</p>
            <ul>
                <li><strong>Gramática clave:</strong> Pasado Simple (verbos regulares -ed y los 50 irregulares más comunes), pasado continuo (was/were doing), futuro con <em>going to</em> vs <em>will</em>.</li>
                <li><strong>Vocabulario:</strong> Viajes, hoteles, direcciones, citas en el calendario y compras en tiendas.</li>
                <li><strong>Hito evaluable:</strong> Contar qué hiciste el fin de semana pasado y qué harás el próximo mes.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with tabs[3]:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">NIVEL B1: INTERMEDIO INDEPENDIENTE</span>
            <div class="card-title">Certificación Universitaria y Autonomía</div>
            <p><strong>Meta:</strong> Resolver imprevistos en viajes, argumentar opiniones y redactar correos de trabajo funcionales.</p>
            <ul>
                <li><strong>Gramática clave:</strong> Present Perfect (con <em>already, yet, just, since, for</em>), primer y segundo condicional (if + would), verbos modales de obligación y consejo (must, should, have to).</li>
                <li><strong>Vocabulario:</strong> Expresión de opiniones, acuerdos, desacuerdos y descripción de planes futuros condicionales.</li>
                <li><strong>Hito evaluable:</strong> Mantener una conversación de 15 minutos explicando tus metas académicas o de negocio.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with tabs[4]:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">NIVEL B2: INTERMEDIO ALTO</span>
            <div class="card-title">Fluidez Profesional y Técnica</div>
            <p><strong>Meta:</strong> Participar en reuniones de trabajo internacionales, debates y entender podcasts nativos sin subtítulos.</p>
            <ul>
                <li><strong>Gramática clave:</strong> Tercer condicional y mixtos, voz pasiva avanzada, verbos modales de deducción en pasado (must have been, could have done), phrasal verbs frecuentes.</li>
                <li><strong>Vocabulario:</strong> Negocios, tecnología, atención al cliente y gestión de proyectos.</li>
                <li><strong>Hito evaluable:</strong> Explicar un proceso técnico o defender una postura en un debate sin traducir mentalmente.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with tabs[5]:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">NIVEL C1: EFICACIA OPERATIVA AVANZADA</span>
            <div class="card-title">Dominio Académico y Especializado</div>
            <p><strong>Meta:</strong> Leer artículos de investigación, escribir ensayos estructurados y hablar con matices estilísticos.</p>
            <ul>
                <li><strong>Gramática clave:</strong> Inversión enfática (<em>Rarely had I seen...</em>), estructuras con subjuntivo, cláusulas de participio y conectores discursivos sofisticados (<em>nevertheless, notwithstanding, whereas</em>).</li>
                <li><strong>Vocabulario:</strong> Jerga clínica, terminología de UX/negocios y sutilezas retóricas.</li>
                <li><strong>Hito evaluable:</strong> Diseñar y presentar un pitch completo en inglés técnico.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with tabs[6]:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">NIVEL C2: MAESTRÍA NATIVA</span>
            <div class="card-title">Bilingüismo Completo y Espontaneidad</div>
            <p><strong>Meta:</strong> Comprender ironías, modismos culturales sutiles, dobles sentidos y expresarse con total naturalidad.</p>
            <ul>
                <li><strong>Gramática y estilo:</strong> Máxima flexibilidad sintáctica, modismos idiomáticos contemporáneos y control absoluto del tono.</li>
                <li><strong>Hito evaluable:</strong> Liderar entrevistas, debates improvisados o conferencias al mismo nivel que un orador nativo educado.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# --- 7. SMART FLASHCARDS ---
elif menu == "🗂️ Flashcards Activas":
    st.markdown("## 🗂️ Smart Flashcards & Retención Activa")
    st.caption("Repaso espaciado con todos los niveles desde A0 hasta C2.")
    
    niveles_disponibles = ["A0", "A1", "A2", "B1", "B2", "C1", "C2", "Todos"]
    c_lvl, c_flt = st.columns([2, 2])
    with c_lvl:
        nivel_sel = st.selectbox("Nivel de estudio:", niveles_disponibles, index=0)
    with c_flt:
        filtro_vista = st.selectbox("Ver tarjetas:", ["Todas", "Solo Pendientes", "Solo Dominadas"], index=0)
        
    deck = get_flashcards(nivel_sel, filtro_vista)
    total_nivel = len(get_flashcards(nivel_sel, "Todas"))
    dominadas_nivel = len(get_flashcards(nivel_sel, "Solo Dominadas"))
    pct = int((dominadas_nivel / total_nivel) * 100) if total_nivel > 0 else 0
    
    st.progress(pct / 100)
    st.caption(f"🏆 Dominadas en **{nivel_sel}**: **{dominadas_nivel} de {total_nivel}** ({pct}%)")
    
    if deck:
        if "f_idx" not in st.session_state:
            st.session_state.f_idx = 0
        if "f_flip" not in st.session_state:
            st.session_state.f_flip = False
        card = deck[st.session_state.f_idx % len(deck)]
        card_id, card_lvl, card_cat, card_front, card_back, is_mastered = card
        
        st.markdown(f"""
        <div class="flashcard-display">
            <span class="tag-badge">{card_lvl} • {card_cat}</span>
            <h2 style="color: #38BDF8; font-size: 2.1rem; margin: 15px 0 0 0;">{card_front}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.f_flip:
            st.success(f"💡 {card_back}")
            
        b1, b2 = st.columns(2)
        if b1.button("👁️ Revelar Significado", use_container_width=True):
            st.session_state.f_flip = True
            st.rerun()
        if b2.button("➡️ Siguiente Tarjeta", use_container_width=True):
            st.session_state.f_idx += 1
            st.session_state.f_flip = False
            st.rerun()
            
        c_f, c_p = st.columns(2)
        if c_f.button("❌ Repasar más", use_container_width=True):
            update_card_mastery(card_id, 0)
            st.session_state.f_idx += 1
            st.session_state.f_flip = False
            st.rerun()
        if c_p.button("✅ ¡La domino!", use_container_width=True):
            update_card_mastery(card_id, 1)
            st.session_state.f_idx += 1
            st.session_state.f_flip = False
            st.rerun()
    else:
        st.info(f"No hay tarjetas con el filtro actual para el nivel {nivel_sel}.")

# --- 8. QUIZZES & EVALUACIONES (10, 25, 50, 100 PREGUNTAS) ---
elif menu == "📝 Quizzes & Evaluaciones":
    st.markdown("## 📝 Centro de Evaluaciones y Tests")
    st.caption("Comprueba tus conocimientos con baterías de 10, 25, 50 o 100 preguntas por nivel.")
    
    niveles_quiz = ["A0", "A1", "A2", "B1", "B2", "C1", "C2", "Todos"]
    col1, col2 = st.columns([1.5, 1])
    with col1:
        nivel_q = col1.selectbox("Selecciona Nivel a Evaluar:", niveles_quiz, index=0)
    with col2:
        cant_q = col2.selectbox("Cantidad de preguntas para la ronda:", [10, 25, 50, 100], index=1)
        
    if st.button(f"🚀 Iniciar Test ({cant_q} Preguntas)", use_container_width=True):
        st.session_state.preguntas_activas = get_quiz_questions(nivel_q, cant_q)
        st.session_state.quiz_evaluado = False
        st.rerun()
        
    if "preguntas_activas" in st.session_state and st.session_state.preguntas_activas:
        st.markdown(f"### 📋 Evaluación en Curso ({len(st.session_state.preguntas_activas)} preguntas)")
        with st.form("quiz_form"):
            user_answers = {}
            for i, item in enumerate(st.session_state.preguntas_activas):
                qid, qlvl, qcat, qtext, op1, op2, op3, op4, corr, expl = item
                st.markdown(f"**Pregunta {i+1} de {len(st.session_state.preguntas_activas)}:** {qtext} <span style='color:#38BDF8; font-size:0.8rem;'>({qlvl} • {qcat})</span>", unsafe_allow_html=True)
                user_answers[i] = st.radio(f"P_{i}", [op1, op2, op3, op4], key=f"ans_{i}", label_visibility="collapsed", index=None)
                st.markdown("---")
            if st.form_submit_button("🏁 Calificar Evaluación Completa"):
                aciertos = sum(1 for idx, item in enumerate(st.session_state.preguntas_activas) if user_answers.get(idx) == item[8])
                save_quiz_score(nivel_q, aciertos, len(st.session_state.preguntas_activas))
                st.session_state.quiz_evaluado = True
                st.session_state.ultimo_score = (aciertos, len(st.session_state.preguntas_activas), nivel_q)
                st.rerun()
                
    if st.session_state.get("quiz_evaluado", False):
        p, t, lvl = st.session_state.ultimo_score
        porcentaje = int((p/t)*100)
        badge_color = "#10B981" if porcentaje >= 80 else ("#F59E0B" if porcentaje >= 60 else "#EF4444")
        st.markdown(f"""
        <div class="glass-card" style="border-left: 6px solid {badge_color};">
            <span class="tag-badge">EVALUACIÓN COMPLETADA</span>
            <div class="card-title">Resultado Final: {p} de {t} aciertos ({porcentaje}%)</div>
            <p style="color:#94A3B8;">Nivel evaluado: <strong>{lvl}</strong>. Sigue practicando para alcanzar el 100% de retención.</p>
        </div>
        """, unsafe_allow_html=True)

# --- 9. POMODORO ---
elif menu == "⏱️ Focus & Pomodoro (15-20m)":
    st.markdown("## ⏱️ Sesión de Estudio Focalizado")
    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">TEMPORIZADOR ACTIVO</span>
            <div class="card-title">Configurar bloque de hoy</div>
        </div>
        """, unsafe_allow_html=True)
        tiempo_foco = st.select_slider("Duración de la sesión:", options=[5, 10, 15, 20, 25, 30], value=15)
        enfoque = st.selectbox("Área a trabajar:", [
            "Speaking Lab: Práctica Oral con IA",
            "Listening: BBC & YouGlish",
            "Writing Clinic: Redacción de Textos",
            "Duolingo & Práctica de Racha",
            "Gringo Academy: Episodio / Telenovela",
            "Activación Neural: Audio e Inmersión Subconsciente",
            "Flashcards: Repaso Espaciado (Niveles A0 - C2)",
            "Quizzes & Evaluaciones de Nivel"
        ])
        if st.button("🔥 Iniciar y Registrar Sesión", use_container_width=True):
            log_session(tiempo_foco, enfoque)
            st.success(f"¡Sesión de **{tiempo_foco} min** guardada con éxito!")
    with c2:
        st.markdown("""
        <div class="glass-card">
            <span class="tag-badge">HISTORIAL RECIENTE</span>
            <div class="card-title">Últimas sesiones completadas</div>
        </div>
        """, unsafe_allow_html=True)
        sesiones = get_recent_sessions()
        if sesiones:
            for s_date, s_min, s_focus in sesiones:
                st.markdown(f"• **{s_min} min** — {s_focus} <span style='color:#64748B; font-size:0.8rem;'>({s_date})</span>", unsafe_allow_html=True)
