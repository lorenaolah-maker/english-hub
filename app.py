import streamlit as st
import sqlite3
import random
import json
import urllib.request
import time
from datetime import datetime

# =========================================================
# 0. TUTOR INTELIGENTE CON FALLBACK Y ROBUSTEZ TOTAL
# =========================================================
def evaluate_speech_with_ai(prompt_text, user_response, is_spoken=False):
    api_key = str(st.secrets.get("GEMINI_API_KEY", "")).strip().strip('"').strip("'")
    if not api_key:
        return "⚠️ Configura GEMINI_API_KEY en Secrets de Streamlit para activar la retroalimentación."
    
    tipo_modalidad = "HABILIDAD ORAL / SPEAKING" if is_spoken else "ESCRITURA / WRITING"
    
    sys_prompt = f"""
    Eres una tutora nativa de inglés experta, empática y rigurosa para estudiantes hispanohablantes.
    Modalidad evaluada: {tipo_modalidad}.
    Reto asignado: "{prompt_text}"
    Respuesta entregada por el alumno: "{user_response}"

    Tu objetivo es brindar retroalimentación exhaustiva estructurada exactamente en estas secciones:
    
    🎯 **Puntuación Global:** [Nota del 1 al 10]/10
    
    🔍 **Análisis Gramatical y Sintaxis:**
    - Identifica cada detalle de concordancia, tiempos verbales y puntuación.
    - Si se trata de errores típicos hispanohablantes (como usar 'have' en vez de 'to be' para la edad, omisión de pronombres, o preposiciones in/on/at), explica el porqué de forma clara y pedagógica.
    
    ✨ **Versión Nivel Nativo (Natural Phrasing):**
    - Entrega la versión pulida exactamente como la diría un nativo contemporáneo en una conversación real.
    
    🗣️ **Guía Fonética y Pronunciación:**
    - Señala las 2 o 3 palabras clave de la respuesta con su pronunciación fonética simplificada en español (ej. *comfortable -> KÖMF-ter-buhl*) y consejos para enlazar sonidos (connected speech).
    
    💡 **Consejo de Oro para Recordar:**
    - Una regla mnemotécnica o truco rápido para nunca más cometer ese error.
    """
    
    payload = {
        "contents": [{"parts": [{"text": sys_prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1000}
    }
    data = json.dumps(payload).encode("utf-8")
    
    candidate_models = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-3.8-flash"]
    last_error = ""
    
    for model_name in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                res_json = json.loads(response.read().decode("utf-8"))
                candidates = res_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
        except Exception as e:
            last_error = str(e)
            time.sleep(0.5)
            continue
            
    return f"No se pudo completar el análisis en este momento ({last_error}). Intenta nuevamente en unos segundos."

# =========================================================
# 1. BASE DE DATOS: CARGA Y EXPANSION DE NIVELES (A0 A C2)
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
        c.execute("INSERT OR IGNORE INTO flashcards (level, category, front, back) SELECT ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM flashcards WHERE front = ?)", (lvl, cat, fr, bk, fr))
        
    quiz_seed = [
        ("A0", "Edad", "Choose the correct sentence for age:", "I have 30 years", "I am 30 years old", "I am having 30 years", "I got 30 years", "I am 30 years old", "En inglés se utiliza el verbo To Be para expresar la edad."),
        ("A1", "Presente", "He _____ coffee every morning.", "drink", "drinks", "drinking", "is drink", "drinks", "En tercera persona singular (he/she/it) en presente simple se añade -s."),
        ("A2", "Pasado Simple", "Yesterday, we _____ to a new Italian restaurant.", "go", "gone", "went", "going", "went", "El pasado simple irregular del verbo 'go' es 'went'."),
        ("B1", "Present Perfect", "She has _____ in London since 2021.", "live", "lives", "lived", "living", "lived", "El Present Perfect se compone de have/has + participio pasado (lived)."),
        ("B2", "Voz Pasiva", "The new project _____ by the committee next week.", "will approve", "will be approved", "is approving", "approves", "will be approved", "Estructura de futuro pasivo: will + be + participio."),
        ("C1", "Inversión", "Hardly _____ the house when the storm began.", "I had left", "had I left", "I did leave", "did I left", "had I left", "Con adverbios negativos al inicio (Hardly, Scarcely) se invierte el auxiliar: had + sujeto + participio."),
        ("C2", "Precisión Léxica", "His argument was so _____ that no one could refute it.", "persuasive", "cogent", "believable", "plausible", "cogent", "'Cogent' connota un argumento claro, lógico, fundamentado y prácticamente irrefutable.")
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

def get_quiz_questions(level, limit=10):
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    c.execute("SELECT id, level, category, question, op1, op2, op3, op4, correct, explanation FROM quizzes WHERE level = ?", (level,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        return []
    random.seed(datetime.now().microsecond)
    return random.sample(rows, min(len(rows), limit))

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
# 2. CONFIGURACIÓN Y ESTILOS VISUALES MODERNOS
# =========================================================
st.set_page_config(
    page_title="English Mastery Hub | AI Edition",
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
    .card-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 0.5rem;
    }
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
    .btn-hotmart:hover {
        background: linear-gradient(135deg, #FB923C 0%, #F97316 100%);
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. NAVEGACIÓN LATERAL
# =========================================================
st.sidebar.markdown("### ⚡ **English Mastery**")
st.sidebar.caption("Ruta Integral: A0 ➔ C2")

menu = st.sidebar.radio(
    "Navegación:",
    [
        "⏱️ Focus & Pomodoro (15-20m)",
        "🎬 Hub de Cursos (Hotmart)",
        "🗺️ Ruta de Hitos (A0 a C2)",
        "🗂️ Flashcards Activas",
        "📝 Quizzes & Evaluaciones",
        "🎙️ Speaking & Feedback Lab"
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

# --- 1. POMODORO ---
if menu == "⏱️ Focus & Pomodoro (15-20m)":
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
            "Gringo Academy: Episodio / Telenovela",
            "Activación Neural: Audio e Inmersión Subconsciente",
            "Flashcards: Repaso Espaciado (Niveles A0 - C2)",
            "Quizzes & Evaluaciones de Nivel",
            "Speaking Lab: Práctica Oral con IA"
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

# --- 2. HUB DE CURSOS (HOTMART) ---
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

# --- 3. RUTA DE HITOS (TEMARIO COMPLETO A0 A C2) ---
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

# --- 4. SMART FLASHCARDS ---
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

# --- 5. QUIZZES & EVALUACIONES ---
elif menu == "📝 Quizzes & Evaluaciones":
    st.markdown("## 📝 Centro de Evaluaciones y Tests")
    st.caption("Comprueba tus conocimientos gramaticales y vocabulario por nivel.")
    
    niveles_quiz = ["A0", "A1", "A2", "B1", "B2", "C1", "C2"]
    col1, col2 = st.columns([1.5, 1])
    with col1:
        nivel_q = st.selectbox("Selecciona Nivel a Evaluar:", niveles_quiz, index=0)
    with col2:
        cant_q = st.selectbox("Cantidad de preguntas:", [5, 10], index=0)
        
    if st.button("🚀 Iniciar Ronda de Test", use_container_width=True):
        st.session_state.preguntas_activas = get_quiz_questions(nivel_q, cant_q)
        st.session_state.quiz_evaluado = False
        st.rerun()
        
    if "preguntas_activas" in st.session_state and st.session_state.preguntas_activas:
        with st.form("quiz_form"):
            user_answers = {}
            for i, item in enumerate(st.session_state.preguntas_activas):
                qid, qlvl, qcat, qtext, op1, op2, op3, op4, corr, expl = item
                st.markdown(f"**{i+1}. {qtext}** *(Tema: {qcat})*")
                user_answers[qid] = st.radio(f"P{i+1}", [op1, op2, op3, op4], key=f"ans_{qid}", label_visibility="collapsed", index=None)
            if st.form_submit_button("🏁 Calificar Evaluación"):
                score = sum(1 for item in st.session_state.preguntas_activas if user_answers.get(item[0]) == item[8])
                save_quiz_score(nivel_q, score, len(st.session_state.preguntas_activas))
                st.session_state.quiz_evaluado = True
                st.session_state.ultimo_score = (score, len(st.session_state.preguntas_activas), nivel_q)
                st.rerun()
                
    if st.session_state.get("quiz_evaluado", False):
        p, t, lvl = st.session_state.ultimo_score
        st.markdown(f"""
        <div class="glass-card">
            <span class="tag-badge">RESULTADO DE LA EVALUACIÓN</span>
            <div class="card-title">Nivel {lvl}: {p} de {t} aciertos ({int((p/t)*100)}%)</div>
        </div>
        """, unsafe_allow_html=True)

# --- 6. SPEAKING & FEEDBACK LAB ---
elif menu == "🎙️ Speaking & Feedback Lab":
    st.markdown("## 🎙️ Speaking & Feedback con Inteligencia Artificial")
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
