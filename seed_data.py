import sqlite3

def populate_database():
    conn = sqlite3.connect("english_learning.db")
    c = conn.cursor()

    # 1. Crear las tablas si aún no existen
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

    # 2. Limpiar registros de prueba previos
    c.execute("DELETE FROM flashcards")
    c.execute("DELETE FROM quizzes")

    # ==========================================
    # 3. BANCO DE FLASHCARDS POR NIVEL
    # ==========================================
    flashcards_data = [
        # --- NIVEL A0 ---
        ("A0", "Verbo To Be", "I am Lorena.", "Yo soy Lorena."),
        ("A0", "Verbo To Be", "You are very kind.", "Tú eres muy amable."),
        ("A0", "Verbo To Be", "He is my teacher.", "Él es mi maestro."),
        ("A0", "Verbo To Be", "She is a student.", "Ella es una estudiante."),
        ("A0", "Verbo To Be", "It is cold today.", "Hace frío hoy / Está frío hoy."),
        ("A0", "Verbo To Be", "We are ready to start.", "Estamos listos para empezar."),
        ("A0", "Verbo To Be", "They are at home.", "Ellos están en casa."),
        ("A0", "Saludos", "Good morning, have a nice day!", "¡Buenos días, que tengas un buen día!"),
        ("A0", "Saludos", "Good afternoon! How are you?", "¡Buenas tardes! ¿Cómo estás?"),
        ("A0", "Saludos", "Good evening, welcome everyone.", "Buenas noches (al llegar), bienvenidos a todos."),
        ("A0", "Saludos", "Good night, see you tomorrow.", "Buenas noches (al despedirse/dormir), hasta mañana."),
        ("A0", "Preguntas Básicas", "What is your name?", "¿Cómo te llamas? / ¿Cuál es tu nombre?"),
        ("A0", "Preguntas Básicas", "Where are you from?", "¿De dónde eres?"),
        ("A0", "Preguntas Básicas", "How old are you?", "¿Cuántos años tienes?"),
        ("A0", "Frases de Supervivencia", "Excuse me, where is the restroom?", "Disculpe, ¿dónde está el baño?"),
        ("A0", "Frases de Supervivencia", "Can you repeat that, please?", "¿Puedes repetir eso, por favor?"),
        ("A0", "Frases de Supervivencia", "I don't understand.", "No entiendo."),
        ("A0", "Frases de Supervivencia", "How do you say this in English?", "¿Cómo se dice esto en inglés?"),
        ("A0", "Cortesía", "Thank you very much!", "¡Muchas gracias!"),
        ("A0", "Cortesía", "You're welcome.", "De nada."),

        # --- NIVEL A1 ---
        ("A1", "Rutinas Diarias", "I wake up early every morning.", "Me despierto temprano todas las mañanas."),
        ("A1", "Rutinas Diarias", "She drinks black coffee without sugar.", "Ella toma café negro sin azúcar."),
        ("A1", "Rutinas Diarias", "He takes a shower at 7:00 AM.", "Él se baña a las 7:00 AM."),
        ("A1", "Rutinas Diarias", "We eat dinner together as a family.", "Cenamos juntos en familia."),
        ("A1", "Trabajo y Ocupaciones", "What do you do for a living?", "¿A qué te dedicas laboralmente?"),
        ("A1", "Trabajo y Ocupaciones", "I work at a beauty salon.", "Trabajo en un salón de belleza."),
        ("A1", "Trabajo y Ocupaciones", "She manages an online business.", "Ella administra un negocio en línea."),
        ("A1", "Compras y Precios", "How much does this dress cost?", "¿Cuánto cuesta este vestido?"),
        ("A1", "Compras y Precios", "Can I pay by credit card?", "¿Puedo pagar con tarjeta de crédito?"),
        ("A1", "Lugares y Direcciones", "The pharmacy is next to the supermarket.", "La farmacia está junto al supermercado."),
        ("A1", "Lugares y Direcciones", "Turn left at the traffic light.", "Gira a la izquierda en el semáforo."),
        ("A1", "Gustos y Preferencias", "I enjoy listening to music while working.", "Disfruto escuchar música mientras trabajo."),
        ("A1", "Gustos y Preferencias", "He doesn't like waking up early on weekends.", "A él no le gusta despertarse temprano los fines de semana."),

        # --- NIVEL A2 ---
        ("A2", "Past Simple Regular", "I worked late yesterday evening.", "Trabajé hasta tarde ayer por la noche."),
        ("A2", "Past Simple Regular", "She called her mother two hours ago.", "Ella llamó a su mamá hace dos horas."),
        ("A2", "Past Simple Irregular", "I went to the store and bought some groceries.", "Fui a la tienda y compré víveres."),
        ("A2", "Past Simple Irregular", "We saw a great movie last weekend.", "Vimos una gran película el fin de semana pasado."),
        ("A2", "Past Simple Irregular", "He had a meeting with his team this morning.", "Él tuvo una reunión con su equipo esta mañana."),
        ("A2", "Peticiones Amables", "Could you please help me with this task?", "¿Podrías por favor ayudarme con esta tarea?"),
        ("A2", "Peticiones Amables", "Would you like something to drink?", "¿Te gustaría algo de tomar?"),
        ("A2", "Comparativos", "This laptop is faster than my old computer.", "Esta laptop es más rápida que mi computadora anterior."),
        ("A2", "Obligación y Consejo", "You should take a break and rest.", "Deberías tomarte un descanso y reposar."),
        ("A2", "Obligación y Consejo", "I have to finish this project today.", "Tengo que terminar este proyecto hoy."),

        # --- NIVEL B1 ---
        ("B1", "Emails y Trabajo", "I am writing to confirm our appointment.", "Escribo para confirmar nuestra cita."),
        ("B1", "Emails y Trabajo", "I look forward to hearing from you soon.", "Espero con gusto tener noticias suyas pronto."),
        ("B1", "Present Perfect", "I have worked in this industry for several years.", "He trabajado en esta industria durante varios años."),
        ("B1", "Present Perfect", "Have you ever traveled abroad?", "¿Alguna vez has viajado al extranjero?"),
        ("B1", "Expresiones Idiomáticas", "We are running out of time to submit the report.", "Se nos está acabando el tiempo para entregar el informe."),
        ("B1", "Expresiones Idiomáticas", "Let's get straight to the point.", "Vayamos directo al grano.")
    ]

    c.executemany("INSERT INTO flashcards (level, category, front, back) VALUES (?, ?, ?, ?)", flashcards_data)

    # ==========================================
    # 4. BANCO DE REACTIVOS PARA QUIZZES
    # ==========================================
    quizzes_data = [
        # --- NIVEL A0 ---
        ("A0", "Verbo To Be", "I ________ very happy to meet you.", "am", "is", "are", "be", "am", "Con el pronombre 'I' la forma del verbo to be en presente siempre es 'am'."),
        ("A0", "Verbo To Be", "She ________ my business partner.", "are", "is", "am", "be", "is", "Para la tercera persona singular (he, she, it) se usa 'is'."),
        ("A0", "Verbo To Be", "They ________ at the office right now.", "is", "am", "are", "be", "are", "Con sujetos plurales como 'they' se emplea 'are'."),
        ("A0", "Pronombres", "________ is my brother. His name is Carlos.", "She", "He", "They", "We", "He", "'He' es el pronombre masculino en singular."),
        ("A0", "Saludos y Respuestas", "How are you doing today? -> ________________", "I have 30 years.", "I'm doing great, thanks!", "Yes, I do.", "Nice to meet you.", "I'm doing great, thanks!", "'How are you doing?' consulta tu estado de ánimo actual."),
        ("A0", "Artículos", "She bought ________ apple and ________ notebook.", "a / an", "an / a", "a / a", "an / an", "an / a", "Se usa 'an' antes de sonido vocal (apple) y 'a' antes de consonante (notebook)."),
        ("A0", "Preguntas Básicas", "________ is your favorite color?", "Who", "Where", "What", "How", "What", "'What' se utiliza para indagar sobre cosas u opciones abiertas."),
        ("A0", "Preguntas Básicas", "________ are you from? - I am from Mexico.", "When", "Where", "Who", "Why", "Where", "'Where' se emplea para preguntar sobre lugares u origen."),
        ("A0", "Números y Cantidad", "How ________ books do you have on the desk?", "much", "many", "old", "often", "many", "Los sustantivos contables en plural (books) usan 'many'."),
        ("A0", "Cortesía", "Can you help me? -> Sure, ________________.", "you're welcome", "no problem", "excuse me", "see you", "no problem", "'No problem' o 'Sure' son respuestas amables a peticiones de ayuda."),

        # --- NIVEL A1 ---
        ("A1", "Present Simple", "David ________ in a bank every weekday.", "work", "works", "working", "is work", "works", "En Present Simple con 3ra persona (he/she/it) se añade -s/-es al verbo."),
        ("A1", "Auxiliares", "________ your sister like spicy food?", "Do", "Does", "Is", "Are", "Does", "Para formular preguntas en Present Simple con He/She se usa el auxiliar 'Does'."),
        ("A1", "Negación Simple", "I ________ drink coffee late at night.", "doesn't", "don't", "not", "am not", "don't", "Con el sujeto 'I' la negación en presente simple se construye con 'don't'."),
        ("A1", "Preposiciones de Tiempo", "The conference begins ________ Monday ________ 9:00 AM.", "at / on", "in / at", "on / at", "on / in", "on / at", "Días de la semana usan 'on' y las horas exactas usan 'at'."),
        ("A1", "Frecuencia", "She ________ arrives late; she is very punctual.", "always", "often", "never", "sometimes", "never", "'Never' indica frecuencia cero, concordando con ser puntual."),
        ("A1", "Posesivos", "This is Maria and that is ________ new car.", "his", "her", "their", "its", "her", "'Her' es el adjetivo posesivo femenino singular."),
        ("A1", "Habilidad (Can)", "He ________ speak three different languages fluently.", "can", "cans", "is can", "can to", "can", "Los verbos modales como 'can' no llevan -s ni 'to'."),
        ("A1", "Plurales Irregulares", "There are three ________ waiting in the reception area.", "childs", "children", "childrens", "child", "children", "El plural irregular de 'child' es 'children'."),
        ("A1", "Vocabulario Rutina", "I usually ________ my teeth after breakfast.", "wash", "brush", "clean", "comb", "brush", "La colocación correcta en inglés es 'brush one's teeth'."),
        ("A1", "Preposiciones de Lugar", "The keys are ________ the kitchen table.", "in", "on", "at", "under to", "on", "Para superficies horizontales se utiliza la preposición 'on'."),

        # --- NIVEL A2 ---
        ("A2", "Past Simple Regular", "They ________ the client yesterday afternoon.", "contact", "contacted", "contacting", "have contacted", "contacted", "'Yesterday' define un tiempo pasado cerrado; requiere terminación regular -ed."),
        ("A2", "Past Simple Irregular", "Last summer, we ________ to Canada on vacation.", "go", "went", "gone", "goed", "went", "'Went' es la forma irregular en pasado simple de 'go'."),
        ("A2", "Pregunta en Pasado", "Where ________ you go on your last trip?", "did", "do", "were", "have", "did", "El auxiliar para estructurar preguntas en pasado simple es 'did'."),
        ("A2", "Negación en Pasado", "She ________ see the email until this morning.", "didn't", "wasn't", "doesn't", "haven't", "didn't", "Las oraciones negativas en pasado simple emplean 'didn't' seguido del verbo base."),
        ("A2", "Comparativos", "My new mobile phone is ________ than the old one.", "more fast", "faster", "fastest", "as fast", "faster", "Los adjetivos cortos de una sílaba forman el comparativo añadiendo -er."),
        ("A2", "Modales", "Could you ________ me the report when you finish?", "send", "sent", "sending", "to send", "send", "Tras el verbo modal 'could' el verbo principal va en su forma base."),
        ("A2", "Present Continuous", "Listen! The manager ________ to the team right now.", "speaks", "is speaking", "spoke", "has spoken", "is speaking", "Acciones que ocurren en el momento de hablar usan 'is/are + -ing'."),
        ("A2", "Conectores", "She was feeling sick, ________ she stayed home to rest.", "because", "so", "although", "but", "so", "'So' introduce la consecuencia o resultado directo de una situación."),
        ("A2", "Superlativos", "Mount Everest is the ________ mountain on Earth.", "higher", "highest", "most high", "more high", "highest", "El superlativo de adjetivos cortos se construye con 'the + adjetivo-est'."),
        ("A2", "Sugerencias", "You look exhausted. You ________ go to sleep early tonight.", "should", "must to", "can to", "ought", "should", "'Should' se utiliza para dar recomendaciones o sugerencias amables.")
    ]

    c.executemany("""
        INSERT INTO quizzes (level, category, question, op1, op2, op3, op4, correct, explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, quizzes_data)

    conn.commit()
    conn.close()
    print("¡Base de datos poblada exitosamente con el banco de reactivos y tarjetas!")

if __name__ == "__main__":
    populate_database()
