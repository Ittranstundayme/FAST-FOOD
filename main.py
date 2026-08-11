import json
import os
import sqlite3
from datetime import datetime, timedelta
import streamlit as st
from PIL import Image

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ---------------------------------------------------------
st.set_page_config(
    page_title="FastFood POS Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos visuales neón / dark mode
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    }
    [data-testid="stSidebar"] {
        background-color: #0d1117 !important;
        border-right: 1px solid #1f2937;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(8px);
    }
    h1 {
        background: linear-gradient(90deg, #10b981, #38bdf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }
    h2, h3 { color: #38bdf8 !important; }
    button[kind="primary"] {
        background: linear-gradient(90deg, #059669 0%, #10b981 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: bold !important;
    }
    .badge-preparado {
        background-color: #065f46; color: #34d399;
        padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px;
    }
    .badge-pendiente {
        background-color: #854d0e; color: #fef08a;
        padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

DB_NAME = "restaurante.db"
IMG_DIR = "imagenes"
if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)


# ---------------------------------------------------------
# CONEXIÓN DUAL (Local SQLite / Nube PostgreSQL)
# ---------------------------------------------------------
def get_connection():
    # Si existen secretos configurados para PostgreSQL, se conecta a la nube
    if "postgres" in st.secrets:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(
            st.secrets["postgres"]["url"],
            cursor_factory=psycopg2.extras.DictCursor,
        )
        return conn
    else:
        # Modo Local con SQLite
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                usuario TEXT UNIQUE NOT NULL,
                clave TEXT NOT NULL,
                nombre TEXT NOT NULL,
                rol TEXT NOT NULL
            )
        """
        )

        cursor.execute("SELECT COUNT(*) FROM usuarios")
        res = cursor.fetchone()
        count = res[0] if res else 0

        if count == 0:
            usuarios_base = [
                ("mesero1", "1234", "Carlos Gómez", "mesero"),
                ("cocina1", "1234", "Chef Mario", "cocina"),
                ("caja1", "1234", "Ana Cajera", "caja"),
                ("admin", "admin", "Administrador", "admin"),
            ]
            cursor.executemany(
                "INSERT INTO usuarios (usuario, clave, nombre, rol) VALUES (%s, %s, %s, %s)"
                if "postgres" in st.secrets
                else "INSERT INTO usuarios (usuario, clave, nombre, rol) VALUES (?, ?, ?, ?)",
                usuarios_base,
            )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS productos (
                id SERIAL PRIMARY KEY,
                nombre TEXT NOT NULL,
                precio REAL NOT NULL,
                categoria TEXT DEFAULT 'General',
                icono TEXT DEFAULT '🍔',
                imagen_path TEXT DEFAULT ''
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS pedidos (
                id SERIAL PRIMARY KEY,
                cliente TEXT NOT NULL,
                items TEXT NOT NULL,
                total REAL NOT NULL,
                estado TEXT DEFAULT 'pendiente',
                mesero TEXT DEFAULT 'Sistema',
                fecha_hora TEXT DEFAULT ''
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cajas (
                id SERIAL PRIMARY KEY,
                cajero TEXT NOT NULL,
                monto_apertura REAL NOT NULL,
                monto_cierre REAL DEFAULT 0.0,
                ventas_efectivo REAL DEFAULT 0.0,
                fecha_apertura TEXT NOT NULL,
                fecha_cierre TEXT DEFAULT '',
                estado TEXT DEFAULT 'abierta'
            )
        """
        )
        conn.commit()


init_db()

# ---------------------------------------------------------
# ESTADO DE SESIÓN
# ---------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = None
if "rol_actual" not in st.session_state:
    st.session_state.rol_actual = None
if "carrito" not in st.session_state:
    st.session_state.carrito = []


# ---------------------------------------------------------
# LOGIN / LOGOUT
# ---------------------------------------------------------
def login():
    st.markdown(
        "<h1 style='text-align: center; margin-top: 40px;'>⚡ FastFood POS Pro</h1>",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### 🔐 Inicio de Sesión")
            user = st.text_input("Usuario")
            clave = st.text_input("Contraseña", type="password")
            if st.button(
                "🚀 INGRESAR AL SISTEMA",
                type="primary",
                use_container_width=True,
            ):
                query = (
                    "SELECT id, nombre, rol FROM usuarios WHERE usuario=%s AND clave=%s"
                    if "postgres" in st.secrets
                    else "SELECT id, nombre, rol FROM usuarios WHERE usuario=? AND clave=?"
                )
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(query, (user.strip(), clave.strip()))
                    res = cursor.fetchone()
                    if res:
                        st.session_state.authenticated = True
                        st.session_state.usuario_actual = res["nombre"]
                        st.session_state.rol_actual = res["rol"]
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos.")


if not st.session_state.authenticated:
    login()
    st.stop()

# Sidebar
st.sidebar.markdown("# ⚡ FastFood POS")
st.sidebar.markdown(
    f"""
    <div style="background-color: #1e293b; padding: 12px; border-radius: 8px; border-left: 4px solid #10b981; margin-bottom: 15px;">
        <span style="color: #94a3b8; font-size: 11px;">ROL ACTUAL: <strong>{st.session_state.rol_actual.upper()}</strong></span><br>
        <strong style="color: #f8fafc; font-size: 15px;">👤 {st.session_state.usuario_actual}</strong>
    </div>
""",
    unsafe_allow_html=True,
)

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()


# ---------------------------------------------------------
# VISTA: MESERO
# ---------------------------------------------------------
def vista_mesero():
    st.markdown("<h1>🛒 Módulo de Pedidos</h1>", unsafe_allow_html=True)
    col_menu, col_carrito = st.columns([2.2, 1.2])

    with col_menu:
        st.subheader("🍔 Menú de Productos")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, nombre, precio, icono, imagen_path FROM productos"
            )
            productos = cursor.fetchall()

        cols = st.columns(3)
        for idx, prod in enumerate(productos):
            with cols[idx % 3]:
                with st.container(border=True):
                    if prod["imagen_path"] and os.path.exists(
                        prod["imagen_path"]
                    ):
                        st.image(prod["imagen_path"], use_container_width=True)
                    else:
                        st.markdown(
                            f"<h1 style='text-align: center;'>{prod['icono']}</h1>",
                            unsafe_allow_html=True,
                        )

                    st.markdown(f"**{prod['nombre']}**")
                    st.markdown(
                        f"<h3 style='color: #10b981; margin:0;'>${prod['precio']:.2f}</h3>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "➕ Agregar",
                        key=f"add_{prod['id']}",
                        use_container_width=True,
                    ):
                        st.session_state.carrito.append(
                            {
                                "nombre": prod["nombre"],
                                "precio": prod["precio"],
                            }
                        )
                        st.rerun()

    with col_carrito:
        with st.container(border=True):
            st.subheader("📋 Orden Cliente")
            cliente = st.text_input(
                "Mesa / Cliente", placeholder="Ej: Mesa 3"
            )
            st.markdown("---")
            total = sum(i["precio"] for i in st.session_state.carrito)

            for i, item in enumerate(st.session_state.carrito):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(item["nombre"])
                c2.write(f"${item['precio']:.2f}")
                if c3.button("❌", key=f"del_{i}"):
                    st.session_state.carrito.pop(i)
                    st.rerun()

            st.markdown("---")
            st.markdown(
                f"<h2 style='color: #10b981; text-align: right;'>Total: ${total:.2f}</h2>",
                unsafe_allow_html=True,
            )

            if st.button(
                "🚀 ENVIAR A COCINA Y CAJA",
                type="primary",
                use_container_width=True,
            ):
                if not cliente.strip() or not st.session_state.carrito:
                    st.warning("Completa la mesa y selecciona productos.")
                else:
                    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    items_json = json.dumps(st.session_state.carrito)
                    sql = (
                        "INSERT INTO pedidos (cliente, items, total, mesero, fecha_hora) VALUES (%s, %s, %s, %s, %s)"
                        if "postgres" in st.secrets
                        else "INSERT INTO pedidos (cliente, items, total, mesero, fecha_hora) VALUES (?, ?, ?, ?, ?)"
                    )
                    with get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            sql,
                            (
                                cliente,
                                items_json,
                                total,
                                st.session_state.usuario_actual,
                                fecha_actual,
                            ),
                        )
                        conn.commit()
                    st.session_state.carrito = []
                    st.success("¡Orden Enviada!")
                    st.rerun()


# ---------------------------------------------------------
# VISTA: COCINA (CON FRAGMENT DE AUTO-REFRESCO NATIVO)
# ---------------------------------------------------------
@st.fragment(run_every="3s")
def render_cocina_fragment():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, cliente, items, mesero, fecha_hora FROM pedidos WHERE estado = 'pendiente' ORDER BY id ASC"
        )
        pedidos = cursor.fetchall()

    if not pedidos:
        st.info("Sin comandas pendientes en este momento ☕")
        return

    cols = st.columns(3)
    for idx, p in enumerate(pedidos):
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(
                    f"<h3 style='color: #f97316; margin:0;'>Orden #{p['id']}</h3>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**Cliente/Mesa:** {p['cliente']}")
                st.caption(
                    f"Mesero: {p['mesero']} | 🕒 {p['fecha_hora'][11:16] if p['fecha_hora'] else ''}"
                )
                st.markdown("---")

                items = json.loads(p["items"])
                for it in items:
                    st.markdown(f"• **{it['nombre']}**")

                st.markdown("---")
                if st.button(
                    "✔ MARCAR LISTO",
                    key=f"cocina_{p['id']}",
                    use_container_width=True,
                    type="primary",
                ):
                    sql = (
                        "UPDATE pedidos SET estado = 'preparado' WHERE id = %s"
                        if "postgres" in st.secrets
                        else "UPDATE pedidos SET estado = 'preparado' WHERE id = ?"
                    )
                    with get_connection() as conn_up:
                        cursor_up = conn_up.cursor()
                        cursor_up.execute(sql, (p["id"],))
                        conn_up.commit()
                    st.rerun()


