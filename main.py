import json
import os
import sqlite3
from datetime import datetime, timedelta
import streamlit as st
from PIL import Image

# ---------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="FastFood POS Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_NAME = "restaurante.db"
IMG_DIR = "imagenes"

if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

# ---------------------------------------------------------
# INYECCIÓN DE ESTILOS CSS (TEMA CLARO - ALTO CONTRASTE)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    /* Fondo principal claro y limpio */
    .stApp {
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
    }
    
    /* Barra lateral en tono claro sutil */
    [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 2px solid #e2e8f0 !important;
    }
    
    /* Tarjetas y Contenedores blancos con sombra sutil y borde definido */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05) !important;
    }

    /* Títulos principales en negro limpio */
    h1 {
        color: #0f172a !important;
        font-weight: 800 !important;
        -webkit-text-fill-color: initial !important;
    }

    /* Subtítulos en azul oscuro intenso */
    h2, h3 {
        color: #1e3a8a !important;
        font-weight: 700 !important;
    }

    /* Párrafos, textos y markdown en negro puro */
    p, span, label, div, .stMarkdown {
        color: #0f172a !important;
    }

    /* Inputs y Selectores con texto negro visible */
    input, select, textarea, [data-baseweb="select"] {
        color: #0f172a !important;
        background-color: #f8fafc !important;
    }

    /* Métricas / KPIs */
    [data-testid="stMetricValue"] {
        color: #059669 !important;
        font-weight: 800 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #334155 !important;
        font-weight: 600 !important;
    }

    /* Botones primarios (Verde vibrante) */
    button[kind="primary"] {
        background: #10b981 !important;
        border: none !important;
        color: #ffffff !important;
        font-weight: bold !important;
        box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3) !important;
    }

    /* Custom Badges para Estados (Textos oscuros y legibles) */
    .badge-preparado {
        background-color: #d1fae5;
        color: #065f46;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 13px;
        border: 1px solid #a7f3d0;
    }
    .badge-pendiente {
        background-color: #fef9c3;
        color: #854d0e;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 13px;
        border: 1px solid #fef08a;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# HELPER DE BASE DE DATOS
# ---------------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                clave TEXT NOT NULL,
                nombre TEXT NOT NULL,
                rol TEXT NOT NULL
            )
        """
        )

        cursor.execute("SELECT COUNT(*) FROM usuarios")
        if cursor.fetchone()[0] == 0:
            usuarios_base = [
                ("mesero1", "1234", "Carlos Gómez", "mesero"),
                ("cocina1", "1234", "Chef Mario", "cocina"),
                ("caja1", "1234", "Ana Cajera", "caja"),
                ("admin", "admin", "Administrador", "admin"),
            ]
            cursor.executemany(
                "INSERT INTO usuarios (usuario, clave, nombre, rol) VALUES (?, ?, ?, ?)",
                usuarios_base,
            )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
# INICIALIZACIÓN DE SESSION STATE
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
# AUTENTICACIÓN
# ---------------------------------------------------------
def login():
    st.markdown(
        "<h1 style='text-align: center; margin-top: 40px; color: #0f172a;'>⚡ FastFood POS Pro</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #475569; font-weight: 600;'>Acceso al Control Operativo</p>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.container(border=True):
            st.markdown("### 🔐 Iniciar Sesión")
            user = st.text_input("Usuario")
            clave = st.text_input("Contraseña", type="password")
            submit = st.button(
                "🚀 INGRESAR AL SISTEMA",
                type="primary",
                use_container_width=True,
            )

            if submit:
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, nombre, rol FROM usuarios WHERE usuario=? AND clave=?",
                        (user.strip(), clave.strip()),
                    )
                    res = cursor.fetchone()
                    if res:
                        st.session_state.authenticated = True
                        st.session_state.usuario_actual = res["nombre"]
                        st.session_state.rol_actual = res["rol"]
                        st.success(f"Bienvenido {res['nombre']}")
                        st.rerun()
                    else:
                        st.error("Usuario o contraseña incorrectos.")


def logout():
    st.session_state.authenticated = False
    st.session_state.usuario_actual = None
    st.session_state.rol_actual = None
    st.session_state.carrito = []
    st.rerun()


if not st.session_state.authenticated:
    login()
    st.stop()

# ---------------------------------------------------------
# BARRA LATERAL (SIDEBAR)
# ---------------------------------------------------------
st.sidebar.markdown("# ⚡ FastFood POS")
st.sidebar.markdown(
    f"""
    <div style="background-color: #f8fafc; padding: 15px; border-radius: 10px; border: 1px solid #cbd5e1; border-left: 5px solid #10b981; margin-bottom: 20px;">
        <span style="color: #475569; font-size: 12px; font-weight: bold;">USUARIO ACTIVO</span><br>
        <strong style="color: #0f172a; font-size: 16px;">👤 {st.session_state.usuario_actual}</strong><br>
        <span style="background-color: #d1fae5; color: #065f46; font-size: 11px; padding: 3px 8px; border-radius: 10px; font-weight: bold; text-transform: uppercase;">{st.session_state.rol_actual}</span>
    </div>
