import json
import os
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

# Configuración de página
st.set_page_config(
    page_title="FastFood POS Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==========================================
# BASE DE DATOS SQLITE
# ==========================================
def get_db():
  conn = sqlite3.connect("restaurante.db", check_same_thread=False)
  conn.row_factory = sqlite3.Row
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
        ("admin", "admin", "Administrador", "admin"),
    ]
    cursor.executemany(
        "INSERT INTO usuarios (usuario, clave, nombre, rol) VALUES (?, ?, ?,"
        " ?)",
        usuarios_base,
    )

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            categoria TEXT DEFAULT 'General',
            icono TEXT DEFAULT '🍔',
            imagen_path TEXT DEFAULT ''
        )
    """)

  cursor.execute("SELECT COUNT(*) FROM productos")
  if cursor.fetchone()[0] == 0:
    prods_base = [
        ("Hamburguesa Clásica", 5.50, "General", "🍔", ""),
        ("Papas Fritas", 2.50, "General", "🍟", ""),
        ("Gaseosa 500ml", 1.50, "General", "🥤", ""),
    ]
    cursor.executemany(
        "INSERT INTO productos (nombre, precio, categoria, icono, imagen_path)"
        " VALUES (?, ?, ?, ?, ?)",
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
            fecha_hora TEXT DEFAULT ''
        )
    """)

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
  conn.close()


init_db()

# ==========================================
# MANEJO DE SESIÓN DE USUARIO
# ==========================================
if "logged_in" not in st.session_state:
  st.session_state.logged_in = False
  st.session_state.usuario = ""
  st.session_state.nombre = ""
  st.session_state.rol = ""
  st.session_state.carrito = []

# ==========================================
# PANTALLA DE LOGIN
# ==========================================
if not st.session_state.logged_in:
  st.markdown(
      "<h1 style='text-align: center;'>⚡ FastFood POS Pro</h1>",
      unsafe_allow_html=True,
  )
  st.markdown(
      "<p style='text-align: center; color: gray;'>Inicio de Sesión por"
      " Rol</p>",
      unsafe_allow_html=True,
  )

  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    with st.form("login_form"):
      user_input = st.text_input("Usuario")
      pass_input = st.text_input("Contraseña", type="password")
      btn_login = st.form_submit_button(
          "INGRESAR AL SISTEMA", use_container_width=True
      )

      if btn_login:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nombre, rol FROM usuarios WHERE usuario=? AND clave=?",
            (user_input.strip(), pass_input.strip()),
        )
        res = cursor.fetchone()
        conn.close()

        if res:
          st.session_state.logged_in = True
          st.session_state.usuario = user_input.strip()
          st.session_state.nombre = res["nombre"]
          st.session_state.rol = res["rol"]
          st.rerun()
        else:
          st.error("Usuario o contraseña incorrectos")

