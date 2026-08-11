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
# HELPER DE BASE DE DATOS
# ---------------------------------------------------------
def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        # Tabla Usuarios
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

        # Tabla Productos
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

        # Tabla Pedidos
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

        # Tabla Cajas
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
        "<h1 style='text-align: center; color: #10b981;'>⚡ FastFood POS Pro</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h4 style='text-align: center;'>Inicio de Sesión por Rol</h4>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            user = st.text_input("Usuario")
            clave = st.text_input("Contraseña", type="password")
            submit = st.form_submit_button(
                "INGRESAR AL SISTEMA", use_container_width=True
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
st.sidebar.title("⚡ FastFood POS Pro")
st.sidebar.markdown(
    f"👤 **{st.session_state.usuario_actual}**\n\n📌 Rol: `{st.session_state.rol_actual.upper()}`"
)
if st.sidebar.button("Cerrar Sesión ➔", use_container_width=True):
    logout()

# ---------------------------------------------------------
# VISTA: MESERO
# ---------------------------------------------------------
def vista_mesero():
    st.header("🛒 Módulo de Pedidos (Mesero)")
    col_menu, col_carrito = st.columns([2, 1])

    with col_menu:
        st.subheader("Catálogo de Productos")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, nombre, precio, icono, imagen_path FROM productos"
            )
            productos = cursor.fetchall()

        if not productos:
            st.info(
                "No hay productos registrados. Un administrador debe agregarlos."
            )

        cols = st.columns(3)
        for idx, prod in enumerate(productos):
            with cols[idx % 3]:
                with st.container(border=True):
                    img_path = prod["imagen_path"]
                    if img_path and os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)
                    else:
                        st.markdown(
                            f"<h1 style='text-align: center;'>{prod['icono']}</h1>",
                            unsafe_allow_html=True,
                        )

                    st.markdown(f"**{prod['nombre']}**")
                    st.markdown(
                        f"<h4 style='color: #10b981;'>${prod['precio']:.2f}</h4>",
                        unsafe_allow_html=True,
                    )

                    if st.button(
                        "Agregar +",
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
        st.subheader("Orden del Cliente")
        cliente = st.text_input("Nombre de Cliente / Mesa", key="cliente_input")

        st.markdown("---")
        total = 0.0
        if not st.session_state.carrito:
            st.write("El carrito está vacío.")
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
        st.markdown(f"### TOTAL: `${total:.2f}`")

        if st.button(
            "🚀 ENVIAR A COCINA Y CAJA",
            type="primary",
            use_container_width=True,
        ):
            if not cliente.strip():
                st.warning("Por favor ingresa el nombre del cliente o mesa.")
            elif not st.session_state.carrito:
                st.warning("El carrito no tiene productos.")
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
                st.success("¡Orden registrada correctamente!")
                st.rerun()


# ---------------------------------------------------------
# VISTA: COCINA
# ---------------------------------------------------------
def vista_cocina():
    st.header("🔥 Monitor de Cocina - Comandas Pendientes")
    if st.button("🔄 Actualizar Comandas"):
        st.rerun()

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, cliente, items, mesero, fecha_hora FROM pedidos WHERE estado = 'pendiente' ORDER BY id ASC"
        )
        pedidos = cursor.fetchall()

    if not pedidos:
        st.info("No hay comandas pendientes por preparar.")
        return

    cols = st.columns(3)
    for idx, p in enumerate(pedidos):
        with cols[idx % 3]:
            with st.container(border=True):
                st.subheader(f"Orden #{p['id']} - {p['cliente']}")
                st.caption(
                    f"📱 Atendido por: {p['mesero']} | 🕒 {p['fecha_hora'][11:16] if p['fecha_hora'] else ''}"
                )
                st.markdown("---")

                items = json.loads(p["items"])
                for it in items:
                    st.write(f"• **{it['nombre']}**")

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
    st.header("💰 Panel de Caja y Arqueo")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, monto_apertura FROM cajas WHERE cajero=? AND estado='abierta'",
            (st.session_state.usuario_actual,),
        )
        caja_abierta = cursor.fetchone()

    # Sección de Estado de Caja
    with st.container(border=True):
        col_caja1, col_caja2 = st.columns([3, 1])
        if not caja_abierta:
            col_caja1.error("🔴 CAJA CERRADA")
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
                    st.success("Caja Abierta")
                    st.rerun()
        else:
            col_caja1.success(
                f"🟢 CAJA ABIERTA (Base: ${caja_abierta['monto_apertura']:.2f})"
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
                st.success(f"Caja Cerrada. Total Esperado en Arqueo: ${esperado:.2f}")
                st.rerun()

    st.subheader("Órdenes Pendientes de Cobro")

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
                st.subheader(f"Orden #{p['id']} - {p['cliente']}")
                st.caption(
                    f"Mesero: {p['mesero']} | {p['fecha_hora'][11:16] if p['fecha_hora'] else ''}"
                )

                if p["estado"] == "preparado":
                    st.success("¡LISTO PARA ENTREGAR!")
                else:
                    st.warning("En preparación")

                st.markdown(f"### Total: `${p['total']:.2f}`")

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
                    st.success(f"Cobro Exitoso. Cambio a entregar: ${cambio:.2f}")
                    st.rerun()


# ---------------------------------------------------------
# VISTA: ADMINISTRADOR
# ---------------------------------------------------------
def vista_admin():
    st.header("🛡️ Panel de Administración")
    tab_reportes, tab_usuarios, tab_menu = st.tabs(
        ["📊 Reportes", "👥 Usuarios & Personal", "🍔 Gestión de Menú"]
    )

    # ------------------ TAB REPORTES ------------------
    with tab_reportes:
        filtro = st.selectbox(
            "📅 Filtrar por fecha:",
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
            "🚫 Ventas Anuladas",
            f"{cant_anulados}",
            delta=f"-${monto_anulado:.2f}",
            delta_color="inverse",
        )
        kpi3.metric("📦 Total Pedidos", f"{total_pedidos}")

        st.subheader("📋 Historial de Órdenes")
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT id, fecha_hora, mesero, cliente, total, estado FROM pedidos {where_clause} ORDER BY id DESC"
            )
            pedidos_historial = cursor.fetchall()

        if pedidos_historial:
            for p in pedidos_historial:
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
                    col_h6.write("🚫 ANULADO")

    # ------------------ TAB USUARIOS ------------------
    with tab_usuarios:
        col_u_form, col_u_tabla = st.columns([1, 2])

        with col_u_form:
            st.subheader("➕ Crear Usuario")
            with st.form("form_crear_usuario"):
                u_nombre = st.text_input("Nombre Completo")
                u_user = st.text_input("Nombre de Usuario")
                u_clave = st.text_input("Contraseña", type="password")
                u_rol = st.selectbox(
                    "Rol / Cargo", ["mesero", "cocina", "caja", "admin"]
                )
                btn_u = st.form_submit_button("Guardar Usuario")

                if btn_u:
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
                            st.error("El nombre de usuario ya existe.")
                    else:
                        st.warning("Completa todos los campos.")

        with col_u_tabla:
            st.subheader("👥 Personal Registrado")
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, nombre, usuario, rol FROM usuarios"
                )
                users = cursor.fetchall()

            for u in users:
                c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                c1.write(u["nombre"])
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

    # ------------------ TAB MENÚ ------------------
    with tab_menu:
        col_m_form, col_m_tabla = st.columns([1, 2])

        with col_m_form:
            st.subheader("➕ Registrar Producto")
            with st.form("form_producto"):
                p_nombre = st.text_input("Nombre del Producto")
                p_precio = st.number_input(
                    "Precio ($)", min_value=0.0, step=0.5
                )
                p_imagen = st.file_uploader(
                    "Imagen del Producto", type=["jpg", "png", "jpeg", "webp"]
                )
                btn_p = st.form_submit_button("Guardar Producto")

                if btn_p:
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
                        st.success(f"Producto '{p_nombre}' registrado.")
                        st.rerun()
                    else:
                        st.warning("Ingresa un nombre y precio válido.")

        with col_m_tabla:
            st.subheader("📋 Menú Actual")
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, nombre, precio, imagen_path FROM productos"
                )
                prods_menu = cursor.fetchall()

            for pm in prods_menu:
                c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
                if pm["imagen_path"] and os.path.exists(pm["imagen_path"]):
                    c1.image(pm["imagen_path"], width=40)
                else:
                    c1.write("🍔")
                c2.write(pm["nombre"])
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
