import json
import os
import sqlite3
from datetime import datetime, timedelta
from PIL import Image
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="FastFood POS Pro", page_icon="⚡", layout="wide"
)


# ==========================================
# BASE DE DATOS Y MIGRACIONES
# ==========================================
def init_db():
  if not os.path.exists("imagenes"):
    os.makedirs("imagenes")

  conn = sqlite3.connect("restaurante.db", check_same_thread=False)
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
  return conn, cursor


conn, cursor = init_db()

# Inicialización de estado de sesión
if "usuario_actual" not in st.session_state:
  st.session_state.usuario_actual = None
  st.session_state.rol_actual = None
  st.session_state.carrito = []

# ==========================================
# LOGIN
# ==========================================
if st.session_state.usuario_actual is None:
  st.title("⚡ FastFood POS Pro")
  st.subheader("Inicio de Sesión por Rol")

  with st.form("login_form"):
    user = st.text_input("Usuario")
    clave = st.text_input("Contraseña", type="password")
    submit = st.form_submit_button("INGRESAR AL SISTEMA")

    if submit:
      cursor.execute(
          "SELECT id, nombre, rol FROM usuarios WHERE usuario=? AND clave=?",
          (user.strip(), clave.strip()),
      )
      res = cursor.fetchone()
      if res:
        st.session_state.usuario_actual = res[1]
        st.session_state.rol_actual = res[2]
        st.rerun()
      else:
        st.error("Usuario o contraseña incorrectos.")

