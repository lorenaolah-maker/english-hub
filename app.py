import streamlit as st
import sqlite3
import random
from datetime import datetime
from google import genai

# ==========================================
# 0. CLIENTE DE INTELIGENCIA ARTIFICIAL
# ==========================================
api_key = st.secrets.get("GEMINI_API_KEY", None)
ai_client = genai.Client(api_key=api_key) if api_key else None

def evaluate_speech_with_ai(prompt_text, user_response):
    if not ai_client:
        return "⚠️ No se detectó la clave GEMINI_API_KEY en Secrets. Revisa la configuración."
    try:
        sys_prompt = f"""
        Eres una tutora de inglés paciente, empática y rigurosa para una estudiante hispanohablante.
        Reto asignado: "{prompt_text}"
        Respuesta del estudiante: "{user_response}"

        Analiza su respuesta y responde con este formato claro:
        🎯 **Calificación:** [Puntaje de 1 a 10]/10
        🔍 **Corrección Gramatical:** [Explica en español de forma súper clara los fallos. Si usó 'have' para la edad, aclara que en inglés la edad se es con 'am/is/are'].
        ✨ **Cómo decirlo como nativo:** [Escribe la oración corregida y pulida en inglés].
        💡 **Consejo de Oro:** [Un consejo práctico de vocabulario o pronunciación].
        """
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=sys_prompt
        )
        return response.text
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

# --- 1. FOCUS & POMODORO ---
if menu == "⏱️ Focus & Pomodoro (15-20m)":
    st.markdown("## ⏱️ Sesión de Estudio Focalizado")
    st.markdown("Diseñado para la regla de oro: **15 a 20 minutos de inmersión diaria** sin distracciones.")

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
            st.success(f"¡Sesión de **{tiempo_foco} min** guardada con éxito! Enfoque: {enfoque}.")

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
        else:
            st.caption("Aún no tienes sesiones registradas. ¡Inicia la primera hoy!")

# --- 2. HUB DE CURSOS ---
elif menu == "🎬 Hub de Cursos (Hotmart)":
    st.markdown("## 🎬 Centro de Mando: Hotmart")
    st.markdown("Monitorea tu progreso sincronizado con el método de ambos programas.")

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
            pasos = [
                "Paso 1: Vocabulario en contexto",
                "Paso 2: Gramática esencial",
                "Paso 3: Pronunciación nativa",
                "Paso 4: Examen de Listening",
                "Paso 5: Práctica de Speaking"
            ]
            idx_p = pasos.index(step) if step in pasos else 0
            nuevo_paso = col_b.selectbox("Fase actual:", pasos, index=idx_p, key=f"step_{cid}")
            nueva_unidad = col_c.number_input("Telenovela / Bloque:", min_value=1, max_value=total, value=unit, key=f"unit_{cid}")
        else:
            bloques = [f"Semana {i}" for i in range(1, 13)]
            idx_b = bloques.index(step) if step in bloques else 0
            nuevo_paso = col_b.selectbox("Semana actual:", bloques, index=idx_b, key=f"step_{cid}")
            nueva_unidad = col_c.number_input("Unidad completada:", min_value=1, max_value=12, value=unit, key=f"unit_{cid}")

        c_save, c_link = st.columns([1, 2])
        with c_save:
            if st.button(f"💾 Guardar {cid.capitalize()}", key=f"btn_{cid}", use_container_width=True):
                update_course(cid, nueva_unidad, nuevo_paso)
                st.toast("Progreso actualizado en base de datos")
                st.rerun()
        with c_link:
            st.markdown(f"[🔗 Ir a Hotmart Club](https://consumer.hotmart.com)")
        st.divider()

