import json
import os
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
from PIL import Image
import streamlit as st

# Configuración visual e inicialización
st.set_page_config(
    page_title="FastFood POS Pro Web",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

os.makedirs("imagenes", exist_ok=True)


# ==========================================
# BASE DE DATOS Y MIGRACIONES
# ==========================================
def get_db():
  conn = sqlite3.connect("restaurante.db", check_same_thread=False)
  conn.row_factory = sqlite3.Row
  return conn


def init_db():
  conn = get_db()
  cursor = conn.cursor()

  # Tabla Usuarios
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

  # Tabla Productos
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

  # Tabla Pedidos
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

  # Tabla Cajas
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
# ESTADO DE SESIÓN Y VARIABLES GLOBALES
# ==========================================
if "logged_in" not in st.session_state:
  st.session_state.logged_in = False
  st.session_state.user_id = None
  st.session_state.usuario = ""
  st.session_state.nombre = ""
  st.session_state.rol = ""
  st.session_state.carrito = []
  st.session_state.user_edit_id = None

# ==========================================
# LOGIN & AUTENTICACIÓN
# ==========================================
if not st.session_state.logged_in:
  col_a, col_b, col_c = st.columns([1, 1.5, 1])
  with col_b:
    st.markdown(
        "<h1 style='text-align: center; color: #10b981;'>⚡ FastFood POS</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: gray;'>Inicio de Sesión por"
        " Rol</p>",
        unsafe_allow_html=True,
    )

    with st.form("form_login"):
      u_input = st.text_input("Usuario")
      p_input = st.text_input("Contraseña", type="password")
      btn_ingresar = st.form_submit_button(
          "INGRESAR AL SISTEMA", use_container_width=True
      )

      if btn_ingresar:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nombre, rol FROM usuarios WHERE usuario=? AND clave=?",
            (u_input.strip(), p_input.strip()),
        )
        res = cursor.fetchone()
        conn.close()

        if res:
          st.session_state.logged_in = True
          st.session_state.user_id = res["id"]
          st.session_state.usuario = u_input.strip()
          st.session_state.nombre = res["nombre"]
          st.session_state.rol = res["rol"]
          st.rerun()
        else:
          st.error("Usuario o contraseña incorrectos.")