else:
  # Header
  col_t, col_u, col_b = st.columns([3, 2, 1])
  with col_t:
    st.title("⚡ FastFood POS Pro")
  with col_u:
    st.write(
        f"👤 **{st.session_state.usuario_actual}**"
        f" ({st.session_state.rol_actual.upper()})"
    )
  with col_b:
    if st.button("Cerrar Sesión ➔"):
      st.session_state.usuario_actual = None
      st.session_state.rol_actual = None
      st.session_state.carrito = []
      st.rerun()

  st.divider()

  # ==========================================
  # VISTA MESERO
  # ==========================================
  if st.session_state.rol_actual == "mesero":
    col_menu, col_cart = st.columns([2, 1])

    with col_menu:
      st.subheader("Catálogo de Productos")
      cursor.execute(
          "SELECT nombre, precio, icono, imagen_path FROM productos"
      )
      prods = cursor.fetchall()

      cols = st.columns(3)
      for i, (nombre, precio, icono, img_path) in enumerate(prods):
        with cols[i % 3]:
          if img_path and os.path.exists(img_path):
            st.image(img_path, width=100)
          else:
            st.markdown(f"### {icono}")
          st.write(f"**{nombre}**")
          st.write(f"${precio:.2f}")
          if st.button(f"Agregar +", key=f"add_{i}"):
            st.session_state.carrito.append(
                {"nombre": nombre, "precio": precio}
            )
            st.toast(f"Añadido: {nombre}")

    with col_cart:
      st.subheader("Orden del Cliente")
      cliente = st.text_input("Nombre de Cliente / Mesa")

      total = sum(item["precio"] for item in st.session_state.carrito)
      for idx, item in enumerate(st.session_state.carrito):
        c1, c2, c3 = st.columns([2, 1, 1])
        c1.write(item["nombre"])
        c2.write(f"${item['precio']:.2f}")
        if c3.button("✕", key=f"del_{idx}"):
          st.session_state.carrito.pop(idx)
          st.rerun()

      st.markdown(f"### TOTAL: ${total:.2f}")

      if st.button("🚀 ENVIAR A COCINA Y CAJA", type="primary"):
        if not cliente.strip() or not st.session_state.carrito:
          st.warning("Escribe el nombre del cliente y agrega productos.")
        else:
          items_json = json.dumps(st.session_state.carrito)
          fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          cursor.execute(
              "INSERT INTO pedidos (cliente, items, total, mesero, fecha_hora)"
              " VALUES (?, ?, ?, ?, ?)",
              (
                  cliente.strip(),
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

  # ==========================================
  # VISTA COCINA
  # ==========================================
  elif st.session_state.rol_actual == "cocina":
    st.subheader("🔥 Monitor de Cocina - Comandas Pendientes")
    cursor.execute(
        "SELECT id, cliente, items, mesero, fecha_hora FROM pedidos WHERE"
        " estado = 'pendiente'"
    )
    pedidos = cursor.fetchall()

    cols = st.columns(3)
    for i, (p_id, cliente, items_raw, mesero, fh) in enumerate(pedidos):
      with cols[i % 3]:
        with st.container(border=True):
          st.markdown(f"### Orden #{p_id} - {cliente}")
          st.caption(f"📱 Atendido: {mesero} | 🕒 {fh[11:16] if fh else ''}")
          items = json.loads(items_raw)
          for item in items:
            st.write(f"• {item['nombre']}")
          if st.button("✔ MARCAR LISTO", key=f"cocina_{p_id}"):
            cursor.execute(
                "UPDATE pedidos SET estado = 'preparado' WHERE id = ?", (p_id,)
            )
            conn.commit()
            st.rerun()

  # ==========================================
  # VISTA CAJA
  # ==========================================
  elif st.session_state.rol_actual == "caja":
    st.subheader("💰 Panel de Cobros")
    cursor.execute(
        "SELECT id, cliente, items, total, estado, mesero, fecha_hora FROM"
        " pedidos WHERE estado != 'cobrado' AND estado != 'anulado'"
    )
    pedidos = cursor.fetchall()

    cols = st.columns(3)
    for i, (p_id, cliente, items_raw, total, estado, mesero, fh) in enumerate(
        pedidos
    ):
      with cols[i % 3]:
        with st.container(border=True):
          st.markdown(f"### Orden #{p_id} - {cliente}")
          st.caption(f"📱 Mesero: {mesero}")
          st.write(
              "Status:"
              f" **{'¡LISTO!' if estado=='preparado' else 'En preparación'}**"
          )
          st.markdown(f"### Total: ${total:.2f}")

          monto = st.number_input(
              "Efectivo", value=float(total), key=f"pay_{p_id}"
          )
          if st.button("💵 COBRAR", key=f"cobro_{p_id}"):
            if monto < total:
              st.error("Monto insuficiente.")
            else:
              cursor.execute(
                  "UPDATE pedidos SET estado = 'cobrado' WHERE id = ?", (p_id,)
              )
              conn.commit()
              st.success(f"Cobrado con éxito. Cambio: ${monto - total:.2f}")
              st.rerun()

  # ==========================================
  # VISTA ADMIN
  # ==========================================
  elif st.session_state.rol_actual == "admin":
    tab1, tab2, tab3 = st.tabs(
        ["📊 Reportes", "👥 Usuarios & Personal", "🍔 Gestión de Menú"]
    )

    with tab1:
      st.subheader("Reportes de Ventas")
      cursor.execute("SELECT SUM(total) FROM pedidos WHERE estado='cobrado'")
      total_cobrado = cursor.fetchone()[0] or 0.0
      st.metric("Ventas Totales Cobradas", f"${total_cobrado:.2f}")

    with tab2:
      st.subheader("Usuarios Registrados")
      cursor.execute("SELECT id, nombre, usuario, rol FROM usuarios")
      st.dataframe(
          cursor.fetchall(),
          column_config={
              "0": "ID",
              "1": "Nombre",
              "2": "Usuario",
              "3": "Rol",
          },
      )

    with tab3:
      st.subheader("Añadir Nuevo Producto")
      with st.form("add_prod"):
        nom = st.text_input("Nombre del Producto")
        precio = st.number_input("Precio", min_value=0.0, step=0.5)
        btn_prod = st.form_submit_button("Guardar Producto")
        if btn_prod and nom:
          cursor.execute(
              "INSERT INTO productos (nombre, precio) VALUES (?, ?)",
              (nom, precio),
          )
          conn.commit()
          st.success("Producto agregado con éxito.")
