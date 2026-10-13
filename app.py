import streamlit as st
import sqlite3
from datetime import datetime

# ==========================================
# 1. BASE DE DATOS LOCAL Y PERSISTENCIA
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

init_db()

# ==========================================
# 2. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================
st.set_page_config(
    page_title="English Mastery Hub | Dark Edition",
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
# 3. NAVEGACIÓN LATERAL + GOODNOTES
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
        "📝 Quizzes & Mini-Tests",
        "🎙️ Speaking Lab"
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
            "Flashcards: Repaso Espaciado",
            "Mini-Quiz Gramatical",
            "Speaking Lab: Práctica en voz alta"
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
                <li><b>Gramática Clave:</b> Pronombres personales, Verbo To Be, Present Simple (regla de tercera persona con -s/-es).</li>
                <li><b>Preguntas funcionales:</b> Estructura con <i>Do / Does / Where / What</i>.</li>
                <li><b>Vocabulario funcional:</b> Saludos formales/informales, profesiones, días, meses y números.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        st.markdown("""
        <div class="glass-card">
            <div class="card-title">Nivel A2: Certificación Universitaria</div>
            <p style="color:#94A3B8;">Competencia requerida para aprobar Cambridge KET, Trinity o equivalentes universitarios.</p>
            <ul>
                <li><b>Pasado Simple:</b> Verbos regulares (-ed) y lista de los 30 verbos irregulares más frecuentes (went, saw, had, bought).</li>
                <li><b>Present Continuous vs. Simple:</b> Distinguir rutinas de lo que ocurre en este momento.</li>
                <li><b>Modales de supervivencia:</b> <i>Can / Could</i> (peticiones amables), <i>Must / Should</i> (deber y sugerencias).</li>
                <li><b>Comparativos:</b> Describir diferencias entre lugares, objetos y situaciones.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with tab3:
        st.markdown("""
        <div class="glass-card">
            <div class="card-title">B1 - B2: Fluidez Profesional e Independencia</div>
            <p style="color:#94A3B8;">Capacidad de mantener reuniones, negociaciones y conversaciones complejas.</p>
            <ul>
                <li><b>Present Perfect:</b> Experiencias y acciones que conectan pasado y presente (<i>I have worked...</i>).</li>
                <li><b>Phrasal Verbs:</b> Verbos compuestos habituales del inglés hablado y negocios.</li>
                <li><b>Condicionales (1st & 2nd):</b> Plantear hipótesis y escenarios futuros.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with tab4:
        st.markdown("""
        <div class="glass-card">
            <div class="card-title">C1 - C2: Dominio Bilingüe Nativo</div>
            <p style="color:#94A3B8;">Comprensión instantánea de sutilezas culturales, jerga, humor y redacción técnica.</p>
        </div>
        """, unsafe_allow_html=True)

# --- 4. FLASHCARDS ACTIVAS CON FILTRO POR NIVEL ---
elif menu == "🗂️ Flashcards Activas":
    st.markdown("## 🗂️ Smart Flashcards")
    st.caption("Filtra por tu nivel y practica antes de voltear la tarjeta:")

    mazos_nivel = {
        "A0 - Principiante Absoluto": [
            {"front": "I am / You are / He is", "back": "Yo soy-estoy / Tú eres-estás / Él es-está", "category": "A0 - Verbo To Be"},
            {"front": "Good morning! Nice to meet you.", "back": "¡Buenos días! Mucho gusto en conocerte.", "category": "A0 - Saludos"},
            {"front": "Where are you from?", "back": "¿De dónde eres?", "category": "A0 - Preguntas Básicas"},
            {"front": "I don't understand, can you repeat?", "back": "No entiendo, ¿puedes repetir?", "category": "A0 - Frases Clave"},
            {"front": "This is my notebook and my pen.", "back": "Este es mi cuaderno y mi pluma.", "category": "A0 - Objetos Cotidianos"}
        ],
        "A1 - Básico": [
            {"front": "What do you do for a living?", "back": "¿A qué te dedicas / De qué trabajas?", "category": "A1 - Profesiones"},
            {"front": "She works from Monday to Friday.", "back": "Ella trabaja de lunes a viernes.", "category": "A1 - Rutinas"},
            {"front": "How much does it cost?", "back": "¿Cuánto cuesta?", "category": "A1 - Compras"},
            {"front": "I like listening to podcasts.", "back": "Me gusta escuchar podcasts.", "category": "A1 - Gustos"}
        ],
        "A2 - Pre-intermedio": [
            {"front": "She scheduled an appointment yesterday.", "back": "Ella agendó una cita ayer.", "category": "A2 - Past Simple"},
            {"front": "Could you please give me a hand?", "back": "¿Podrías echarme una mano, por favor?", "category": "A2 - Peticiones"},
            {"front": "How long does it take?", "back": "¿Cuánto tiempo toma / tarda?", "category": "A2 - Preguntas de Viaje"},
            {"front": "I used to wake up early every day.", "back": "Solía despertarme temprano todos los días.", "category": "A2 - Hábitos Pasados"}
        ],
        "B1 - Intermedio / Conversación": [
            {"front": "I'm looking forward to meeting you.", "back": "Tengo muchas ganas / Espero con gusto conocerte.", "category": "B1 - Emails & Negocios"},
            {"front": "I'm running out of time.", "back": "Se me está agotando el tiempo.", "category": "B1 - Expresión Coloquial"},
            {"front": "Never mind, it doesn't matter.", "back": "No te preocupes / Olvídalo, no tiene importancia.", "category": "B1 - Cotidiano"}
        ]
    }

    col_lvl, _ = st.columns([2, 1])
    with col_lvl:
        nivel_escogido = st.selectbox(
            "Selecciona tu nivel de estudio:",
            ["A0 - Principiante Absoluto", "A1 - Básico", "A2 - Pre-intermedio", "B1 - Intermedio / Conversación", "Todos los niveles"],
            index=0
        )

    if nivel_escogido == "Todos los niveles":
        deck = [c for items in mazos_nivel.values() for c in items]
    else:
        deck = mazos_nivel.get(nivel_escogido, [])

    if "flash_idx" not in st.session_state:
        st.session_state.flash_idx = 0
    if "flash_flip" not in st.session_state:
        st.session_state.flash_flip = False

    current = deck[st.session_state.flash_idx % len(deck)]

    st.markdown(f"<span class='tag-badge'>{current['category']}</span> • Tarjeta {st.session_state.flash_idx % len(deck) + 1} de {len(deck)}", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="flashcard-display">
        <h2 style="color: #38BDF8; font-size: 2rem; margin: 0;">{current['front']}</h2>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.flash_flip:
        st.markdown(f"""
        <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10B981; border-radius: 12px; padding: 1.2rem; text-align: center; margin-bottom: 1rem;">
            <h3 style="color: #34D399; margin: 0;">💡 {current['back']}</h3>
        </div>
        """, unsafe_allow_html=True)

    b1, b2 = st.columns(2)
    with b1:
        if st.button("👁️ Voltear / Revelar", use_container_width=True):
            st.session_state.flash_flip = True
            st.rerun()
    with b2:
        if st.button("➡️ Siguiente Tarjeta", use_container_width=True):
            st.session_state.flash_idx += 1
            st.session_state.flash_flip = False
            st.rerun()

# --- 5. QUIZZES CON FILTRO POR NIVEL ---
elif menu == "📝 Quizzes & Mini-Tests":
    st.markdown("## 📝 Evaluaciones Rápidas con Feedback")
    st.caption("Ponte a prueba con ejercicios adaptados a tu nivel:")

    col_q, _ = st.columns([2, 1])
    with col_q:
        nivel_quiz = st.selectbox(
            "Selecciona el nivel del Quiz:",
            ["A0 - Fundamentos Iniciales", "A1 - Presente y Rutinas", "A2 - Pasado Simple y Preposiciones"],
            index=0
        )

    st.divider()

    if nivel_quiz == "A0 - Fundamentos Iniciales":
        st.markdown("#### 1. Verbo To Be (Pronombres Básicos)")
        q1 = st.radio("Hello! My name is Lorena and I ________ a student.", ["is", "am", "are", "be"], index=None, key="q_a0_1")
        if st.button("Verificar #1", key="btn_a0_1"):
            if q1 == "am":
                st.success("¡Excelente! ✅ Con el pronombre **I** siempre usamos **am** (*I am*).")
            elif q1 is not None:
                st.error("Incorrecto ❌ Recuerda: I am, You are, He is, She is.")

        st.divider()

        st.markdown("#### 2. Saludos y Respuestas Clave")
        q2 = st.radio("How are you today? ➔ ________________", ["I have 25 years.", "Nice to meet you.", "I'm doing well, thank you!", "I live in Mexico."], index=None, key="q_a0_2")
        if st.button("Verificar #2", key="btn_a0_2"):
            if q2 == "I'm doing well, thank you!":
                st.success("¡Exacto! ✅ 'How are you?' pregunta cómo estás. La respuesta natural es 'I'm doing well'.")
            elif q2 is not None:
                st.error("Incorrecto ❌ 'How are you?' es para estado de ánimo o bienestar.")

    elif nivel_quiz == "A1 - Presente y Rutinas":
        st.markdown("#### 1. Regla de Tercera Persona (-s / -es)")
        q1 = st.radio("She ________ in an office from Monday to Friday.", ["work", "works", "working", "is work"], index=None, key="q_a1_1")
        if st.button("Verificar #1", key="btn_a1_1"):
            if q1 == "works":
                st.success("¡Correcto! ✅ En Present Simple con He/She/It agregamos **-s** al verbo.")
            elif q1 is not None:
                st.error("Incorrecto ❌ Para 'She' la forma correcta es **works**.")

        st.divider()

        st.markdown("#### 2. Preguntas con Auxiliar")
        q2 = st.radio("________ you speak English?", ["Are", "Do", "Is", "Does"], index=None, key="q_a1_2")
        if st.button("Verificar #2", key="btn_a1_2"):
            if q2 == "Do":
                st.success("¡Muy bien! ✅ Con verbos de acción y 'you' usamos el auxiliar **Do**.")
            elif q2 is not None:
                st.error("Incorrecto ❌ La pregunta usa el auxiliar **Do**: *Do you speak...?*")

    elif nivel_quiz == "A2 - Pasado Simple y Preposiciones":
        st.markdown("#### 1. Tiempo Verbal (Past Simple)")
        q1 = st.radio("Last night, they ________ home very late after the meeting.", ["arrive", "arrived", "arriving", "have arrived"], index=None, key="q_a2_1")
        if st.button("Verificar #1", key="btn_a2_1"):
            if q1 == "arrived":
                st.success("¡Correcto! ✅ 'Last night' indica pasado puntual cerrado. Verbo regular con terminación -ed.")
            elif q1 is not None:
                st.error("Incorrecto ❌ 'Last night' exige Past Simple: **arrived**.")

        st.divider()

        st.markdown("#### 2. Preposiciones de Tiempo")
        q2 = st.radio("The webinar is scheduled ________ 10:00 AM ________ Friday.", ["in / on", "at / on", "on / at", "at / in"], index=None, key="q_a2_2")
        if st.button("Verificar #2", key="btn_a2_2"):
            if q2 == "at / on":
                st.success("¡Exacto! ✅ Horas exactas usan **at** (*at 10:00 AM*) y días de la semana usan **on** (*on Friday*).")
            elif q2 is not None:
                st.error("Incorrecto ❌ Regla básica: **AT** para la hora, **ON** para el día.")

# --- 6. SPEAKING LAB (CON MICRÓFONO + TEXTO) ---
elif menu == "🎙️ Speaking Lab":
    st.markdown("## 🎙️ Speaking & Writing Lab")
    st.markdown("Entrena tu fluidez en inglés grabando tu voz o redactando tu respuesta diaria.")

    prompts = [
        "Describe your typical morning routine in 3 sentences. (A0/A1)",
        "Introduce yourself: your name, where you live and what you do. (A0)",
        "What did you do last weekend? Mention 2 activities. (A2)",
        "Explain why learning English will help your career. (B1)"
    ]
    tema = st.selectbox("Elige tu reto de hoy:", prompts)

    st.info(f"🗣️ **Prompt de práctica:** \"{tema}\"")

    modo_practica = st.radio(
        "¿Cómo quieres responder el reto de hoy?",
        ["🎙️ Hablado (Grabar audio con micrófono)", "✍️ Escrito (Borrador de texto)"],
        horizontal=True
    )

    if modo_practica == "🎙️ Hablado (Grabar audio con micrófono)":
        st.markdown("""
        **Instrucciones de Voz:**
        1. Presiona el botón del micrófono abajo y habla en voz alta en inglés.
        2. Al terminar, vuelve a presionarlo para detener la grabación.
        3. Dale Play para escuchar tu entonación y pronunciación.
        """)

        audio_grabado = st.audio_input("Grábate hablando en inglés:")

        if audio_grabado:
            st.audio(audio_grabado)
            st.success("¡Excelente! Tu audio quedó grabado. Escúchate con atención.")
            st.info("💡 **Guía de autoevaluación:** ¿Pronunciaste las palabras completas? ¿Se entendió tu mensaje sin pausas muy largas?")

    else:
        st.markdown("""
        **Instrucciones de Escritura:**
        1. Escribe tu respuesta en inglés directamente en el recuadro.
        2. Puedes copiarlo para revisar gramática y vocabulario.
        """)

        speech_text = st.text_area("Pega o escribe tu respuesta en inglés:", placeholder="Hi, my name is Lorena and I live in...")
        if st.button("Guardar Borrador", use_container_width=True):
            if speech_text.strip():
                st.success("¡Texto registrado con éxito! Excelente hábito de escritura diaria.")
            else:
                st.warning("Escribe al menos una oración antes de guardar.")
