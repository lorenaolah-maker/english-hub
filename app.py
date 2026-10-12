import streamlit as st
import sqlite3
import os
import base64
from datetime import datetime

# ==========================================
# 1. BASE DE DATOS LOCAL
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
# 2. CONFIGURACIÓN Y ESTILOS
# ==========================================
st.set_page_config(
    page_title="English Mastery Hub | Lorena Álvarez",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<head><meta name="google" content="notranslate"></head>
<style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .glass-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
    }
    .card-title { font-size: 1.25rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.5rem; }
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
    }
    .profile-container {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 0 16px 0;
        border-bottom: 1px solid rgba(148, 163, 184, 0.15);
        margin-bottom: 15px;
    }
    .profile-img {
        width: 58px;
        height: 58px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid #38BDF8;
        box-shadow: 0 4px 10px rgba(56, 189, 248, 0.25);
    }
    .profile-info {
        display: flex;
        flex-direction: column;
    }
    .profile-name {
        font-size: 1.05rem;
        font-weight: 700;
        color: #F8FAFC;
        margin: 0;
    }
    .profile-badge {
        font-size: 0.78rem;
        color: #38BDF8;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 4px;
        margin-top: 3px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. BARRA LATERAL (FOTO DE LORENA + GOODNOTES)
# ==========================================

# Carga y codificación de imagen en Base64 para que cargue en cualquier navegador
foto_path = "lorena.jpg"
if os.path.exists(foto_path):
    with open(foto_path, "rb") as f:
        img_bytes = f.read()
    img_b64 = base64.b64encode(img_bytes).decode()
    img_src = f"data:image/jpeg;base64,{img_b64}"
else:
    img_src = "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=250&auto=format&fit=crop"

st.sidebar.markdown(f"""
<div class="profile-container">
    <img src="{img_src}" class="profile-img">
    <div class="profile-info">
        <h4 class="profile-name">Lorena Álvarez</h4>
        <span class="profile-badge">🇬🇧 English Mastery ⚡</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### ⚡ **English Mastery**")
st.sidebar.caption("Ruta Integral: A0 ➔ C2")

menu = st.sidebar.radio(
    "Navegación:",
    [
        "⏱️ Focus & Pomodoro (15-20m)",
        "🎬 Hub de Cursos (Hotmart)",
        "🗺️ Ruta de Hitos (A0 a C2)",
        "🗂️ Flashcards Activas",
        "📝 Quizzes & Mini-Tests A2",
        "🎙️ Speaking Lab"
    ]
)

st.sidebar.divider()
st.sidebar.markdown("### 📝 Libreta Digital")
st.sidebar.markdown(
    """<a href="goodnotes://" target="_blank" style="text-decoration: none;">
        <button style="width: 100%; background: #0284C7; color: white; border: none; padding: 12px; border-radius: 10px; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px;">
            📖 Abrir Goodnotes
        </button>
    </a>""",
    unsafe_allow_html=True
)

# ==========================================
# 4. CONTENIDO PERSONALIZADO
# ==========================================
if menu == "⏱️ Focus & Pomodoro (15-20m)":
    st.markdown("## ⏱️ Sesión de Estudio Focalizado")
    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown('<div class="glass-card"><span class="tag-badge">TEMPORIZADOR</span><div class="card-title">Configurar Bloque Diario</div></div>', unsafe_allow_html=True)
        tiempo_foco = st.select_slider("Minutos:", options=[5, 10, 15, 20, 25, 30], value=15)
        enfoque = st.selectbox("Área de hoy:", [
            "Gringo Academy: Episodio / Telenovela",
            "Activación Neural: Audio e Inmersión",
            "Flashcards: Repaso Espaciado",
            "Mini-Quiz Gramatical A2",
            "Speaking Lab: Práctica en voz alta"
        ])
        if st.button("🔥 Iniciar y Registrar Sesión", use_container_width=True):
            log_session(tiempo_foco, enfoque)
            st.success(f"¡Excelente Lorena! Sesión de {tiempo_foco} min guardada con éxito.")
    with c2:
        st.markdown('<div class="glass-card"><span class="tag-badge">HISTORIAL</span><div class="card-title">Tus últimas sesiones</div></div>', unsafe_allow_html=True)
        sesiones = get_recent_sessions()
        if sesiones:
            for s_date, s_min, s_focus in sesiones:
                st.markdown(f"• **{s_min} min** — {s_focus} <span style='color:#64748B; font-size:0.8rem;'>({s_date})</span>", unsafe_allow_html=True)
        else:
            st.caption("Sin sesiones registradas aún. ¡Iniciemos hoy Lorena!")

elif menu == "🎬 Hub de Cursos (Hotmart)":
    st.markdown("## 🎬 Centro de Mando: Hotmart")
    courses = get_courses()
    for cid, name, unit, total, step, last in courses:
        st.markdown(f'<div class="glass-card"><span class="tag-badge">CURSO</span><div class="card-title">{name}</div></div>', unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns([2, 1.2, 1])
        pct = int((unit / total) * 100) if total > 0 else 0
        col_a.progress(pct / 100)
        col_a.caption(f"Avance de Lorena: **{unit} de {total}** ({pct}%) | Última vez: {last}")
        if cid == "gringo":
            pasos = ["Paso 1: Vocabulario en contexto", "Paso 2: Gramática esencial", "Paso 3: Pronunciación nativa", "Paso 4: Examen de Listening", "Paso 5: Práctica de Speaking"]
            idx_p = pasos.index(step) if step in pasos else 0
            nuevo_paso = col_b.selectbox("Fase actual:", pasos, index=idx_p, key=f"step_{cid}")
            nueva_unidad = col_c.number_input("Telenovela / Bloque:", min_value=1, max_value=total, value=unit, key=f"unit_{cid}")
        else:
            bloques = [f"Semana {i}" for i in range(1, 13)]
            idx_b = bloques.index(step) if step in bloques else 0
            nuevo_paso = col_b.selectbox("Semana actual:", bloques, index=idx_b, key=f"step_{cid}")
            nueva_unidad = col_c.number_input("Unidad:", min_value=1, max_value=12, value=unit, key=f"unit_{cid}")
        c_save, c_link = st.columns([1, 2])
        with c_save:
            if st.button(f"💾 Guardar {cid.capitalize()}", key=f"btn_{cid}", use_container_width=True):
                update_course(cid, nueva_unidad, nuevo_paso)
                st.toast("Progreso guardado")
                st.rerun()
        with c_link:
            st.markdown("[🔗 Ir a Hotmart](https://consumer.hotmart.com)")
        st.divider()

elif menu == "🗺️ Ruta de Hitos (A0 a C2)":
    st.markdown("## 🗺️ Mapa de Competencias")
    t1, t2, t3, t4 = st.tabs(["🟢 A0 / A1", "🎯 A2 (Meta Certificación)", "🔵 B1 / B2", "🟣 C1 / C2"])
    with t1:
        st.markdown('<div class="glass-card"><div class="card-title">A0 / A1: Fundamentos</div><p>Pronombres, Verbo To Be, Present Simple y rutinas diarias.</p></div>', unsafe_allow_html=True)
    with t2:
        st.markdown('<div class="glass-card"><div class="card-title">A2: Titulación Universitaria</div><p>Past Simple, Present Continuous, Can/Could, Comparativos.</p></div>', unsafe_allow_html=True)
    with t3:
        st.markdown('<div class="glass-card"><div class="card-title">B1 / B2: Fluidez Profesional</div><p>Present Perfect, Phrasal Verbs y Condicionales.</p></div>', unsafe_allow_html=True)
    with t4:
        st.markdown('<div class="glass-card"><div class="card-title">C1 / C2: Dominio Bilingüe</div><p>Matices idiomáticos y vocabulario técnico avanzado.</p></div>', unsafe_allow_html=True)

elif menu == "🗂️ Flashcards Activas":
    st.markdown("## 🗂️ Smart Flashcards")
    deck = [
        {"front": "I'm looking forward to meeting you.", "back": "Espero con muchas ganas conocerte.", "cat": "Negocios"},
        {"front": "Could you please give me a hand?", "back": "¿Podrías echarme una mano?", "cat": "Cotidiano"},
        {"front": "She scheduled an appointment yesterday.", "back": "Ella agendó una cita ayer.", "cat": "A2 - Past Simple"},
        {"front": "How long does it take?", "back": "¿Cuánto tiempo tarda?", "cat": "Preguntas"},
        {"front": "I'm running out of time.", "back": "Se me acaba el tiempo.", "cat": "Expresión"}
    ]
    if "flash_idx" not in st.session_state: st.session_state.flash_idx = 0
    if "flash_flip" not in st.session_state: st.session_state.flash_flip = False
    cur = deck[st.session_state.flash_idx % len(deck)]
    st.markdown(f"<span class='tag-badge'>{cur['cat']}</span>", unsafe_allow_html=True)
    st.markdown(f'<div class="flashcard-display"><h2 style="color:#38BDF8; margin:0;">{cur["front"]}</h2></div>', unsafe_allow_html=True)
    if st.session_state.flash_flip:
        st.markdown(f'<div style="background:rgba(16,185,129,0.15); border:1px solid #10B981; border-radius:12px; padding:1.2rem; text-align:center; margin-bottom:1rem;"><h3 style="color:#34D399; margin:0;">💡 {cur["back"]}</h3></div>', unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1:
        if st.button("👁️ Revelar", use_container_width=True):
            st.session_state.flash_flip = True
            st.rerun()
    with b2:
        if st.button("➡️ Siguiente", use_container_width=True):
            st.session_state.flash_idx += 1
            st.session_state.flash_flip = False
            st.rerun()

elif menu == "📝 Quizzes & Mini-Tests A2":
    st.markdown("## 📝 Evaluaciones Rápidas")
    st.markdown("#### 1. Past Simple")
    q1 = st.radio("Last night, they ________ home very late.", ["arrive", "arrived", "arriving"], index=None, key="q1")
    if st.button("Verificar #1"):
        if q1 == "arrived": st.success("¡Correcto Lorena! ✅ Acción concluida en el pasado.")
        elif q1 is not None: st.error("Incorrecto ❌ Pasado simple: arrived.")

elif menu == "🎙️ Speaking Lab":
    st.markdown("## 🎙️ Speaking Lab")
    tema = st.selectbox("Reto de hoy:", [
        "Describe your typical morning routine in 3 sentences.",
        "What did you do last weekend?",
        "Explain why learning English will help you in your career."
    ])
    st.info(f"🗣️ **Prompt:** \"{tema}\"")
    txt = st.text_area("Tu respuesta:", placeholder="In the morning...")
    if st.button("Guardar Borrador", use_container_width=True):
        if txt.strip(): st.success("¡Listo Lorena! Cópialo y compártelo para revisarlo.")
        else: st.warning("Escribe algo primero.")