# --- 3. RUTA POR NIVELES ---
elif menu == "🗺️ Ruta de Hitos (A0 a C2)":
    st.markdown("## 🗺️ Mapa de Competencias: Nivel 0 al C2")
    tab1, tab2, tab3, tab4 = st.tabs(["🟢 Nivel 0 / A1", "🎯 Nivel A2 (Titulación)", "🔵 Niveles B1 / B2", "🟣 Niveles C1 / C2"])
    
    with tab1:
        st.markdown("""
        <div class="glass-card">
            <div class="card-title">Fundamentos y Despegue</div>
            <p style="color:#94A3B8;">El objetivo es interiorizar estructuras automáticas sin traducir mentalmente palabra por palabra.</p>
            <ul>
                <li><b>Gramática Clave:</b> Pronombres personales, Verbo To Be, Present Simple.</li>
                <li><b>Preguntas funcionales:</b> Estructura con <i>Do / Does / Where / What</i>.</li>
                <li><b>Vocabulario:</b> Saludos, profesiones, días, números y compras.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with tab2:
        st.markdown("""
        <div class="glass-card">
            <div class="card-title">Nivel A2: Certificación Universitaria</div>
            <p style="color:#94A3B8;">Competencia requerida para exámenes de titulación.</p>
            <ul>
                <li><b>Pasado Simple:</b> Verbos regulares (-ed) y verbos irregulares frecuentes.</li>
                <li><b>Present Continuous:</b> Acciones en el momento.</li>
                <li><b>Modales:</b> <i>Can / Could / Should</i>.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with tab3:
        st.markdown("""
        <div class="glass-card">
            <div class="card-title">B1 - B2: Fluidez Profesional e Independencia</div>
            <p style="color:#94A3B8;">Capacidad de mantener reuniones y conversaciones fluidas.</p>
        </div>
        """, unsafe_allow_html=True)
    with tab4:
        st.markdown("""
        <div class="glass-card">
            <div class="card-title">C1 - C2: Dominio Bilingüe Nativo</div>
        </div>
        """, unsafe_allow_html=True)

# --- 4. FLASHCARDS CON PROGRESO ---
elif menu == "🗂️ Flashcards Activas":
    st.markdown("## 🗂️ Smart Flashcards & Retención Activa")
    st.caption("Marca las que ya dominas para llevar tu métrica real de aprendizaje.")

    c_lvl, c_flt = st.columns([2, 2])
    with c_lvl:
        nivel_sel = st.selectbox("Nivel de estudio:", ["A0", "A1", "A2", "B1", "Todos"], index=0)
    with c_flt:
        filtro_vista = st.selectbox("Ver tarjetas:", ["Todas", "Solo Pendientes", "Solo Dominadas"], index=0)

    deck = get_flashcards(nivel_sel, filtro_vista)
    total_nivel = len(get_flashcards(nivel_sel, "Todas"))
    dominadas_nivel = len(get_flashcards(nivel_sel, "Solo Dominadas"))
    porcentaje = int((dominadas_nivel / total_nivel) * 100) if total_nivel > 0 else 0

    st.progress(porcentaje / 100)
    st.caption(f"🏆 Dominadas en {nivel_sel}: **{dominadas_nivel} de {total_nivel}** ({porcentaje}%)")

    if not deck:
        st.info("No hay tarjetas con ese filtro actualmente.")
    else:
        if "f_idx" not in st.session_state:
            st.session_state.f_idx = 0
        if "f_flip" not in st.session_state:
            st.session_state.f_flip = False

        card = deck[st.session_state.f_idx % len(deck)]
        card_id, card_lvl, card_cat, card_front, card_back, is_mastered = card

        estado_txt = "✅ DOMINADA" if is_mastered == 1 else "⏳ EN APRENDIZAJE"
        st.markdown(f"<span class='tag-badge'>{card_lvl} • {card_cat}</span> • <small style='color:#94A3B8;'>{estado_txt} (Tarjeta {st.session_state.f_idx % len(deck) + 1} de {len(deck)})</small>", unsafe_allow_html=True)

        st.markdown(f"""
        <div class="flashcard-display">
            <h2 style="color: #38BDF8; font-size: 2rem; margin: 0;">{card_front}</h2>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.f_flip:
            st.markdown(f"""
            <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10B981; border-radius: 12px; padding: 1.2rem; text-align: center; margin-bottom: 1rem;">
                <h3 style="color: #34D399; margin: 0;">💡 {card_back}</h3>
            </div>
            """, unsafe_allow_html=True)

        b_voltear, b_sig = st.columns([1, 1])
        with b_voltear:
            if st.button("👁️ Voltear / Revelar", use_container_width=True):
                st.session_state.f_flip = True
                st.rerun()
        with b_sig:
            if st.button("➡️ Siguiente Tarjeta", use_container_width=True):
                st.session_state.f_idx += 1
                st.session_state.f_flip = False
                st.rerun()

        st.markdown("#### ¿Cómo te fue con esta frase?")
        c_fail, c_pass = st.columns(2)
        with c_fail:
            if st.button("❌ Aún me cuesta", use_container_width=True):
                update_card_mastery(card_id, 0)
                st.session_state.f_idx += 1
                st.session_state.f_flip = False
                st.toast("Marcada para seguir repasando")
                st.rerun()
        with c_pass:
            if st.button("✅ ¡Ya me la sé!", use_container_width=True):
                update_card_mastery(card_id, 1)
                st.session_state.f_idx += 1
                st.session_state.f_flip = False
                st.toast("¡Excelente! Sumada a tus tarjetas dominadas 🎉")
                st.rerun()

# --- 5. QUIZZES CON EVALUACIÓN ---
elif menu == "📝 Quizzes & Evaluaciones":
    st.markdown("## 📝 Centro de Evaluaciones y Tests")
    st.caption("Ponte a prueba con rondas de preguntas dinámicas y guarda tu puntuación.")

    col1, col2 = st.columns([1.5, 1])
    with col1:
        nivel_q = st.selectbox("Selecciona Nivel a Evaluar:", ["A0", "A1", "A2", "B1"], index=0)
    with col2:
        cant_q = st.selectbox("Cantidad de preguntas:", [10, 25, 50], index=0)

    if st.button("🚀 Iniciar Nueva Ronda de Preguntas", use_container_width=True):
        st.session_state.preguntas_activas = get_quiz_questions(nivel_q, cant_q)
        st.session_state.quiz_evaluado = False
        st.session_state.quiz_respuestas = {}
        st.rerun()

    if "preguntas_activas" in st.session_state and st.session_state.preguntas_activas:
        preguntas = st.session_state.preguntas_activas
        st.info(f"Mostrando **{len(preguntas)} preguntas** de nivel **{nivel_q}**.")

        with st.form("quiz_form"):
            user_answers = {}
            for i, item in enumerate(preguntas):
                qid, qlvl, qcat, qtext, op1, op2, op3, op4, corr, expl = item
                st.markdown(f"**{i+1}. {qtext}** `<span style='color:#38BDF8;'>[{qcat}]</span>`", unsafe_allow_html=True)
                user_answers[qid] = st.radio(
                    f"Pregunta {i+1}",
                    [op1, op2, op3, op4],
                    key=f"user_ans_{qid}",
                    label_visibility="collapsed",
                    index=None
                )
                st.divider()

            submitted = st.form_submit_button("🏁 Terminar y Calificar Ronda")
            if submitted:
                puntaje = 0
                for item in preguntas:
                    qid, _, _, _, _, _, _, _, corr, _ = item
                    if user_answers.get(qid) == corr:
                        puntaje += 1
                save_quiz_score(nivel_q, puntaje, len(preguntas))
                st.session_state.quiz_evaluado = True
                st.session_state.ultimo_score = (puntaje, len(preguntas), nivel_q)
                st.rerun()

    if st.session_state.get("quiz_evaluado", False):
        p, t, lvl = st.session_state.ultimo_score
        pct = int((p / t) * 100) if t > 0 else 0
        if pct >= 80:
            st.success(f"🎉 ¡Felicidades! Calificación: **{p} de {t}** ({pct}%). ¡Dominas muy bien {lvl}!")
        else:
            st.warning(f"✍️ Calificación: **{p} de {t}** ({pct}%). Continúa practicando con las Flashcards.")

    st.markdown("### 📊 Historial de Exámenes Guardados")
    historial = get_quiz_history()
    if historial:
        for h_date, h_lvl, h_score, h_total, h_pct in historial:
            st.markdown(f"• **{h_lvl}** — **{h_score}/{h_total}** ({h_pct}%) <small style='color:#64748B;'>[{h_date}]</small>", unsafe_allow_html=True)
    else:
        st.caption("Aún no has completado evaluaciones. Inicia una arriba.")

# --- 6. SPEAKING & RETROALIMENTACIÓN CON IA ---
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
        st.markdown("**Escribe tu respuesta en inglés:**")
        user_text = st.text_area("Tu respuesta:", placeholder="I am Lorena and I am 38 years old...", height=120)

        if st.button("🤖 Analizar y Corregir con IA", use_container_width=True):
            if not user_text.strip():
                st.warning("Escribe al menos una frase en inglés antes de analizar.")
            else:
                with st.spinner("Tu tutor de IA está evaluando tu gramática y estilo..."):
                    retro = evaluate_speech_with_ai(tema, user_text)
                    st.markdown("""
                    <div class="glass-card">
                        <span class="tag-badge">RETROALIMENTACIÓN PERSONALIZADA</span>
                    """, unsafe_allow_html=True)
                    st.markdown(retro)
                    st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.markdown("**Grábate respondiendo en voz alta:**")
        audio_grabado = st.audio_input("Presiona para grabar:")
        if audio_grabado:
            st.audio(audio_grabado)
            st.success("¡Audio grabado! Escúchate para notar tu entonación.")
        
        st.markdown("**Escribe lo que dijiste para que la IA lo califique:**")
        speech_text = st.text_area("Borrador de lo que hablaste:", placeholder="I said: First I wake up early...", height=100)
        if st.button("🤖 Evaluar lo que dije con IA", use_container_width=True):
            if not speech_text.strip():
                st.warning("Escribe el texto de tu audio para que la IA pueda corregirte.")
            else:
                with st.spinner("Evaluando fluidez y vocabulario..."):
                    retro = evaluate_speech_with_ai(tema, speech_text)
                    st.markdown("""
                    <div class="glass-card">
                        <span class="tag-badge">ANÁLISIS DE LO HABLADO</span>
                    """, unsafe_allow_html=True)
                    st.markdown(retro)
                    st.markdown("</div>", unsafe_allow_html=True)