""",
    unsafe_allow_html=True,
)

if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    logout()

# ---------------------------------------------------------
# VISTA: MESERO
# ---------------------------------------------------------
def vista_mesero():
    st.markdown("<h1>🛒 Módulo de Pedidos</h1>", unsafe_allow_html=True)
    col_menu, col_carrito = st.columns([2.2, 1.2])

    with col_menu:
        st.subheader("🍔 Catálogo de Productos")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, nombre, precio, icono, imagen_path FROM productos"
            )
            productos = cursor.fetchall()

        if not productos:
            st.info("No hay productos registrados en el menú.")

        cols = st.columns(3)
        for idx, prod in enumerate(productos):
            with cols[idx % 3]:
                with st.container(border=True):
                    img_path = prod["imagen_path"]
                    if img_path and os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)
                    else:
                        st.markdown(
                            f"<h1 style='text-align: center; margin: 10px 0;'>{prod['icono']}</h1>",
                            unsafe_allow_html=True,
                        )

                    st.markdown(
                        f"<p style='color: #0f172a; font-weight: bold; font-size: 15px; margin:0;'>{prod['nombre']}</p>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<h3 style='color: #059669; margin: 0;'>${prod['precio']:.2f}</h3>",
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
            st.subheader("📋 Orden del Cliente")
            cliente = st.text_input(
                "Nombre de Cliente / Mesa",
                key="cliente_input",
                placeholder="Ej. Mesa 4 / Juan",
            )

            st.markdown("---")
            total = 0.0
            if not st.session_state.carrito:
                st.caption("El carrito está vacío.")
            else:
                for i, item in enumerate(st.session_state.carrito):
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.write(f"**{item['nombre']}**")
                    c2.write(f"${item['precio']:.2f}")
                    if c3.button("❌", key=f"del_cart_{i}"):
                        st.session_state.carrito.pop(i)
                        st.rerun()
                    total += item["precio"]

            st.markdown("---")
            st.markdown(
                f"<div style='text-align: right;'><span style='color: #475569; font-weight: bold;'>Total a Pagar:</span><h2 style='color: #059669; margin:0;'>${total:.2f}</h2></div>",
                unsafe_allow_html=True,
            )
            st.write("")

            if st.button(
                "🚀 ENVIAR A COCINA Y CAJA",
                type="primary",
                use_container_width=True,
            ):
                if not cliente.strip():
                    st.warning("Escribe el nombre del cliente o mesa.")
                elif not st.session_state.carrito:
                    st.warning("Selecciona productos del menú.")
                else:
                    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    items_json = json.dumps(st.session_state.carrito)
                    with get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO pedidos (cliente, items, total, mesero, fecha_hora) VALUES (?, ?, ?, ?, ?)",
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
                    st.success("¡Orden enviada!")
                    st.rerun()


# ---------------------------------------------------------
# VISTA: COCINA
# ---------------------------------------------------------
def vista_cocina():
    st.markdown("<h1>🔥 Monitor de Cocina</h1>", unsafe_allow_html=True)
    if st.button("🔄 Actualizar Comandas"):
        st.rerun()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, cliente, items, mesero, fecha_hora FROM pedidos WHERE estado = 'pendiente' ORDER BY id ASC"
        )
        pedidos = cursor.fetchall()

    if not pedidos:
        st.info("Sin comandas pendientes por cocinar 🎉")
        return

    cols = st.columns(3)
    for idx, p in enumerate(pedidos):
        with cols[idx % 3]:
            with st.container(border=True):
                st.markdown(
                    f"<h3 style='color: #ea580c; margin:0;'>Orden #{p['id']}</h3>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<p style='color: #0f172a; font-weight: bold; margin:0;'>Cliente: {p['cliente']}</p>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"Atendido por: {p['mesero']} | 🕒 {p['fecha_hora'][11:16] if p['fecha_hora'] else ''}"
                )
                st.markdown("---")

                items = json.loads(p["items"])
                for it in items:
                    st.markdown(
                        f"<p style='color: #0f172a; font-weight: 600; margin:2px 0;'>• {it['nombre']}</p>",
                        unsafe_allow_html=True,
                    )

                st.markdown("---")
                if st.button(
                    "✔ MARCAR LISTO",
                    key=f"cocina_{p['id']}",
                    use_container_width=True,
                    type="primary",
                ):
                    with get_connection() as conn_up:
                        cursor_up = conn_up.cursor()
                        cursor_up.execute(
                            "UPDATE pedidos SET estado = 'preparado' WHERE id = ?",
                            (p["id"],),
                        )
                        conn_up.commit()
                    st.rerun()


# ---------------------------------------------------------
# VISTA: CAJA
# ---------------------------------------------------------
def vista_caja():
    st.markdown("<h1>💰 Control de Caja y Pagos</h1>", unsafe_allow_html=True)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, monto_apertura FROM cajas WHERE cajero=? AND estado='abierta'",
            (st.session_state.usuario_actual,),
        )
        caja_abierta = cursor.fetchone()

    with st.container(border=True):
        col_caja1, col_caja2 = st.columns([3, 1.2])
        if not caja_abierta:
            col_caja1.markdown(
                "<h3 style='color: #dc2626; margin:0;'>🔴 CAJA CERRADA</h3>",
                unsafe_allow_html=True,
            )
            with col_caja2.popover("🔓 Abrir Caja"):
                monto_apertura = st.number_input(
                    "Monto Base Inicial ($):", min_value=0.0, step=5.0
                )
                if st.button("Confirmar Apertura"):
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with get_connection() as conn_ins:
                        c_ins = conn_ins.cursor()
                        c_ins.execute(
                            "INSERT INTO cajas (cajero, monto_apertura, fecha_apertura, estado) VALUES (?, ?, ?, 'abierta')",
                            (
                                st.session_state.usuario_actual,
                                monto_apertura,
                                fecha,
                            ),
                        )
                        conn_ins.commit()
                    st.success("Caja Abierta Exitosamente")
                    st.rerun()
        else:
            col_caja1.markdown(
                f"<h3 style='color: #059669; margin:0;'>🟢 CAJA ABIERTA <small style='font-size:14px; color:#475569;'>(Base: ${caja_abierta['monto_apertura']:.2f})</small></h3>",
                unsafe_allow_html=True,
            )
            if col_caja2.button("🔒 CERRAR CAJA (ARQUEO)"):
                with get_connection() as conn_tot:
                    c_tot = conn_tot.cursor()
                    c_tot.execute(
                        "SELECT SUM(total) FROM pedidos WHERE estado='cobrado'"
                    )
                    ventas = c_tot.fetchone()[0] or 0.0

                base = caja_abierta["monto_apertura"]
                esperado = base + ventas
                fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                with get_connection() as conn_close:
                    c_close = conn_close.cursor()
                    c_close.execute(
                        "UPDATE cajas SET monto_cierre=?, ventas_efectivo=?, fecha_cierre=?, estado='cerrada' WHERE id=?",
                        (esperado, ventas, fecha, caja_abierta["id"]),
                    )
                    conn_close.commit()
                st.balloons()
                st.success(f"Caja Cerrada. Arqueo Esperado: ${esperado:.2f}")
                st.rerun()

    st.subheader("💳 Cuentas Pendientes")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, cliente, items, total, estado, mesero, fecha_hora FROM pedidos WHERE estado != 'cobrado' AND estado != 'anulado'"
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
                    f"### Orden #{p['id']} - <span style='color:#0284c7;'>{p['cliente']}</span>",
                    unsafe_allow_html=True,
                )
                st.caption(f"Mesero: {p['mesero']}")

                if p["estado"] == "preparado":
                    st.markdown(
                        "<span class='badge-preparado'>¡LISTO PARA ENTREGAR!</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<span class='badge-pendiente'>En cocina...</span>",
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    f"<h2 style='color:#059669; margin-top:10px;'>${p['total']:.2f}</h2>",
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
                    with get_connection() as conn_pay:
                        c_pay = conn_pay.cursor()
                        c_pay.execute(
                            "UPDATE pedidos SET estado = 'cobrado' WHERE id = ?",
                            (p["id"],),
                        )
                        conn_pay.commit()
                    st.success(f"Cobro Exitoso. Cambio: ${cambio:.2f}")
                    st.rerun()


# ---------------------------------------------------------
# VISTA: ADMINISTRADOR
# ---------------------------------------------------------
def vista_admin():
    st.markdown("<h1>🛡️ Módulo Administrador</h1>", unsafe_allow_html=True)
    tab_reportes, tab_usuarios, tab_menu = st.tabs(
        ["📊 Reportes KPI", "👥 Personal", "🍔 Menú"]
    )

    with tab_reportes:
        filtro = st.selectbox(
            "📅 Filtrar reporte por fecha:",
            ["Hoy", "Ayer", "Últimos 7 días", "Todos los Tiempos"],
        )

        hoy = datetime.now()
        where_clause = ""
        if filtro == "Hoy":
            where_clause = f"WHERE fecha_hora LIKE '{hoy.strftime('%Y-%m-%d')}%'"
        elif filtro == "Ayer":
            ayer = (hoy - timedelta(days=1)).strftime("%Y-%m-%d")
            where_clause = f"WHERE fecha_hora LIKE '{ayer}%'"
        elif filtro == "Últimos 7 días":
            hace_7 = (hoy - timedelta(days=7)).strftime("%Y-%m-%d")
            where_clause = f"WHERE fecha_hora >= '{hace_7}'"

        with get_connection() as conn:
            cursor = conn.cursor()

            and_cobrado = (
                "AND estado='cobrado'"
                if where_clause
                else "WHERE estado='cobrado'"
            )
            cursor.execute(
                f"SELECT SUM(total) FROM pedidos {where_clause} {and_cobrado}"
            )
            cobrado = cursor.fetchone()[0] or 0.0

            and_anulado = (
                "AND estado='anulado'"
                if where_clause
                else "WHERE estado='anulado'"
            )
            cursor.execute(
                f"SELECT COUNT(*), SUM(total) FROM pedidos {where_clause} {and_anulado}"
            )
            res_anulado = cursor.fetchone()
            cant_anulados = res_anulado[0] or 0
            monto_anulado = res_anulado[1] or 0.0

            cursor.execute(f"SELECT COUNT(*) FROM pedidos {where_clause}")
            total_pedidos = cursor.fetchone()[0] or 0

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("💵 Ventas Cobradas", f"${cobrado:.2f}")
        kpi2.metric(
            "🚫 Órdenes Anuladas",
            f"{cant_anulados}",
            delta=f"-${monto_anulado:.2f}",
            delta_color="inverse",
        )
        kpi3.metric("📦 Total de Pedidos", f"{total_pedidos}")

        st.subheader("📋 Historial Reciente")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT id, fecha_hora, mesero, cliente, total, estado FROM pedidos {where_clause} ORDER BY id DESC"
            )
            pedidos_historial = cursor.fetchall()

        if pedidos_historial:
            for p in pedidos_historial:
                with st.container(border=True):
                    col_h1, col_h2, col_h3, col_h4, col_h5, col_h6 = st.columns(
                        [1, 2, 2, 2, 2, 2]
                    )
                    col_h1.write(f"#{p['id']}")
                    col_h2.write(p["fecha_hora"])
                    col_h3.write(p["mesero"])
                    col_h4.write(p["cliente"])
                    col_h5.write(f"${p['total']:.2f}")

                    if p["estado"] != "anulado":
                        if col_h6.button("🚫 Anular", key=f"anular_{p['id']}"):
                            with get_connection() as conn_an:
                                c_an = conn_an.cursor()
                                c_an.execute(
                                    "UPDATE pedidos SET estado='anulado' WHERE id=?",
                                    (p["id"],),
                                )
                                conn_an.commit()
                            st.rerun()
                    else:
                        col_h6.error("ANULADO")

    with tab_usuarios:
        col_u_form, col_u_tabla = st.columns([1, 1.5])

        with col_u_form:
            with st.container(border=True):
                st.subheader("➕ Registrar Usuario")
                u_nombre = st.text_input("Nombre Completo")
                u_user = st.text_input("Nombre de Usuario")
                u_clave = st.text_input("Contraseña", type="password")
                u_rol = st.selectbox(
                    "Rol / Cargo", ["mesero", "cocina", "caja", "admin"]
                )

                if st.button("Guardar Usuario", type="primary"):
                    if u_nombre and u_user and u_clave:
                        try:
                            with get_connection() as conn:
                                c = conn.cursor()
                                c.execute(
                                    "INSERT INTO usuarios (nombre, usuario, clave, rol) VALUES (?, ?, ?, ?)",
                                    (u_nombre, u_user, u_clave, u_rol),
                                )
                                conn.commit()
                            st.success("Usuario creado con éxito.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("El usuario ya existe.")
                    else:
                        st.warning("Completa los datos.")

        with col_u_tabla:
            st.subheader("👥 Personal en Sistema")
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, nombre, usuario, rol FROM usuarios"
                )
                users = cursor.fetchall()

            for u in users:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                    c1.write(f"**{u['nombre']}**")
                    c2.write(f"`{u['usuario']}`")
                    c3.write(u["rol"].upper())
                    if c4.button("🗑️", key=f"del_user_{u['id']}"):
                        with get_connection() as conn_del:
                            c_del = conn_del.cursor()
                            c_del.execute(
                                "DELETE FROM usuarios WHERE id=?", (u["id"],)
                            )
                            conn_del.commit()
                        st.rerun()

    with tab_menu:
        col_m_form, col_m_tabla = st.columns([1, 1.5])

        with col_m_form:
            with st.container(border=True):
                st.subheader("➕ Registrar Producto")
                p_nombre = st.text_input("Nombre del Producto")
                p_precio = st.number_input(
                    "Precio ($)", min_value=0.0, step=0.5
                )
                p_imagen = st.file_uploader(
                    "Imagen", type=["jpg", "png", "jpeg", "webp"]
                )

                if st.button("Guardar Producto", type="primary"):
                    if p_nombre and p_precio > 0:
                        dest_path = ""
                        if p_imagen is not None:
                            nom_limpio = "".join(
                                c
                                for c in p_nombre
                                if c.isalnum() or c in (" ", "_")
                            ).rstrip()
                            ext = os.path.splitext(p_imagen.name)[1]
                            dest_path = os.path.join(
                                IMG_DIR, f"prod_{nom_limpio.replace(' ', '_')}{ext}"
                            )

                            img = Image.open(p_imagen).convert("RGB")
                            img.save(dest_path)

                        with get_connection() as conn:
                            c = conn.cursor()
                            c.execute(
                                "INSERT INTO productos (nombre, precio, categoria, icono, imagen_path) VALUES (?, ?, 'General', '🍔', ?)",
                                (p_nombre, p_precio, dest_path),
                            )
                            conn.commit()
                        st.success(f"Producto '{p_nombre}' guardado.")
                        st.rerun()
                    else:
                        st.warning("Escribe nombre y precio.")

        with col_m_tabla:
            st.subheader("📋 Menú Registrado")
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, nombre, precio, imagen_path FROM productos"
                )
                prods_menu = cursor.fetchall()

            for pm in prods_menu:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
                    if pm["imagen_path"] and os.path.exists(pm["imagen_path"]):
                        c1.image(pm["imagen_path"], width=40)
                    else:
                        c1.write("🍔")
                    c2.write(f"**{pm['nombre']}**")
                    c3.write(f"${pm['precio']:.2f}")
                    if c4.button("🗑️", key=f"del_prod_{pm['id']}"):
                        with get_connection() as conn_del_p:
                            c_dp = conn_del_p.cursor()
                            c_dp.execute(
                                "DELETE FROM productos WHERE id=?", (pm["id"],)
                            )
                            conn_del_p.commit()
                        st.rerun()


# ---------------------------------------------------------
# ENRUTADOR POR ROL
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