# ==========================================
# INTERFAZ PRINCIPAL DENTRO DEL SISTEMA
# ==========================================
else:
  st.sidebar.title(f"👤 {st.session_state.nombre}")
  st.sidebar.caption(f"Rol: {st.session_state.rol.upper()}")

  if st.sidebar.button("🔒 Cerrar Sesión", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.carrito = []
    st.rerun()

  st.sidebar.divider()

  # ------------------------------------------
  # VISTA MESERO
  # ------------------------------------------
  if st.session_state.rol == "mesero":
    st.header("📋 Toma de Pedidos - Mesero")
    col_left, col_right = st.columns([2, 1])

    with col_left:
      st.subheader("🍔 Catálogo de Productos")
      conn = get_db()
      cursor = conn.cursor()
      cursor.execute("SELECT * FROM productos")
      productos = cursor.fetchall()
      conn.close()

      cols = st.columns(3)
      for idx, p in enumerate(productos):
        with cols[idx % 3]:
          st.markdown(
              f"### {p['icono']} {p['nombre']}\n**${p['precio']:.2f}**"
          )
          if st.button(
              "Agregar +", key=f"add_{p['id']}", use_container_width=True
          ):
            st.session_state.carrito.append(
                {"nombre": p["nombre"], "precio": p["precio"]}
            )
            st.rerun()

    with col_right:
      st.subheader("🛒 Orden Actual")
      cliente = st.text_input("Nombre de Cliente / Mesa")

      total = 0.0
      for i, item in enumerate(st.session_state.carrito):
        total += item["precio"]
        c1, c2 = st.columns([3, 1])
        c1.write(f"• {item['nombre']} (${item['precio']:.2f})")
        if c2.button("✕", key=f"del_{i}"):
          st.session_state.carrito.pop(i)
          st.rerun()

      st.markdown(f"### TOTAL: :green[${total:.2f}]")

      if st.button(
          "🚀 ENVIAR A COCINA Y CAJA", type="primary", use_container_width=True
      ):
        if not cliente or not st.session_state.carrito:
          st.warning("Ingresa el cliente y agrega al menos un producto.")
        else:
          conn = get_db()
          cursor = conn.cursor()
          fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          cursor.execute(
              "INSERT INTO pedidos (cliente, items, total, mesero, fecha_hora)"
              " VALUES (?, ?, ?, ?, ?)",
              (
                  cliente,
                  json.dumps(st.session_state.carrito),
                  total,
                  st.session_state.nombre,
                  fecha,
              ),
          )
          conn.commit()
          conn.close()

          st.session_state.carrito = []
          st.success("¡Orden registrada con éxito!")
          st.rerun()

  # ------------------------------------------
  # VISTA COCINA
  # ------------------------------------------
  elif st.session_state.rol == "cocina":
    st.header("🔥 Monitor de Cocina - Comandas Pendientes")
    if st.button("🔄 Actualizar Comandas"):
      st.rerun()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM pedidos WHERE estado='pendiente' ORDER BY id ASC"
    )
    pedidos = cursor.fetchall()
    conn.close()

    if not pedidos:
      st.info("No hay comandas pendientes por preparar.")

    cols = st.columns(3)
    for idx, p in enumerate(pedidos):
      items = json.loads(p["items"])
      with cols[idx % 3]:
        with st.container(border=True):
          st.subheader(f"Orden #{p['id']} - {p['cliente']}")
          st.caption(f"Atendido: {p['mesero']} | 🕒 {p['fecha_hora'][11:16]}")
          for it in items:
            st.write(f"• **{it['nombre']}**")
          if st.button(
              "✔ MARCAR LISTO", key=f"ready_{p['id']}", use_container_width=True
          ):
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE pedidos SET estado='preparado' WHERE id=?", (p["id"],)
            )
            conn.commit()
            conn.close()
            st.rerun()

  # ------------------------------------------
  # VISTA CAJA
  # ------------------------------------------
  elif st.session_state.rol == "caja":
    st.header("💰 Panel de Cobros y Caja")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM cajas WHERE cajero=? AND estado='abierta'",
        (st.session_state.nombre,),
    )
    caja_activa = cursor.fetchone()

    c1, c2 = st.columns([2, 1])
    if not caja_activa:
      c1.error("⚠️ CAJA CERRADA")
      with c2:
        monto = st.number_input(
            "Base Inicial ($)", min_value=0.0, value=50.0, step=5.0
        )
        if st.button("🔓 ABRIR CAJA", use_container_width=True):
          fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          cursor.execute(
              "INSERT INTO cajas (cajero, monto_apertura, fecha_apertura,"
              " estado) VALUES (?, ?, ?, 'abierta')",
              (st.session_state.nombre, monto, fecha),
          )
          conn.commit()
          st.success("Caja abierta exitosamente.")
          st.rerun()
    else:
      c1.success(f"🟢 CAJA ABIERTA (Base: ${caja_activa['monto_apertura']:.2f})")
      with c2:
        if st.button("🔒 CERRAR CAJA (ARQUEO)", use_container_width=True):
          cursor.execute(
              "SELECT SUM(total) FROM pedidos WHERE estado='cobrado'"
          )
          ventas = cursor.fetchone()[0] or 0.0
          total_cierre = caja_activa["monto_apertura"] + ventas
          fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

          cursor.execute(
              "UPDATE cajas SET monto_cierre=?, ventas_efectivo=?,"
              " fecha_cierre=?, estado='cerrada' WHERE id=?",
              (total_cierre, ventas, fecha, caja_activa["id"]),
          )
          conn.commit()
          st.info(
              f"Arqueo realizado. Total en caja: ${total_cierre:.2f} (Ventas:"
              f" ${ventas:.2f})"
          )
          st.rerun()

    st.divider()
    cursor.execute(
        "SELECT * FROM pedidos WHERE estado!='cobrado' AND estado!='anulado'"
        " ORDER BY id DESC"
    )
    pedidos_cobro = cursor.fetchall()
    conn.close()

    cols_caja = st.columns(3)
    for idx, p in enumerate(pedidos_cobro):
      with cols_caja[idx % 3]:
        with st.container(border=True):
          st.subheader(f"Orden #{p['id']} - {p['cliente']}")
          st.caption(f"Mesero: {p['mesero']}")
          st.write(
              f"Estado:"
              f" **{p['estado'].upper()}**"
          )
          st.markdown(f"### Total: :green[${p['total']:.2f}]")

          pago = st.number_input(
              f"Efectivo ($)",
              min_value=0.0,
              value=float(p["total"]),
              key=f"pay_{p['id']}",
          )
          if st.button(
              "💵 COBRAR", key=f"btn_pay_{p['id']}", use_container_width=True
          ):
            if pago < p["total"]:
              st.error("Monto insuficiente.")
            else:
              conn = get_db()
              cursor = conn.cursor()
              cursor.execute(
                  "UPDATE pedidos SET estado='cobrado' WHERE id=?", (p["id"],)
              )
              conn.commit()
              conn.close()
              st.success(
                  f"¡Cobrado! Cambio: ${(pago - p['total']):.2f}"
              )
              st.rerun()

  # ------------------------------------------
  # VISTA ADMINISTRADOR
  # ------------------------------------------
  elif st.session_state.rol == "admin":
    st.header("📊 Panel de Administración Global")
    tab1, tab2, tab3 = st.tabs(
        ["📊 Reportes y KPIs", "👥 Personal", "🍔 Menú"]
    )

    with tab1:
      filtro = st.selectbox(
          "📅 Filtrar Reporte por Fecha:",
          ["Hoy", "Ayer", "Últimos 7 días", "Todos los Tiempos"],
      )

      query = "SELECT * FROM pedidos WHERE 1=1"
      params = []
      hoy = datetime.now()

      if filtro == "Hoy":
        query += " AND fecha_hora LIKE ?"
        params.append(f"{hoy.strftime('%Y-%m-%d')}%")
      elif filtro == "Ayer":
        ayer = (hoy - timedelta(days=1)).strftime("%Y-%m-%d")
        query += " AND fecha_hora LIKE ?"
        params.append(f"{ayer}%")
      elif filtro == "Últimos 7 días":
        hace_7 = (hoy - timedelta(days=7)).strftime("%Y-%m-%d")
        query += " AND fecha_hora >= ?"
        params.append(hace_7)

      query += " ORDER BY id DESC"

      conn = get_db()
      df_pedidos = pd.read_sql_query(query, conn, params=params)
      conn.close()

      total_cobrado = (
          df_pedidos[df_pedidos["estado"] == "cobrado"]["total"].sum()
          if not df_pedidos.empty
          else 0.0
      )
      anulados = (
          len(df_pedidos[df_pedidos["estado"] == "anulado"])
          if not df_pedidos.empty
          else 0
      )

      k1, k2, k3 = st.columns(3)
      k1.metric("💵 Ventas Cobradas", f"${total_cobrado:.2f}")
      k2.metric("🚫 Ventas Anuladas", f"{anulados}")
      k3.metric("📦 Total Pedidos", f"{len(df_pedidos)}")

      st.subheader("Historial de Pedidos")
      st.dataframe(df_pedidos, use_container_width=True)

    with tab2:
      st.subheader("Gestión de Personal")
      with st.form("form_user"):
        n_nombre = st.text_input("Nombre Completo")
        n_user = st.text_input("Usuario Login")
        n_pass = st.text_input("Contraseña", type="password")
        n_rol = st.selectbox("Rol", ["mesero", "cocina", "caja", "admin"])
        if st.form_submit_button("💾 Guardar Usuario"):
          if n_nombre and n_user and n_pass:
            conn = get_db()
            cursor = conn.cursor()
            try:
              cursor.execute(
                  "INSERT INTO usuarios (nombre, usuario, clave, rol) VALUES"
                  " (?, ?, ?, ?)",
                  (n_nombre, n_user, n_pass, n_rol),
              )
              conn.commit()
              st.success(f"Usuario '{n_user}' creado.")
            except Exception as e:
              st.error(f"Error: {e}")
            conn.close()

    with tab3:
      st.subheader("Gestión de Menú")
      with st.form("form_prod"):
        p_nom = st.text_input("Nombre Producto")
        p_precio = st.number_input("Precio ($)", min_value=0.1, step=0.5)
        if st.form_submit_button("💾 Guardar Producto"):
          if p_nom:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO productos (nombre, precio) VALUES (?, ?)",
                (p_nom, p_precio),
            )
            conn.commit()
            conn.close()
            st.success("Producto añadido al menú.")