# ==========================================
# INTERFAZ DENTRO DEL SISTEMA POR ROL
# ==========================================
else:
  # Header
  c_head1, c_head2 = st.columns([4, 1])
  with c_head1:
    st.markdown(
        f"### ⚡ FastFood POS Pro — <span style='color:#10b981;'>👤"
        f" {st.session_state.nombre} ({st.session_state.rol.upper()})</span>",
        unsafe_allow_html=True,
    )
  with c_head2:
    if st.button("Cerrar Sesión ➔", type="secondary", use_container_width=True):
      st.session_state.logged_in = False
      st.session_state.carrito = []
      st.rerun()

  st.divider()

  # ------------------------------------------
  # 1. VISTA MESERO
  # ------------------------------------------
  if st.session_state.rol == "mesero":
    col_cat, col_ord = st.columns([2.2, 1])

    with col_cat:
      st.subheader("Catálogo de Productos")
      conn = get_db()
      cursor = conn.cursor()
      cursor.execute("SELECT * FROM productos ORDER BY id DESC")
      prods = cursor.fetchall()
      conn.close()

      cols = st.columns(3)
      for idx, p in enumerate(prods):
        with cols[idx % 3]:
          with st.container(border=True):
            if p["imagen_path"] and os.path.exists(p["imagen_path"]):
              st.image(p["imagen_path"], use_container_width=True)
            else:
              st.markdown(
                  f"<h1 style='text-align: center;'>{p['icono']}</h1>",
                  unsafe_allow_html=True,
              )

            st.markdown(f"**{p['nombre']}**")
            st.markdown(
                f"<span style='color:#10b981;"
                f" font-weight:bold;'>${p['precio']:.2f}</span>",
                unsafe_allow_html=True,
            )
            if st.button(
                "Agregar +", key=f"add_cart_{p['id']}", use_container_width=True
            ):
              st.session_state.carrito.append(
                  {"nombre": p["nombre"], "precio": p["precio"]}
              )
              st.rerun()

    with col_ord:
      st.subheader("Orden del Cliente")
      cliente = st.text_input(
          "Nombre de Cliente / Mesa", key="input_cliente_mesero"
      )

      total = 0.0
      for idx, item in enumerate(st.session_state.carrito):
        total += item["precio"]
        ci1, ci2 = st.columns([3, 1])
        ci1.write(f"{item['nombre']} — **${item['precio']:.2f}**")
        if ci2.button("✕", key=f"del_cart_{idx}"):
          st.session_state.carrito.pop(idx)
          st.rerun()

      st.markdown(
          f"### TOTAL: <span style='color:#10b981;'>${total:.2f}</span>",
          unsafe_allow_html=True,
      )

      if st.button(
          "🚀 ENVIAR A COCINA Y CAJA", type="primary", use_container_width=True
      ):
        if not cliente.strip() or not st.session_state.carrito:
          st.warning("Escribe el nombre del cliente y agrega productos.")
        else:
          conn = get_db()
          cursor = conn.cursor()
          fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          cursor.execute(
              "INSERT INTO pedidos (cliente, items, total, mesero, fecha_hora)"
              " VALUES (?, ?, ?, ?, ?)",
              (
                  cliente.strip(),
                  json.dumps(st.session_state.carrito),
                  total,
                  st.session_state.nombre,
                  fecha_actual,
              ),
          )
          conn.commit()
          conn.close()

          st.session_state.carrito = []
          st.success("¡Orden registrada correctamente!")
          st.rerun()

  # ------------------------------------------
  # 2. VISTA COCINA
  # ------------------------------------------
  elif st.session_state.rol == "cocina":
    st.markdown(
        "<h3 style='color:#f97316;'>🔥 Monitor de Cocina - Comandas"
        " Pendientes</h3>",
        unsafe_allow_html=True,
    )
    if st.button("🔄 Refrescar Comandas"):
      st.rerun()

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, cliente, items, mesero, fecha_hora FROM pedidos WHERE"
        " estado='pendiente' ORDER BY id ASC"
    )
    pedidos = cursor.fetchall()
    conn.close()

    cols_cocina = st.columns(3)
    for idx, (p_id, cliente, items_raw, mesero, fh) in enumerate(pedidos):
      items = json.loads(items_raw)
      hora = fh[11:16] if fh else ""
      with cols_cocina[idx % 3]:
        with st.container(border=True):
          st.markdown(
              f"<h4 style='color:#f97316; margin:0;'>Orden #{p_id} -"
              f" {cliente}</h4>",
              unsafe_allow_html=True,
          )
          st.caption(f"📱 Atendido: {mesero} | 🕒 {hora}")

          for it in items:
            st.write(f"• {it['nombre']}")

          if st.button(
              "✔ MARCAR LISTO", key=f"ready_coc_{p_id}", use_container_width=True
          ):
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE pedidos SET estado='preparado' WHERE id=?", (p_id,)
            )
            conn.commit()
            conn.close()
            st.rerun()

  # ------------------------------------------
  # 3. VISTA CAJA
  # ------------------------------------------
  elif st.session_state.rol == "caja":
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, monto_apertura FROM cajas WHERE cajero=? AND"
        " estado='abierta'",
        (st.session_state.nombre,),
    )
    caja_abierta = cursor.fetchone()

    cb_left, cb_right = st.columns([3, 1])
    if not caja_abierta:
      cb_left.markdown(
          "<h4 style='color:#ef4444;'>⚠️ CAJA CERRADA</h4>",
          unsafe_allow_html=True,
      )
      with cb_right:
        monto_base = st.number_input(
            "Base dinero en caja ($):", min_value=0.0, value=0.0, step=5.0
        )
        if st.button("🔓 ABRIR CAJA", use_container_width=True):
          fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
          cursor.execute(
              "INSERT INTO cajas (cajero, monto_apertura, fecha_apertura,"
              " estado) VALUES (?, ?, ?, 'abierta')",
              (st.session_state.nombre, monto_base, fecha),
          )
          conn.commit()
          st.success(f"Caja abierta con base de ${monto_base:.2f}")
          st.rerun()
    else:
      cb_left.markdown(
          f"<h4 style='color:#10b981;'>🟢 CAJA ABIERTA (Base:"
          f" ${caja_abierta['monto_apertura']:.2f})</h4>",
          unsafe_allow_html=True,
      )
      with cb_right:
        if st.button("🔒 CERRAR CAJA (ARQUEO)", use_container_width=True):
          cursor.execute(
              "SELECT SUM(total) FROM pedidos WHERE estado='cobrado'"
          )
          total_ventas = cursor.fetchone()[0] or 0.0
          base = caja_abierta["monto_apertura"]
          esperado = base + total_ventas
          fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

          cursor.execute(
              "UPDATE cajas SET monto_cierre=?, ventas_efectivo=?,"
              " fecha_cierre=?, estado='cerrada' WHERE id=?",
              (esperado, total_ventas, fecha, caja_abierta["id"]),
          )
          conn.commit()
          st.info(
              f"📊 RESUMEN DE CIERRE:\n\n• Base Inicial: ${base:.2f}\n• Ventas"
              f" Cobradas: ${total_ventas:.2f}\n• TOTAL ESPERADO: ${esperado:.2f}"
          )
          st.rerun()

    st.markdown(
        "<h3 style='color:#38bdf8;'>💰 Panel de Cobros</h3>",
        unsafe_allow_html=True,
    )

    cursor.execute(
        "SELECT id, cliente, items, total, estado, mesero, fecha_hora FROM"
        " pedidos WHERE estado!='cobrado' AND estado!='anulado' ORDER BY id"
        " DESC"
    )
    pedidos_caja = cursor.fetchall()

    cols_caja = st.columns(3)
    for idx, (p_id, cliente, items_raw, total, estado, mesero, fh) in enumerate(
        pedidos_caja
    ):
      hora = fh[11:16] if fh else ""
      with cols_caja[idx % 3]:
        with st.container(border=True):
          st.markdown(
              f"<h4 style='color:#38bdf8; margin:0;'>Orden #{p_id} -"
              f" {cliente}</h4>",
              unsafe_allow_html=True,
          )
          st.caption(f"📱 Mesero: {mesero} | 🕒 {hora}")

          badge_txt = (
              "¡LISTO PARA ENTREGAR!"
              if estado == "preparado"
              else "En preparación"
          )
          badge_col = "#10b981" if estado == "preparado" else "#eab308"
          st.markdown(
              f"<span style='color:{badge_col};"
              f" font-weight:bold;'>{badge_txt}</span>",
              unsafe_allow_html=True,
          )

          # Opción Añadir Adicional
          with st.expander("➕ Añadir Adicional"):
            cursor.execute("SELECT id, nombre, precio FROM productos")
            prods_add = cursor.fetchall()
            dict_prods = {
                f"{pr['nombre']} - ${pr['precio']:.2f}": pr for pr in prods_add
            }
            if dict_prods:
              p_sel = st.selectbox(
                  "Producto", list(dict_prods.keys()), key=f"sel_add_{p_id}"
              )
              if st.button("Agregar a Cuenta", key=f"btn_add_exp_{p_id}"):
                prod_obj = dict_prods[p_sel]
                items_l = json.loads(items_raw)
                items_l.append(
                    {"nombre": prod_obj["nombre"], "precio": prod_obj["precio"]}
                )
                nuevo_total = total + prod_obj["precio"]

                cursor.execute(
                    "UPDATE pedidos SET items=?, total=? WHERE id=?",
                    (json.dumps(items_l), nuevo_total, p_id),
                )
                conn.commit()
                st.success("Item añadido.")
                st.rerun()

          st.markdown(
              f"<h3 style='color:#10b981;'>Total: ${total:.2f}</h3>",
              unsafe_allow_html=True,
          )

          monto_pagado = st.number_input(
              f"Efectivo entregado ($):",
              min_value=0.0,
              value=float(total),
              key=f"pay_val_{p_id}",
          )
          if st.button(
              "💵 COBRAR", key=f"btn_cobrar_{p_id}", use_container_width=True
          ):
            if monto_pagado < total:
              st.error(f"Monto insuficiente. Total: ${total:.2f}")
            else:
              cursor.execute(
                  "UPDATE pedidos SET estado='cobrado' WHERE id=?", (p_id,)
              )
              conn.commit()
              cambio = monto_pagado - total
              st.success(
                  f"¡Cobro Exitoso!\nTotal: ${total:.2f} | Cambio:"
                  f" ${cambio:.2f}"
              )
              st.rerun()

    conn.close()

  # ------------------------------------------
  # 4. VISTA ADMINISTRADOR
  # ------------------------------------------
  elif st.session_state.rol == "admin":
    st.subheader("📊 Panel Administrador")
    tab_rep, tab_usr, tab_men = st.tabs(
        ["📊 Reportes", "👥 Usuarios & Personal", "🍔 Gestión de Menú"]
    )

    # Pestana 1: Reportes
    with tab_rep:
      st.markdown("##### 📅 Filtrar Reporte por Fecha:")
      filtro_f = st.selectbox(
          "Selecciona rango:",
          ["Hoy", "Ayer", "Últimos 7 días", "Todos los Tiempos"],
          label_visibility="collapsed",
      )

      hoy = datetime.now()
      filtro_sql = ""
      params = []

      if filtro_f == "Hoy":
        filtro_sql = "WHERE fecha_hora LIKE ?"
        params.append(f"{hoy.strftime('%Y-%m-%d')}%")
      elif filtro_f == "Ayer":
        ayer = (hoy - timedelta(days=1)).strftime("%Y-%m-%d")
        filtro_sql = "WHERE fecha_hora LIKE ?"
        params.append(f"{ayer}%")
      elif filtro_f == "Últimos 7 días":
        hace_7 = (hoy - timedelta(days=7)).strftime("%Y-%m-%d")
        filtro_sql = "WHERE fecha_hora >= ?"
        params.append(hace_7)

      conn = get_db()
      cursor = conn.cursor()

      # KPIs
      and_cobrado = (
          "AND estado='cobrado'" if filtro_sql else "WHERE estado='cobrado'"
      )
      cursor.execute(
          f"SELECT SUM(total) FROM pedidos {filtro_sql} {and_cobrado}", params
      )
      total_cobrado = cursor.fetchone()[0] or 0.0

      and_anulado = (
          "AND estado='anulado'" if filtro_sql else "WHERE estado='anulado'"
      )
      cursor.execute(
          f"SELECT COUNT(*), SUM(total) FROM pedidos {filtro_sql}"
          f" {and_anulado}",
          params,
      )
      res_anulados = cursor.fetchone()
      cant_anuladas = res_anulados[0] or 0
      monto_anulado = res_anulados[1] or 0.0

      cursor.execute(f"SELECT COUNT(*) FROM pedidos {filtro_sql}", params)
      total_pedidos = cursor.fetchone()[0] or 0

      k1, k2, k3 = st.columns(3)
      k1.metric("💵 Ventas Cobradas", f"${total_cobrado:.2f}")
      k2.metric("🚫 Ventas Anuladas", f"{cant_anuladas} (${monto_anulado:.2f})")
      k3.metric("📦 Total Pedidos", f"{total_pedidos}")

      st.markdown("##### 📋 Historial General de Órdenes")
      cursor.execute(
          f"SELECT id, fecha_hora, mesero, cliente, items, total, estado FROM"
          f" pedidos {filtro_sql} ORDER BY id DESC",
          params,
      )
      pedidos_hist = cursor.fetchall()

      for p_id, fh, mesero, cliente, items_raw, total, estado in pedidos_hist:
        it_list = json.loads(items_raw)
        resumen_items = ", ".join([i["nombre"] for i in it_list])

        ch1, ch2, ch3, ch4, ch5, ch6, ch7, ch8 = st.columns(
            [0.5, 1.5, 1.2, 1.2, 2.2, 1, 1, 1]
        )
        ch1.write(f"#{p_id}")
        ch2.write(fh if fh else "N/A")
        ch3.write(mesero)
        ch4.write(cliente)
        ch5.write(resumen_items)
        ch6.write(f"${total:.2f}")

        col_est = "#10b981" if estado == "cobrado" else "#38bdf8"
        if estado == "anulado":
          col_est = "#ef4444"
        ch7.markdown(
            f"<span style='color:{col_est};"
            f" font-weight:bold;'>{estado.upper()}</span>",
            unsafe_allow_html=True,
        )

        if estado != "anulado":
          if ch8.button("🚫 Anular", key=f"anular_{p_id}"):
            cursor.execute(
                "UPDATE pedidos SET estado='anulado' WHERE id=?", (p_id,)
            )
            conn.commit()
            st.rerun()

      conn.close()

    # Pestana 2: Usuarios
    with tab_usr:
      col_uf, col_ut = st.columns([1, 2])

      with col_uf:
        if st.session_state.user_edit_id:
          st.markdown("##### ✏ Editando Usuario")
          conn = get_db()
          cursor = conn.cursor()
          cursor.execute(
              "SELECT nombre, usuario, clave, rol FROM usuarios WHERE id=?",
              (st.session_state.user_edit_id,),
          )
          u_data = cursor.fetchone()
          conn.close()

          def_nom = u_data["nombre"] if u_data else ""
          def_usr = u_data["usuario"] if u_data else ""
          def_pas = u_data["clave"] if u_data else ""
          def_rol = u_data["rol"] if u_data else "mesero"
        else:
          st.markdown("##### ➕ Registrar / Editar Usuario")
          def_nom, def_usr, def_pas, def_rol = "", "", "", "mesero"

        with st.form("form_gestion_usuario"):
          unombre = st.text_input("Nombre Completo", value=def_nom)
          uuser = st.text_input("Nombre de Usuario (Login)", value=def_usr)
          uclave = st.text_input("Contraseña", value=def_pas, type="password")
          urol = st.selectbox(
              "Rol / Cargo:",
              ["mesero", "cocina", "caja", "admin"],
              index=["mesero", "cocina", "caja", "admin"].index(def_rol),
          )

          btn_txt = (
              "💾 ACTUALIZAR DATOS"
              if st.session_state.user_edit_id
              else "💾 GUARDAR USUARIO"
          )
          btn_g_u = st.form_submit_button(btn_txt, use_container_width=True)

          if btn_g_u:
            if not unombre or not uuser or not uclave:
              st.warning("Por favor completa todos los campos.")
            else:
              conn = get_db()
              cursor = conn.cursor()
              try:
                if st.session_state.user_edit_id:
                  cursor.execute(
                      "UPDATE usuarios SET nombre=?, usuario=?, clave=?,"
                      " rol=? WHERE id=?",
                      (
                          unombre,
                          uuser,
                          uclave,
                          urol,
                          st.session_state.user_edit_id,
                      ),
                  )
                  st.success("Usuario actualizado correctamente.")
                  st.session_state.user_edit_id = None
                else:
                  cursor.execute(
                      "INSERT INTO usuarios (nombre, usuario, clave, rol)"
                      " VALUES (?, ?, ?, ?)",
                      (unombre, uuser, uclave, urol),
                  )
                  st.success(f"Usuario '{uuser}' creado exitosamente.")
                conn.commit()
                conn.close()
                st.rerun()
              except sqlite3.IntegrityError:
                st.error(f"El nombre de usuario '{uuser}' ya existe.")
                conn.close()

        if st.session_state.user_edit_id:
          if st.button("✕ Cancelar Edición", use_container_width=True):
            st.session_state.user_edit_id = None
            st.rerun()

      with col_ut:
        st.markdown("##### 👥 Personal Registrado en el Sistema")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, usuario, clave, rol FROM usuarios")
        usuarios_lista = cursor.fetchall()
        conn.close()

        for u_id, nombre, user, clave, rol in usuarios_lista:
          cu1, cu2, cu3, cu4, cu5 = st.columns([2, 1.5, 1.2, 1, 1])
          cu1.write(nombre)
          cu2.write(user)

          col_r = "#10b981" if rol == "mesero" else "#38bdf8"
          if rol == "cocina":
            col_r = "#f97316"
          elif rol == "admin":
            col_r = "#a855f7"
          cu3.markdown(
              f"<span style='color:{col_r};"
              f" font-weight:bold;'>{rol.upper()}</span>",
              unsafe_allow_html=True,
          )

          if cu4.button("✏ Editar", key=f"edit_u_{u_id}"):
            st.session_state.user_edit_id = u_id
            st.rerun()

          if u_id != st.session_state.user_id:
            if cu5.button("🗑 Eliminar", key=f"del_u_{u_id}"):
              conn = get_db()
              cursor = conn.cursor()
              cursor.execute("DELETE FROM usuarios WHERE id=?", (u_id,))
              conn.commit()
              conn.close()
              st.rerun()

    # Pestana 3: Menú
    with tab_men:
      col_mf, col_mt = st.columns([1, 2])

      with col_mf:
        st.markdown("##### ➕ Registrar Nuevo Producto")
        with st.form("form_nuevo_prod", clear_on_submit=True):
          p_nombre = st.text_input("Nombre del Producto")
          p_precio_str = st.text_input("Precio (ej: 4.50)")
          p_img = st.file_uploader(
              "📷 Seleccionar Imagen", type=["png", "jpg", "jpeg", "webp"]
          )
          btn_g_p = st.form_submit_button(
              "💾 GUARDAR EN EL MENÚ", use_container_width=True
          )

          if btn_g_p:
            if not p_nombre or not p_precio_str:
              st.warning("Ingresa el nombre y el precio.")
            else:
              try:
                precio_val = float(p_precio_str)
                dest_path = ""

                if p_img is not None:
                  ext = os.path.splitext(p_img.name)[1]
                  nom_limpio = "".join(
                      c for c in p_nombre if c.isalnum() or c in (" ", "_")
                  ).rstrip()
                  filename = f"prod_{nom_limpio.replace(' ', '_')}{ext}"
                  dest_path = os.path.join("imagenes", filename)

                  image = Image.open(p_img)
                  image.convert("RGB").save(dest_path)

                conn = get_db()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO productos (nombre, precio, categoria, icono,"
                    " imagen_path) VALUES (?, ?, ?, ?, ?)",
                    (p_nombre, precio_val, "General", "🍔", dest_path),
                )
                conn.commit()
                conn.close()

                st.success(f"¡Producto '{p_nombre}' guardado con éxito!")
                st.rerun()
              except ValueError:
                st.error("El precio debe ser un número válido (ej: 5.00).")

      with col_mt:
        st.markdown("##### 📋 Productos en el Menú Actual")
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nombre, precio, imagen_path FROM productos ORDER BY id"
            " DESC"
        )
        prods_lista = cursor.fetchall()
        conn.close()

        for p_id, nombre, precio, img_path in prods_lista:
          cm1, cm2, cm3, cm4 = st.columns([1, 3, 1.5, 1])

          with cm1:
            if img_path and os.path.exists(img_path):
              st.image(img_path, width=40)
            else:
              st.write("🍔")

          cm2.write(f"**{nombre}**")
          cm3.markdown(
              f"<span style='color:#10b981;"
              f" font-weight:bold;'>${precio:.2f}</span>",
              unsafe_allow_html=True,
          )

          if cm4.button("🗑 Eliminar", key=f"del_prod_{p_id}"):
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM productos WHERE id=?", (p_id,))
            conn.commit()
            conn.close()
            st.rerun()