def vista_cocina():
    st.markdown(
        "<h1>🔥 Monitor de Cocina <small style='font-size:14px; color:#10b981;'>(En Vivo 🔴)</small></h1>",
        unsafe_allow_html=True,
    )
    render_cocina_fragment()


# ---------------------------------------------------------
# VISTA: CAJA (CON FRAGMENT DE AUTO-REFRESCO NATIVO)
# ---------------------------------------------------------
@st.fragment(run_every="3s")
def render_caja_fragment():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, cliente, items, total, estado, mesero, fecha_hora FROM pedidos WHERE estado != 'cobrado' AND estado != 'anulado' ORDER BY id ASC"
        )
        pedidos_caja = cursor.fetchall()

    if not pedidos_caja:
        st.info("No hay cobros pendientes.")
        return

    cols = st.columns(3)
    for idx, p in enumerate(pedidos_caja):
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(
                    f"### Orden #{p['id']} - <span style='color:#38bdf8;'>{p['cliente']}</span>",
                    unsafe_allow_html=True,
                )
                if p["estado"] == "preparado":
                    st.markdown(
                        "<span class='badge-preparado'>¡LISTO PARA ENTREGAR!</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<span class='badge-pendiente'>En Cocina...</span>",
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    f"<h2 style='color:#10b981; margin-top:8px;'>${p['total']:.2f}</h2>",
                    unsafe_allow_html=True,
                )

                monto_pagado = st.number_input(
                    "Paga con ($):",
                    value=float(p["total"]),
                    min_value=float(p["total"]),
                    key=f"monto_{p['id']}",
                )

                if st.button(
                    "💵 COBRAR",
                    key=f"cobrar_{p['id']}",
                    use_container_width=True,
                    type="primary",
                ):
                    cambio = monto_pagado - p["total"]
                    sql = (
                        "UPDATE pedidos SET estado = 'cobrado' WHERE id = %s"
                        if "postgres" in st.secrets
                        else "UPDATE pedidos SET estado = 'cobrado' WHERE id = ?"
                    )
                    with get_connection() as conn_pay:
                        c_pay = conn_pay.cursor()
                        c_pay.execute(sql, (p["id"],))
                        conn_pay.commit()
                    st.success(f"Cobrado. Cambio: ${cambio:.2f}")
                    st.rerun()


