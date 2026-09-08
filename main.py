import json
import os
import sqlite3
from datetime import datetime, timedelta
import streamlit as st

# Configuración de la página Web
st.set_page_config(
    page_title="FastFood POS Pro",
    page_icon="⚡",
    layout="wide"
)

# ==========================================
# BASE DE DATOS Y MIGRACIONES
# ==========================================
def get_db():
    conn = sqlite3.connect("restaurante.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            clave TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        usuarios_base = [
            ("mesero1", "1234", "Carlos Gómez", "mesero"),
            ("cocina1", "1234", "Chef Mario", "cocina"),
            ("caja1", "1234", "Ana Cajera", "caja"),
            ("multi1", "1234", "Juan Multitarea", "multitarea"),
            ("admin", "admin", "Administrador", "admin"),
        ]
        cursor.executemany(
            "INSERT INTO usuarios (usuario, clave, nombre, rol) VALUES (?, ?, ?, ?)",
            usuarios_base,
        )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM categorias")
    if cursor.fetchone()[0] == 0:
        cats = [("Alitas & Entradas",), ("Hamburguesas",), ("Bebidas",), ("Porciones & Acompañantes",), ("General",)]
        cursor.executemany("INSERT INTO categorias (nombre) VALUES (?)", cats)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS salsas_terminos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM salsas_terminos")
    if cursor.fetchone()[0] == 0:
        salsas_base = [
            ("BBQ",), ("Picante",), ("Queso",), ("Mostaza Miel",), 
            ("Ajo y Hierbas",), ("Bien Cocido",), ("Término Medio",), ("Sin Salsa / Al Natural",)
        ]
        cursor.executemany("INSERT INTO salsas_terminos (nombre) VALUES (?)", salsas_base)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            categoria TEXT DEFAULT 'General',
            icono TEXT DEFAULT '🍔',
            imagen_path TEXT DEFAULT '',
            requiere_salsa INTEGER DEFAULT 0
        )
    """)

    try:
        cursor.execute("ALTER TABLE productos ADD COLUMN requiere_salsa INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cursor.execute("SELECT COUNT(*) FROM productos")
    if cursor.fetchone()[0] == 0:
        prods_base = [
            ("Porción de Alitas (6 unidades)", 5.50, "Alitas & Entradas", "🍗", "", 1),
            ("Porción de Papas", 1.50, "Porciones & Acompañantes", "🍟", "", 0),
            ("Porción de Arroz", 1.00, "Porciones & Acompañantes", "🍚", "", 0),
            ("Porción de Ensalada", 1.25, "Porciones & Acompañantes", "🥗", "", 0),
        ]
        cursor.executemany(
            "INSERT INTO productos (nombre, precio, categoria, icono, imagen_path, requiere_salsa) VALUES (?, ?, ?, ?, ?, ?)",
            prods_base,
        )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            items TEXT NOT NULL,
            total REAL NOT NULL,
            estado TEXT DEFAULT 'pendiente',
            mesero TEXT DEFAULT 'Sistema',
            metodo_pago TEXT DEFAULT 'Efectivo',
            fecha_hora TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metodos_pago (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM metodos_pago")
    if cursor.fetchone()[0] == 0:
        metodos_base = [
            ("Efectivo",),
            ("Transf. Banco de Loja",),
            ("Transf. Banco Pichincha",)
        ]
        cursor.executemany("INSERT INTO metodos_pago (nombre) VALUES (?)", metodos_base)

    cursor.execute("""
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
    """)

    conn.commit()

init_db()

# Inicializar Variables de Sesión
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = ""
if "rol_actual" not in st.session_state:
    st.session_state.rol_actual = ""
if "carrito" not in st.session_state:
    st.session_state.carrito = []

# ==========================================
# AUTENTICACIÓN
# ==========================================
def login():
    st.title("⚡ FastFood POS Pro Web")
    st.subheader("Inicio de Sesión")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR AL SISTEMA", use_container_width=True):
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, rol FROM usuarios WHERE usuario=? AND clave=?", (username, password))
            res = cursor.fetchone()
            if res:
                st.session_state.authenticated = True
                st.session_state.usuario_actual = res[1]
                st.session_state.rol_actual = res[2]
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

def logout():
    st.session_state.authenticated = False
    st.session_state.usuario_actual = ""
    st.session_state.rol_actual = ""
    st.session_state.carrito = []
    st.rerun()

# ==========================================
# MÓDULO PEDIDOS
# ==========================================
def modulo_tomar_pedido():
    st.header("📝 Toma de Pedidos")
    conn = get_db()
    cursor = conn.cursor()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        cursor.execute("SELECT nombre FROM categorias")
        cats = ["Todas"] + [c[0] for c in cursor.fetchall()]
        cat_sel = st.selectbox("📁 Filtrar por Sección:", cats)

        if cat_sel == "Todas":
            cursor.execute("SELECT id, nombre, precio, icono, requiere_salsa FROM productos")
        else:
            cursor.execute("SELECT id, nombre, precio, icono, requiere_salsa FROM productos WHERE categoria=?", (cat_sel,))
        prods = cursor.fetchall()

        grid_cols = st.columns(3)
        for idx, (p_id, p_nombre, p_precio, p_icono, p_req) in enumerate(prods):
            with grid_cols[idx % 3]:
                st.markdown(f"### {p_icono} {p_nombre}")
                st.markdown(f"**${p_precio:.2f}**")
                
                if p_req == 1:
                    cursor.execute("SELECT nombre FROM salsas_terminos")
                    salsas = [s[0] for s in cursor.fetchall()]
                    salsa_sel = st.selectbox(f"Salsa/Término ({p_nombre}):", salsas, key=f"salsa_{p_id}_{idx}")
                    nota = st.text_input(f"Nota ({p_nombre}):", key=f"nota_{p_id}_{idx}")
                    if st.button("Agregar +", key=f"btn_{p_id}_{idx}"):
                        item_nombre = f"{p_nombre} [{salsa_sel}]"
                        if nota:
                            item_nombre += f" ({nota})"
                        st.session_state.carrito.append({"nombre": item_nombre, "precio": p_precio})
                        st.success("Agregado")
                        st.rerun()
                else:
                    if st.button("Agregar +", key=f"btn_{p_id}_{idx}"):
                        st.session_state.carrito.append({"nombre": p_nombre, "precio": p_precio})
                        st.success("Agregado")
                        st.rerun()

    with col_right:
        st.subheader("🛒 Orden Actual")
        cliente = st.text_input("Nombre de Cliente / Mesa:")

        st.markdown("---")
        st.subheader("✨ Item Especial / Pedido Libre")
        with st.expander("Añadir Pedido Especial"):
            desc_libre = st.text_input("Descripción:")
            precio_libre = st.number_input("Precio ($):", min_value=0.0, step=0.50)
            if st.button("Agregar Pedido Especial"):
                if desc_libre and precio_libre > 0:
                    st.session_state.carrito.append({"nombre": f"⭐ {desc_libre}", "precio": precio_libre})
                    st.rerun()

        st.markdown("---")
        total = 0.0
        for idx, item in enumerate(st.session_state.carrito):
            total += item["precio"]
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(item["nombre"])
            c2.write(f"${item['precio']:.2f}")
            if c3.button("✕", key=f"del_cart_{idx}"):
                st.session_state.carrito.pop(idx)
                st.rerun()

        st.markdown(f"### TOTAL: ${total:.2f}")

        if st.button("🚀 REGISTRAR PEDIDO", type="primary", use_container_width=True):
            if not cliente:
                st.warning("Escribe el nombre del cliente.")
            elif not st.session_state.carrito:
                st.warning("El carrito está vacío.")
            else:
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT INTO pedidos (cliente, items, total, mesero, fecha_hora) VALUES (?, ?, ?, ?, ?)",
                    (cliente, json.dumps(st.session_state.carrito), total, st.session_state.usuario_actual, fecha_actual),
                )
                conn.commit()
                st.session_state.carrito = []
                st.success("¡Orden registrada exitosamente!")
                st.rerun()

# ==========================================
# MÓDULO COBROS Y CAJA
# ==========================================
def modulo_caja():
    st.header("💰 Panel de Cobros y Caja")
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, monto_apertura FROM cajas WHERE cajero=? AND estado='abierta'", (st.session_state.usuario_actual,))
    caja_abierta = cursor.fetchone()

    if not caja_abierta:
        st.warning("⚠️ La caja se encuentra CERRADA.")
        monto_base = st.number_input("Monto base de apertura ($):", min_value=0.0, step=5.0)
        if st.button("🔓 ABRIR CAJA"):
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO cajas (cajero, monto_apertura, fecha_apertura, estado) VALUES (?, ?, ?, 'abierta')",
                           (st.session_state.usuario_actual, monto_base, fecha))
            conn.commit()
            st.success(f"Caja abierta con base de ${monto_base:.2f}")
            st.rerun()
    else:
        st.success(f"🟢 CAJA ABIERTA | Base Inicial: ${caja_abierta[1]:.2f}")
        if st.button("🔒 CERRAR CAJA (Arqueo)"):
            cursor.execute("SELECT SUM(total) FROM pedidos WHERE estado='cobrado'")
            total_v = cursor.fetchone()[0] or 0.0
            esperado = caja_abierta[1] + total_v
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE cajas SET monto_cierre=?, ventas_efectivo=?, fecha_cierre=?, estado='cerrada' WHERE id=?",
                           (esperado, total_v, fecha, caja_abierta[0]))
            conn.commit()
            st.info(f"Caja cerrada. Total acumulado en arqueo: ${esperado:.2f}")
            st.rerun()

    st.markdown("---")
    st.subheader("Órdenes Pendientes de Cobro")

    cursor.execute("SELECT nombre FROM metodos_pago")
    metodos = [m[0] for m in cursor.fetchall()]

    cursor.execute("SELECT id, cliente, items, total, mesero, fecha_hora FROM pedidos WHERE estado != 'cobrado' AND estado != 'anulado'")
    pedidos_pendientes = cursor.fetchall()

    if not pedidos_pendientes:
        st.info("No hay pedidos pendientes por cobrar.")

    cols = st.columns(3)
    for idx, (p_id, cliente, items_raw, total, mesero, fh) in enumerate(pedidos_pendientes):
        with cols[idx % 3]:
            st.markdown(f"### Orden #{p_id} - {cliente}")
            st.write(f"Atendido por: **{mesero}**")
            st.markdown(f"## Total: ${total:.2f}")

            metodo_sel = st.selectbox("Método de Pago:", metodos, key=f"mp_{p_id}")
            if st.button("💵 COBRAR", key=f"cobrar_{p_id}", type="primary"):
                cursor.execute("UPDATE pedidos SET estado = 'cobrado', metodo_pago = ? WHERE id = ?", (metodo_sel, p_id))
                conn.commit()
                st.success(f"Orden #{p_id} cobrada.")
                st.rerun()

# ==========================================
# MÓDULO COCINA
# ==========================================
def modulo_cocina():
    st.header("🔥 Monitor de Cocina - Comandas Pendientes")
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, cliente, items, mesero FROM pedidos WHERE estado = 'pendiente'")
    pedidos = cursor.fetchall()

    if not pedidos:
        st.info("No hay comandas pendientes en cocina.")

    cols = st.columns(3)
    for idx, (p_id, cliente, items_raw, mesero) in enumerate(pedidos):
        with cols[idx % 3]:
            st.error(f"Orden #{p_id} - {cliente}")
            st.caption(f"Atendido por: {mesero}")
            items = json.loads(items_raw)
            for item in items:
                st.write(f"• {item['nombre']}")
            if st.button("✔ MARCAR LISTO", key=f"cocina_{p_id}"):
                cursor.execute("UPDATE pedidos SET estado = 'preparado' WHERE id = ?", (p_id,))
                conn.commit()
                st.rerun()

# ==========================================
# MÓDULO REPORTES DETALLADOS
# ==========================================
def modulo_reportes():
    st.header("📊 Reportes y Métricas Detalladas")
    conn = get_db()
    cursor = conn.cursor()

    opcion_rango = st.selectbox("📅 Seleccionar Rango / Filtro:", ["Hoy", "Ayer", "Últimos 7 días", "Todos los Tiempos", "Día Específico"])
    
    filtro_sql = ""
    hoy = datetime.now()

    if opcion_rango == "Hoy":
        filtro_sql = f"WHERE fecha_hora LIKE '{hoy.strftime('%Y-%m-%d')}%'"
    elif opcion_rango == "Ayer":
        filtro_sql = f"WHERE fecha_hora LIKE '{(hoy - timedelta(days=1)).strftime('%Y-%m-%d')}%'"
    elif opcion_rango == "Últimos 7 días":
        filtro_sql = f"WHERE fecha_hora >= '{(hoy - timedelta(days=7)).strftime('%Y-%m-%d')}'"
    elif opcion_rango == "Día Específico":
        fecha_manual = st.date_input("Selecciona la fecha exacta:", datetime.now())
        filtro_sql = f"WHERE fecha_hora LIKE '{fecha_manual.strftime('%Y-%m-%d')}%'"

    and_cobrado = "AND estado='cobrado'" if filtro_sql else "WHERE estado='cobrado'"
    cursor.execute(f"SELECT SUM(total) FROM pedidos {filtro_sql} {and_cobrado}")
    total_cobrado = cursor.fetchone()[0] or 0.0

    cursor.execute(f"SELECT COUNT(*) FROM pedidos {filtro_sql}")
    total_pedidos = cursor.fetchone()[0] or 0

    kpi1, kpi2 = st.columns(2)
    kpi1.metric("💵 Ventas Totales Cobradas", f"${total_cobrado:.2f}")
    kpi2.metric("📦 Cantidad de Pedidos", str(total_pedidos))

    st.markdown("---")
    st.subheader("💳 Desglose por Formas de Pago")
    cursor.execute("SELECT nombre FROM metodos_pago")
    metodos = [m[0] for m in cursor.fetchall()]

    m_cols = st.columns(len(metodos))
    for idx, mp in enumerate(metodos):
        cond_mp = f"{filtro_sql} AND estado='cobrado' AND metodo_pago='{mp}'" if filtro_sql else f"WHERE estado='cobrado' AND metodo_pago='{mp}'"
        cursor.execute(f"SELECT SUM(total), COUNT(*) FROM pedidos {cond_mp}")
        res_mp = cursor.fetchone()
        subtotal_mp = res_mp[0] or 0.0
        cant_mp = res_mp[1] or 0
        m_cols[idx].metric(mp, f"${subtotal_mp:.2f}", f"{cant_mp} transacciones")

    st.markdown("---")
    st.subheader("📋 Historial Detallado de Órdenes")
    cursor.execute(f"SELECT id, fecha_hora, mesero, cliente, metodo_pago, total, estado FROM pedidos {filtro_sql} ORDER BY id DESC")
    pedidos_historial = cursor.fetchall()

    if pedidos_historial:
        st.dataframe(
            pedidos_historial,
            column_config={
                "0": "ID", "1": "Fecha y Hora", "2": "Tomado por", 
                "3": "Cliente/Mesa", "4": "Forma de Pago", "5": "Total ($)", "6": "Estado"
            },
            use_container_width=True
        )

# ==========================================
# ADMINISTRACIÓN Y CONFIGURACIÓN
# ==========================================
def modulo_admin():
    st.header("⚙️ Configuración del Sistema")
    tab1, tab2, tab3, tab4 = st.tabs(["👥 Usuarios", "🍔 Menú y Secciones", "🥫 Salsas & Términos", "💳 Métodos de Pago"])

    conn = get_db()
    cursor = conn.cursor()

    with tab1:
        st.subheader("Gestión de Usuarios")
        with st.form("form_usr"):
            nom = st.text_input("Nombre Completo")
            usr = st.text_input("Nombre de Usuario")
            pwd = st.text_input("Contraseña", type="password")
            rol = st.selectbox("Rol/Cargo", ["mesero", "cocina", "caja", "multitarea", "admin"])
            if st.form_submit_button("Guardar Usuario"):
                if nom and usr and pwd:
                    try:
                        cursor.execute("INSERT INTO usuarios (nombre, usuario, clave, rol) VALUES (?, ?, ?, ?)", (nom, usr, pwd, rol))
                        conn.commit()
                        st.success("Usuario creado")
                        st.rerun()
                    except:
                        st.error("El usuario ya existe.")

        cursor.execute("SELECT id, nombre, usuario, rol FROM usuarios")
        st.table(cursor.fetchall())

    with tab2:
        st.subheader("Gestión de Secciones y Productos")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            n_sec = st.text_input("Nueva Sección/Categoría:")
            if st.button("+ Crear Sección"):
                if n_sec:
                    try:
                        cursor.execute("INSERT INTO categorias (nombre) VALUES (?)", (n_sec,))
                        conn.commit()
                        st.success("Sección agregada")
                        st.rerun()
                    except:
                        st.error("Ya existe")

        with col_s2:
            cursor.execute("SELECT nombre FROM categorias WHERE nombre != 'General'")
            cats_del = [c[0] for c in cursor.fetchall()]
            if cats_del:
                s_del = st.selectbox("Eliminar Sección:", cats_del)
                if st.button("🗑 Borrar Sección"):
                    cursor.execute("UPDATE productos SET categoria='General' WHERE categoria=?", (s_del,))
                    cursor.execute("DELETE FROM categorias WHERE nombre=?", (s_del,))
                    conn.commit()
                    st.success("Sección eliminada")
                    st.rerun()

        st.markdown("---")
        st.subheader("Registrar Producto")
        cursor.execute("SELECT nombre FROM categorias")
        cats_list = [c[0] for c in cursor.fetchall()]
        
        with st.form("form_prod"):
            p_nom = st.text_input("Nombre de Producto")
            p_pre = st.number_input("Precio ($)", min_value=0.0, step=0.50)
            p_cat = st.selectbox("Sección", cats_list)
            p_req = st.checkbox("¿Requiere elegir Salsa o Término?")
            if st.form_submit_button("Guardar Producto"):
                if p_nom and p_pre > 0:
                    cursor.execute("INSERT INTO productos (nombre, precio, categoria, requiere_salsa) VALUES (?, ?, ?, ?)",
                                   (p_nom, p_pre, p_cat, 1 if p_req else 0))
                    conn.commit()
                    st.success("Producto registrado")
                    st.rerun()

    with tab3:
        st.subheader("Salsas y Términos")
        n_salsa = st.text_input("Nueva Salsa o Término (ej: BBQ, Picante, Bien Cocido):")
        if st.button("Guardar Salsa/Término"):
            if n_salsa:
                try:
                    cursor.execute("INSERT INTO salsas_terminos (nombre) VALUES (?)", (n_salsa,))
                    conn.commit()
                    st.success("Guardado")
                    st.rerun()
                except:
                    st.error("Ya existe.")

        cursor.execute("SELECT id, nombre FROM salsas_terminos")
        st.table(cursor.fetchall())

    with tab4:
        st.subheader("Formas de Pago")
        n_pago = st.text_input("Nueva Forma de Pago (ej: Tarjeta de Crédito):")
        if st.button("Guardar Método"):
            if n_pago:
                try:
                    cursor.execute("INSERT INTO metodos_pago (nombre) VALUES (?)", (n_pago,))
                    conn.commit()
                    st.success("Guardado")
                    st.rerun()
                except:
                    st.error("Ya existe.")

        cursor.execute("SELECT id, nombre FROM metodos_pago")
        st.table(cursor.fetchall())

# ==========================================
# APLICACIÓN PRINCIPAL
# ==========================================
if not st.session_state.authenticated:
    login()
else:
    st.sidebar.title("⚡ FastFood POS Pro")
    st.sidebar.write(f"👤 **{st.session_state.usuario_actual}**")
    st.sidebar.caption(f"Rol: {st.session_state.rol_actual.upper()}")

    if st.sidebar.button("Cerrar Sesión", type="secondary"):
        logout()

    st.sidebar.markdown("---")

    rol = st.session_state.rol_actual

    if rol == "mesero":
        modulo_tomar_pedido()
    elif rol == "cocina":
        modulo_cocina()
    elif rol == "caja":
        modulo_caja()
    elif rol == "multitarea":
        opcion = st.sidebar.radio("Navegación:", ["📝 Tomar Pedido", "💰 Cobros y Caja", "🔥 Cocina"])
        if opcion == "📝 Tomar Pedido":
            modulo_tomar_pedido()
        elif opcion == "💰 Cobros y Caja":
            modulo_caja()
        elif opcion == "🔥 Cocina":
            modulo_cocina()
    elif rol == "admin":
        opcion = st.sidebar.radio("Navegación Admin:", ["📝 Tomar Pedido", "💰 Cobros y Caja", "🔥 Cocina", "📊 Reportes", "⚙️ Configuración Admin"])
        if opcion == "📝 Tomar Pedido":
            modulo_tomar_pedido()
        elif opcion == "💰 Cobros y Caja":
            modulo_caja()
        elif opcion == "🔥 Cocina":
            modulo_cocina()
        elif opcion == "📊 Reportes":
            modulo_reportes()
        elif opcion == "⚙️ Configuración Admin":
            modulo_admin()
