import streamlit as st
import sqlite3
import random
import json
import urllib.request
from datetime import datetime

# ==========================================
# 0. TUTOR INTELIGENTE (GEMINI 3.8 FLASH)
# ==========================================
def evaluate_speech_with_ai(prompt_text, user_response):
    api_key = str(st.secrets.get("GEMINI_API_KEY", "")).strip().strip('"').strip("'")
    if not api_key:
        return "⚠️ Configura GEMINI_API_KEY en Secrets para activar la retroalimentación."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
    
    sys_prompt = f"""
    Eres una tutora de inglés empática, amigable y muy clara para una estudiante hispanohablante.
    Reto asignado: "{prompt_text}"
    Respuesta de la estudiante: "{user_response}"

    Evalúa su respuesta y entrega tu análisis con este formato exacto:
    🎯 **Calificación:** [Puntaje de 1 a 10]/10
    🔍 **Corrección Gramatical:** [Explica en español claro los errores cometidos. Si usó 'have' para la edad, explica por qué en inglés se usa el verbo To Be].
    ✨ **Cómo decirlo como nativo:** [Escribe la oración corregida y pulida en inglés para que la repita].
    💡 **Consejo de Oro:** [Un consejo práctico de pronunciación o estructura].
    """
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": sys_prompt}
                ]
            }
        ]
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            candidate = res_json.get("candidates", [{}])[0]
            parts = candidate.get("content", {}).get("parts", [{}])
            return parts[0].get("text", "No se recibió respuesta del modelo.")
    except Exception as e:
        return f"Error al conectar con la IA: {str(e)}"

# ==========================================
# 1. BASE DE DATOS Y ESTRUCTURA DE PROGRESO
# ==========================================
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

def get_quiz_history():
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()
    c.execute("SELECT date, level, score, total, pct FROM quiz_history ORDER BY id DESC LIMIT 5")
    rows = c.fetchall()
    conn.close()
    return rows

init_db()

