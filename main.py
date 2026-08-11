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
# INYECCIÓN DE ESTILOS CSS (TEMA AZUL OSCURO - LETRAS VISIBLES)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    /* Fondo principal con degradado azul oscuro */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%) !important;
        color: #ffffff !important;
    }
    
    /* Barra lateral estilizada */
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div {
        background-color: #0d1117 !important;
        border-right: 1px solid #1f2937 !important;
    }
    
    /* Tarjetas y Contenedores translúcidos */
    [data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stForm"] {
        background: rgba(30, 41, 59, 0.85) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
    }

    /* TEXTOS GLOBALES DE PANTALLA EN BLANCO */
    p, span, label, div, li, td, th, [data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: 500;
    }

    /* -------------------------------------------------- */
    /* CORRECCIÓN PARA CUADROS BLANCOS, DESPLEGABLES Y POPOVERS */
    /* -------------------------------------------------- */
    
    /* Opciones del Selectbox / Desplegable (Fondo blanco -> Letras oscuras) */
    [data-baseweb="menu"], [data-baseweb="popover"], div[role="listbox"], ul[role="listbox"] {
        background-color: #ffffff !important;
    }
    
    [data-baseweb="menu"] * , [data-baseweb="popover"] * , div[role="listbox"] * , ul[role="listbox"] * {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        font-weight: 600 !important;
    }

    /* Hover de opciones desplegables */
    [data-baseweb="option"] {
        background-color: #ffffff !important;
    }
    [data-baseweb="option"]:hover, [aria-selected="true"] {
        background-color: #e2e8f0 !important;
    }

    /* Inputs de texto y selectores principales */
    input, select, [data-baseweb="select"] > div {
        background-color: #1e293b !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        border: 1px solid #475569 !important;
    }

    /* Botones secundarios / blancos (Anular, Cerrar Sesión) */
    button:not([kind="primary"]) {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
    }
    button:not([kind="primary"]) * {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        font-weight: bold !important;
    }

    /* -------------------------------------------------- */

    /* Título H1 principal */
    h1 {
        background: linear-gradient(90deg, #10b981, #38bdf8);
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        font-weight: 800 !important;
    }

    /* Subtítulos H2 y H3 en cian brillante */
    h2, h3 {
        color: #38bdf8 !important;
        -webkit-text-fill-color: #38bdf8 !important;
        font-weight: 700 !important;
    }

    /* Pestañas (Tabs) */
    [data-baseweb="tab-list"] {
        background-color: #1e293b !important;
        border-radius: 8px !important;
        padding: 4px !important;
    }
    [data-baseweb="tab"] p {
        color: #94a3b8 !important;
        -webkit-text-fill-color: #94a3b8 !important;
        font-weight: bold !important;
    }
    [data-baseweb="tab"][aria-selected="true"] {
        background-color: #334155 !important;
        border-radius: 6px !important;
    }
    [data-baseweb="tab"][aria-selected="true"] p {
        color: #38bdf8 !important;
        -webkit-text-fill-color: #38bdf8 !important;
    }

    /* Métricas e Indicadores KPI */
    [data-testid="stMetricValue"] div {
        color: #10b981 !important;
        -webkit-text-fill-color: #10b981 !important;
        font-weight: 800 !important;
    }
    [data-testid="stMetricLabel"] p {
        color: #f1f5f9 !important;
        -webkit-text-fill-color: #f1f5f9 !important;
        font-weight: 700 !important;
    }

    /* Botones primarios (Verde Esmeralda) */
    button[kind="primary"] {
        background: linear-gradient(90deg, #059669 0%, #10b981 100%) !important;
        border: none !important;
    }
    button[kind="primary"] * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: bold !important;
    }

    /* Badges de estado */
    .badge-preparado {
        background-color: #065f46 !important;
        color: #34d399 !important;
        -webkit-text-fill-color: #34d399 !important;
        padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 13px;
    }
    .badge-pendiente {
        background-color: #854d0e !important;
        color: #fef08a !important;
        -webkit-text-fill-color: #fef08a !important;
        padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 13px;
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
                ("multi1", "1234", "Cajera & Mesera", "multifuncion"),
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
        "<h1 style='text-align: center; margin-top: 50px;'>⚡ FastFood POS Pro</h1>",
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
    <div style="background-color: #1e293b; padding: 15px; border-radius: 10px; border-left: 4px solid #10b981; margin-bottom: 20px;">
        <span style="color: #94a3b8; font-size: 12px;">USUARIO ACTIVO</span><br>
        <strong style="color: #f8fafc; font-size: 16px;">👤 {st.session_state.usuario_actual}</strong><br>
        <span style="background-color: #065f46; color: #34d399; font-size: 10px; padding: 2px 8px; border-radius: 10px; font-weight: bold; text-transform: uppercase;">{st.session_state.rol_actual}</span>
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

    tab_nuevo, tab_editar = st.tabs(["📝 Nuevo Pedido", "✏️ Pedidos Activos (Editar / Borrar)"])

    with tab_nuevo:
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

                        st.markdown(f"**{prod['nombre']}**")
                        st.markdown(
                            f"<h3 style='color: #10b981; margin: 0;'>${prod['precio']:.2f}</h3>",
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
                        c1.write(item["nombre"])
                        c2.write(f"${item['precio']:.2f}")
                        if c3.button("❌", key=f"del_cart_{i}"):
                            st.session_state.carrito.pop(i)
                            st.rerun()
                        total += item["precio"]

                st.markdown("---")
                st.markdown(
                    f"<div style='text-align: right;'><span style='color: #94a3b8;'>Total a Pagar:</span><h2 style='color: #10b981; margin:0;'>${total:.2f}</h2></div>",
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

    with tab_editar:
        st.subheader("🛠️ Administrar Pedidos en Curso")
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, cliente, items, total, estado, mesero, fecha_hora FROM pedidos WHERE estado != 'cobrado' AND estado != 'anulado' ORDER BY id DESC"
            )
            pedidos_activos = cursor.fetchall()

        if not pedidos_activos:
            st.info("No hay pedidos activos para modificar en este momento.")
        else:
            for p in pedidos_activos:
                with st.container(border=True):
                    col_p1, col_p2, col_p3 = st.columns([2, 2, 1.5])
                    
                    with col_p1:
                        st.markdown(f"### Orden #{p['id']} - <span style='color:#38bdf8;'>{p['cliente']}</span>", unsafe_allow_html=True)
                        st.caption(f"Atendido por: {p['mesero']} | 🕒 {p['fecha_hora']}")
                        
                        if p["estado"] == "preparado":
                            st.markdown("<span class='badge-preparado'>¡LISTO PARA ENTREGAR!</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("<span class='badge-pendiente'>En cocina...</span>", unsafe_allow_html=True)

                    with col_p2:
                        st.markdown("**Productos:**")
                        items = json.loads(p["items"])
                        for it in items:
                            st.write(f"• {it['nombre']} (${it['precio']:.2f})")
                        st.markdown(f"<h3 style='color:#10b981; margin:0;'>Total: ${p['total']:.2f}</h3>", unsafe_allow_html=True)

                    with col_p3:
                        st.write("")
                        with st.popover("✏️ Editar Pedido", use_container_width=True):
                            st.markdown(f"#### Modificar Orden #{p['id']}")
                            nuevo_cliente = st.text_input("Cliente/Mesa", value=p["cliente"], key=f"edit_cli_{p['id']}")
                            
                            with get_connection() as conn_prod:
                                c_prod = conn_prod.cursor()
                                c_prod.execute("SELECT nombre, precio FROM productos")
                                prods_menu = c_prod.fetchall()
                            
                            if prods_menu:
                                prod_select = st.selectbox(
                                    "Añadir Producto:",
                                    [f"{pm['nombre']} - ${pm['precio']:.2f}" for pm in prods_menu],
                                    key=f"select_p_{p['id']}"
                                )
                                
                                if st.button("➕ Añadir este producto", key=f"btn_add_p_{p['id']}"):
                                    nombre_p = prod_select.split(" - $")[0]
                                    precio_p = float(prod_select.split(" - $")[1])
                                    
                                    items.append({"nombre": nombre_p, "precio": precio_p})
                                    nuevo_total = p["total"] + precio_p
                                    
                                    with get_connection() as conn_up:
                                        c_up = conn_up.cursor()
                                        c_up.execute(
                                            "UPDATE pedidos SET cliente=?, items=?, total=? WHERE id=?",
                                            (nuevo_cliente, json.dumps(items), nuevo_total, p["id"])
                                        )
                                        conn_up.commit()
                                    st.success(f"¡Añadido {nombre_p}!")
                                    st.rerun()

                            if st.button("💾 Guardar Cambios Nombre", key=f"save_name_{p['id']}"):
                                with get_connection() as conn_up_name:
                                    c_un = conn_up_name.cursor()
                                    c_un.execute(
                                        "UPDATE pedidos SET cliente=? WHERE id=?",
                                        (nuevo_cliente, p["id"])
                                    )
                                    conn_up_name.commit()
                                st.success("¡Mesa/Cliente actualizada!")
                                st.rerun()

                        if st.button("🗑️ Anular / Eliminar", key=f"del_ped_{p['id']}", use_container_width=True):
                            with get_connection() as conn_del:
                                c_del = conn_del.cursor()
                                c_del.execute("UPDATE pedidos SET estado='anulado' WHERE id=?", (p["id"],))
                                conn_del.commit()
                            st.warning(f"Orden #{p['id']} Anulada.")
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
                    f"<h3 style='color: #f97316; margin:0;'>Orden #{p['id']}</h3>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**Cliente:** {p['cliente']}")
                st.caption(
                    f"Atendido por: {p['mesero']} | 🕒 {p['fecha_hora'][11:16] if p['fecha_hora'] else ''}"
                )
                st.markdown("---")

                items = json.loads(p["items"])
                for it in items:
                    st.markdown(
                        f"<span style='color: #f8fafc;'>• {it['nombre']}</span>",
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
                "<h3 style='color: #ef4444; margin:0;'>🔴 CAJA CERRADA</h3>",
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
                f"<h3 style='color: #10b981; margin:0;'>🟢 CAJA ABIERTA <small style='font-size:14px; color:#94a3b8;'>(Base: ${caja_abierta['monto_apertura']:.2f})</small></h3>",
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
                    f"### Orden #{p['id']} - <span style='color:#38bdf8;'>{p['cliente']}</span>",
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
                    f"<h2 style='color:#10b981; margin-top:10px;'>${p['total']:.2f}</h2>",
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
# VISTA: MULTIFUNCIÓN (CAJERO & MESERO EN UNA MISMA PANTALLA)
# ---------------------------------------------------------
def vista_multifuncion():
    st.markdown("<h1>⚡ Módulo Integrado (Caja & Mesero)</h1>", unsafe_allow_html=True)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, monto_apertura FROM cajas WHERE cajero=? AND estado='abierta'",
            (st.session_state.usuario_actual,),
        )
        caja_abierta = cursor.fetchone()

    with st.container(border=True):
        col_c1, col_c2 = st.columns([3, 1])
        if not caja_abierta:
            col_c1.markdown("<h4 style='color: #ef4444; margin:0;'>🔴 CAJA CERRADA</h4>", unsafe_allow_html=True)
            with col_c2.popover("🔓 Abrir Caja"):
                m_ap = st.number_input("Monto Inicial ($):", min_value=0.0, step=5.0)
                if st.button("Aceptar"):
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with get_connection() as conn_i:
                        c_i = conn_i.cursor()
                        c_i.execute(
                            "INSERT INTO cajas (cajero, monto_apertura, fecha_apertura, estado) VALUES (?, ?, ?, 'abierta')",
                            (st.session_state.usuario_actual, m_ap, fecha),
                        )
                        conn_i.commit()
                    st.success("Caja Abierta")
                    st.rerun()
        else:
            col_c1.markdown(f"<h4 style='color: #10b981; margin:0;'>🟢 CAJA ABIERTA (Base: ${caja_abierta['monto_apertura']:.2f})</h4>", unsafe_allow_html=True)
            if col_c2.button("🔒 Cerrar Caja"):
                with get_connection() as conn_tot:
                    c_tot = conn_tot.cursor()
                    c_tot.execute("SELECT SUM(total) FROM pedidos WHERE estado='cobrado'")
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
                st.success(f"Caja Cerrada. Arqueo: ${esperado:.2f}")
                st.rerun()

    col_toma, col_cobros, col_edicion = st.columns([1.2, 1.2, 1.2])

    # --- COLUMNA 1: TOMAR NUEVO PEDIDO ---
    with col_toma:
        with st.container(border=True):
            st.subheader("🛒 Nuevo Pedido")
            cli_multi = st.text_input("Mesa / Cliente:", key="cli_multi")
            
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT id, nombre, precio FROM productos")
                prods = c.fetchall()

            if prods:
                p_selected = st.selectbox("Selecciona Producto:", [f"{p['nombre']} - ${p['precio']:.2f}" for p in prods])
                if st.button("➕ Agregar al Carrito", use_container_width=True):
                    nom = p_selected.split(" - $")[0]
                    prec = float(p_selected.split(" - $")[1])
                    st.session_state.carrito.append({"nombre": nom, "precio": prec})
                    st.rerun()

            st.markdown("---")
            total_c = 0.0
            for idx, item in enumerate(st.session_state.carrito):
                cx, cy = st.columns([3, 1])
                cx.write(f"• {item['nombre']} (${item['precio']:.2f})")
                if cy.button("❌", key=f"del_m_{idx}"):
                    st.session_state.carrito.pop(idx)
                    st.rerun()
                total_c += item["precio"]

            st.markdown(f"### Total: `${total_c:.2f}`")

            if st.button("🚀 ENVIAR ORDEN", type="primary", use_container_width=True):
                if not cli_multi.strip() or not st.session_state.carrito:
                    st.warning("Completa la mesa y el carrito.")
                else:
                    fecha_act = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with get_connection() as conn:
                        c = conn.cursor()
                        c.execute(
                            "INSERT INTO pedidos (cliente, items, total, mesero, fecha_hora) VALUES (?, ?, ?, ?, ?)",
                            (cli_multi, json.dumps(st.session_state.carrito), total_c, st.session_state.usuario_actual, fecha_act),
                        )
                        conn.commit()
                    st.session_state.carrito = []
                    st.success("¡Orden Enviada!")
                    st.rerun()

    # --- COLUMNA 2: PANTALLA DE COBROS ---
    with col_cobros:
        with st.container(border=True):
            st.subheader("💵 Cobrar Pedidos")
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT id, cliente, total, estado FROM pedidos WHERE estado != 'cobrado' AND estado != 'anulado' ORDER BY id DESC")
                peds_cobro = c.fetchall()

            if not peds_cobro:
                st.info("Sin cuentas pendientes.")
            else:
                for pc in peds_cobro:
                    with st.container(border=True):
                        st.markdown(f"**Orden #{pc['id']} - {pc['cliente']}**")
                        if pc['estado'] == 'preparado':
                            st.markdown("<span class='badge-preparado'>¡LISTO!</span>", unsafe_allow_html=True)
                        else:
                            st.markdown("<span class='badge-pendiente'>En Cocina</span>", unsafe_allow_html=True)
                        
                        st.markdown(f"<h3 style='color:#10b981; margin:0;'>${pc['total']:.2f}</h3>", unsafe_allow_html=True)
                        pag = st.number_input("Paga ($):", value=float(pc['total']), min_value=float(pc['total']), key=f"pm_{pc['id']}")
                        
                        if st.button("💵 COBRAR", key=f"cob_m_{pc['id']}", use_container_width=True, type="primary"):
                            cambio = pag - pc['total']
                            with get_connection() as conn_up:
                                cu = conn_up.cursor()
                                cu.execute("UPDATE pedidos SET estado='cobrado' WHERE id=?", (pc['id'],))
                                conn_up.commit()
                            st.success(f"Cobrado. Cambio: ${cambio:.2f}")
                            st.rerun()

    # --- COLUMNA 3: EDITAR O BORRAR PEDIDOS ACTIVOS ---
    with col_edicion:
        with st.container(border=True):
            st.subheader("🛠️ Gestor de Mesas")
            with get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT id, cliente, items, total FROM pedidos WHERE estado != 'cobrado' AND estado != 'anulado' ORDER BY id DESC")
                peds_act = c.fetchall()

            if not peds_act:
                st.info("Sin pedidos activos.")
            else:
                for pa in peds_act:
                    with st.container(border=True):
                        st.markdown(f"**#{pa['id']} - {pa['cliente']}** (${pa['total']:.2f})")
                        items_m = json.loads(pa["items"])
                        
                        with st.popover("✏️ Modificar", use_container_width=True):
                            n_cli = st.text_input("Cambiar Mesa:", value=pa["cliente"], key=f"n_cli_{pa['id']}")
                            if prods:
                                p_add = st.selectbox("Añadir producto:", [f"{pr['nombre']} - ${pr['precio']:.2f}" for pr in prods], key=f"p_add_{pa['id']}")
                                if st.button("➕ Añadir", key=f"btn_add_mult_{pa['id']}"):
                                    n_p = p_add.split(" - $")[0]
                                    p_p = float(p_add.split(" - $")[1])
                                    items_m.append({"nombre": n_p, "precio": p_p})
                                    n_tot = pa["total"] + p_p
                                    with get_connection() as conn_u:
                                        cu = conn_u.cursor()
                                        cu.execute("UPDATE pedidos SET cliente=?, items=?, total=? WHERE id=?", (n_cli, json.dumps(items_m), n_tot, pa["id"]))
                                        conn_u.commit()
                                    st.success("Actualizado")
                                    st.rerun()

                        if st.button("🗑️ Anular", key=f"del_m_act_{pa['id']}", use_container_width=True):
                            with get_connection() as conn_d:
                                cd = conn_d.cursor()
                                cd.execute("UPDATE pedidos SET estado='anulado' WHERE id=?", (pa["id"],))
                                conn_d.commit()
                            st.warning("Anulado")
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
                    "Rol / Cargo", ["mesero", "cocina", "caja", "multifuncion", "admin"]
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
elif rol == "multifuncion":
    vista_multifuncion()
elif rol == "admin":
    vista_admin()