def vista_caja():
    st.markdown(
        "<h1>💰 Control de Caja <small style='font-size:14px; color:#10b981;'>(En Vivo 🔴)</small></h1>",
        unsafe_allow_html=True,
    )
    render_caja_fragment()


# ---------------------------------------------------------
# VISTA: ADMIN
# ---------------------------------------------------------
def vista_admin():
    st.markdown("<h1>🛡️ Módulo Administrador</h1>", unsafe_allow_html=True)
    tab_reportes, tab_usuarios, tab_menu = st.tabs(
        ["📊 Reportes", "👥 Usuarios", "🍔 Menú"]
    )

    with tab_reportes:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT SUM(total) FROM pedidos WHERE estado='cobrado'"
            )
            res_c = cursor.fetchone()
            cobrado = res_c[0] if res_c and res_c[0] else 0.0

            cursor.execute("SELECT COUNT(*) FROM pedidos")
            res_p = cursor.fetchone()
            total_pedidos = res_p[0] if res_p else 0

        c1, c2 = st.columns(2)
        c1.metric("💵 Total Cobrado", f"${cobrado:.2f}")
        c2.metric("📦 Total Pedidos", f"{total_pedidos}")

    with tab_usuarios:
        st.subheader("👥 Usuarios del Sistema")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, usuario, rol FROM usuarios")
            users = cursor.fetchall()

        for u in users:
            st.write(f"• **{u['nombre']}** (`{u['usuario']}`) - {u['rol'].upper()}")

    with tab_menu:
        st.subheader("➕ Registrar Producto")
        p_nombre = st.text_input("Nombre Producto")
        p_precio = st.number_input("Precio ($)", min_value=0.0)
        if st.button("Guardar Producto", type="primary"):
            if p_nombre and p_precio > 0:
                sql = (
                    "INSERT INTO productos (nombre, precio, categoria, icono) VALUES (%s, %s, 'General', '🍔')"
                    if "postgres" in st.secrets
                    else "INSERT INTO productos (nombre, precio, categoria, icono) VALUES (?, ?, 'General', '🍔')"
                )
                with get_connection() as conn:
                    c = conn.cursor()
                    c.execute(sql, (p_nombre, p_precio))
                    conn.commit()
                st.success("Guardado")
                st.rerun()


# ---------------------------------------------------------
# ENRUTAMIENTO POR ROL
# ---------------------------------------------------------
rol = st.session_state.rol_actual
if rol == "mesero":
    vista_mesero()
elif rol == "cocina":
    vista_cocina()
elif rol == "caja":
    vista_caja()
elif rol == "admin":
    vista_admin()