# ==========================================
# 2. CONFIGURACIÓN Y ESTILOS
# ==========================================
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
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .glass-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }
    .card-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 0.5rem;
    }
    .tag-badge {
        display: inline-block;
        background: rgba(56, 189, 248, 0.15);
        color: #38BDF8;
        border: 1px solid rgba(56, 189, 248, 0.3);
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.8rem;
    }
    .flashcard-display {
        background: linear-gradient(145deg, #1E293B, #0F172A);
        border: 1px solid #334155;
        border-radius: 20px;
        padding: 2.5rem 1.5rem;
        text-align: center;
        margin: 1.5rem 0;
        box-shadow: 0 15px 30px rgba(0,0,0,0.4);
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
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. NAVEGACIÓN LATERAL
# ==========================================
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

# ==========================================
# 4. MÓDULOS DE LA APLICACIÓN
# ==========================================

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
            "Flashcards: Repaso Espaciado y Memorización",
            "Quizzes & Evaluaciones de Nivel",
            "Speaking Lab: Práctica Oral en Voz Alta"
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

elif menu == "🎬 Hub de Cursos (Hotmart)":
    st.markdown("## 🎬 Centro de Mando: Hotmart")
    courses = get_courses()
    for cid, name, unit, total, step, last in courses:
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

elif menu == "🗺️ Ruta de Hitos (A0 a C2)":
    st.markdown("## 🗺️ Mapa de Competencias: Nivel 0 al C2")
    tab1, tab2 = st.tabs(["🟢 Fundamentos (A0 - A1)", "🎯 Titulación (A2 - B1)"])
    with tab1:
        st.info("Objetivo: Interiorizar estructuras automáticas sin traducir mentalmente palabra por palabra.")
    with tab2:
        st.success("Objetivo: Certificación Universitaria y dominio funcional de tiempos pasados y modales.")

elif menu == "🗂️ Flashcards Activas":
    st.markdown("## 🗂️ Smart Flashcards & Retención Activa")
    c_lvl, c_flt = st.columns([2, 2])
    with c_lvl:
        nivel_sel = st.selectbox("Nivel de estudio:", ["A0", "A1", "A2", "B1", "Todos"], index=0)
    with c_flt:
        filtro_vista = st.selectbox("Ver tarjetas:", ["Todas", "Solo Pendientes", "Solo Dominadas"], index=0)
    deck = get_flashcards(nivel_sel, filtro_vista)
    total_nivel = len(get_flashcards(nivel_sel, "Todas"))
    dominadas_nivel = len(get_flashcards(nivel_sel, "Solo Dominadas"))
    pct = int((dominadas_nivel / total_nivel) * 100) if total_nivel > 0 else 0
    st.progress(pct / 100)
    st.caption(f"🏆 Dominadas en {nivel_sel}: **{dominadas_nivel} de {total_nivel}** ({pct}%)")
    if deck:
        if "f_idx" not in st.session_state:
            st.session_state.f_idx = 0
        if "f_flip" not in st.session_state:
            st.session_state.f_flip = False
        card = deck[st.session_state.f_idx % len(deck)]
        card_id, card_lvl, card_cat, card_front, card_back, is_mastered = card
        st.markdown(f"""
        <div class="flashcard-display">
            <h2 style="color: #38BDF8; font-size: 2rem; margin: 0;">{card_front}</h2>
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.f_flip:
            st.success(f"💡 {card_back}")
        b1, b2 = st.columns(2)
        if b1.button("👁️ Revelar", use_container_width=True):
            st.session_state.f_flip = True
            st.rerun()
        if b2.button("➡️ Siguiente", use_container_width=True):
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

elif menu == "📝 Quizzes & Evaluaciones":
    st.markdown("## 📝 Centro de Evaluaciones y Tests")
    col1, col2 = st.columns([1.5, 1])
    with col1:
        nivel_q = st.selectbox("Selecciona Nivel a Evaluar:", ["A0", "A1", "A2", "B1"], index=0)
    with col2:
        cant_q = st.selectbox("Cantidad de preguntas:", [10, 25], index=0)
    if st.button("🚀 Iniciar Ronda", use_container_width=True):
        st.session_state.preguntas_activas = get_quiz_questions(nivel_q, cant_q)
        st.session_state.quiz_evaluado = False
        st.rerun()
    if "preguntas_activas" in st.session_state and st.session_state.preguntas_activas:
        with st.form("quiz_form"):
            user_answers = {}
            for i, item in enumerate(st.session_state.preguntas_activas):
                qid, qlvl, qcat, qtext, op1, op2, op3, op4, corr, expl = item
                st.markdown(f"**{i+1}. {qtext}**")
                user_answers[qid] = st.radio(f"P{i+1}", [op1, op2, op3, op4], key=f"ans_{qid}", label_visibility="collapsed", index=None)
            if st.form_submit_button("🏁 Calificar Ronda"):
                score = sum(1 for item in st.session_state.preguntas_activas if user_answers.get(item[0]) == item[8])
                save_quiz_score(nivel_q, score, len(st.session_state.preguntas_activas))
                st.session_state.quiz_evaluado = True
                st.session_state.ultimo_score = (score, len(st.session_state.preguntas_activas), nivel_q)
                st.rerun()
    if st.session_state.get("quiz_evaluado", False):
        p, t, lvl = st.session_state.ultimo_score
        st.success(f"🏆 Resultado: **{p} de {t}** aciertos en {lvl}.")

# --- 6. SPEAKING & IA FEEDBACK LAB ---
elif menu == "🎙️ Speaking & Feedback Lab":
    st.markdown("## 🎙️ Speaking & Feedback con Inteligencia Artificial")
    st.markdown("Practica tus respuestas orales o escritas y recibe corrección instantánea de un tutor nativo con IA.")

    prompts = [
        "Introduce yourself: your name, where you live, and your age. (A0)",
        "Describe your typical morning routine in 3 sentences. (A0/A1)",
        "What do you enjoy doing on weekends? (A1)",
        "What did you do yesterday afternoon? Mention 2 activities. (A2)",
        "Explain why learning English will help you in your career. (B1)"
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
                with st.spinner("Tu tutora de IA está analizando tu gramática..."):
                    retro = evaluate_speech_with_ai(tema, user_text)
                    st.markdown("""
                    <div class="glass-card">
                        <span class="tag-badge">RETROALIMENTACIÓN PERSONALIZADA</span>
                    """, unsafe_allow_html=True)
                    st.markdown(retro)
                    st.markdown("</div>", unsafe_allow_html=True)
    else:
        audio_grabado = st.audio_input("Presiona para grabar:")
        if audio_grabado:
            st.audio(audio_grabado)
            st.success("¡Audio grabado! Escúchate con atención.")
        speech_text = st.text_area("Borrador de lo que hablaste en voz alta:", placeholder="Escribe aquí lo que dijiste para que la IA lo califique...", height=100)
        if st.button("🤖 Evaluar lo que dije con IA", use_container_width=True):
            if not speech_text.strip():
                st.warning("Escribe el texto de lo que hablaste para que la IA pueda corregirte.")
            else:
                with st.spinner("Tu tutora de IA está evaluando tu respuesta..."):
                    retro = evaluate_speech_with_ai(tema, speech_text)
                    st.markdown("""
                    <div class="glass-card">
                        <span class="tag-badge">ANÁLISIS DE LO HABLADO</span>
                    """, unsafe_allow_html=True)
                    st.markdown(retro)
                    st.markdown("</div>", unsafe_allow_html=True)
