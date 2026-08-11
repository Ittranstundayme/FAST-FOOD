import json
import os
import sqlite3
from datetime import datetime, timedelta
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image

# Configuración visual
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class SistemaPOSPro(ctk.CTk):

  def __init__(self):
    super().__init__()

    self.title("⚡ FastFood POS Pro - Sistema de Control")
    self.geometry("1220x820")

    self.init_db()

    self.usuario_actual = None
    self.rol_actual = None
    self.user_id_actual = None
    self.carrito = []
    self.ruta_imagen_seleccionada = None
    self.usuario_id_edicion = None

    self.mostrar_login()

  # ==========================================
  # BASE DE DATOS Y MIGRACIONES
  # ==========================================
  def init_db(self):
    if not os.path.exists("imagenes"):
      os.makedirs("imagenes")

    self.conn = sqlite3.connect("restaurante.db")
    self.cursor = self.conn.cursor()

    # Tabla Usuarios
    self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                clave TEXT NOT NULL,
                nombre TEXT NOT NULL,
                rol TEXT NOT NULL
            )
        """)

    self.cursor.execute("SELECT COUNT(*) FROM usuarios")
    if self.cursor.fetchone()[0] == 0:
      usuarios_base = [
          ("mesero1", "1234", "Carlos Gómez", "mesero"),
          ("cocina1", "1234", "Chef Mario", "cocina"),
          ("caja1", "1234", "Ana Cajera", "caja"),
          ("admin", "admin", "Administrador", "admin"),
      ]
      self.cursor.executemany(
          "INSERT INTO usuarios (usuario, clave, nombre, rol) VALUES (?, ?,"
          " ?, ?)",
          usuarios_base,
      )

    # Tabla Productos
    self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                precio REAL NOT NULL,
                categoria TEXT DEFAULT 'General',
                icono TEXT DEFAULT '🍔',
                imagen_path TEXT DEFAULT ''
            )
        """)

    # Tabla Pedidos (Incluye fecha_hora)
    self.cursor.execute("""
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

    # Tabla Cajas (Apertura y Cierre)
    self.cursor.execute("""
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

    # Migraciones/Autorreparación de columnas
    try:
      self.cursor.execute(
          "ALTER TABLE productos ADD COLUMN imagen_path TEXT DEFAULT ''"
      )
    except sqlite3.OperationalError:
      pass

    try:
      self.cursor.execute(
          "ALTER TABLE productos ADD COLUMN categoria TEXT DEFAULT 'General'"
      )
    except sqlite3.OperationalError:
      pass

    try:
      self.cursor.execute(
          "ALTER TABLE pedidos ADD COLUMN fecha_hora TEXT DEFAULT ''"
      )
    except sqlite3.OperationalError:
      pass

    self.conn.commit()

  # ==========================================
  # LOGIN & AUTENTICACIÓN
  # ==========================================
  def mostrar_login(self):
    for widget in self.winfo_children():
      widget.destroy()

    frame_login = ctk.CTkFrame(self, corner_radius=15, width=400, height=450)
    frame_login.place(relx=0.5, rely=0.5, anchor="center")

    ctk.CTkLabel(
        frame_login,
        text="⚡ FastFood POS",
        font=ctk.CTkFont(size=26, weight="bold"),
        text_color="#10b981",
    ).pack(pady=(30, 5))
    ctk.CTkLabel(
        frame_login,
        text="Inicio de Sesión por Rol",
        font=ctk.CTkFont(size=14),
        text_color="gray",
    ).pack(pady=(0, 20))

    self.entry_user = ctk.CTkEntry(
        frame_login,
        placeholder_text="Usuario",
        width=280,
        height=45,
        corner_radius=10,
    )
    self.entry_user.pack(pady=10)

    self.entry_pass = ctk.CTkEntry(
        frame_login,
        placeholder_text="Contraseña",
        show="*",
        width=280,
        height=45,
        corner_radius=10,
    )
    self.entry_pass.pack(pady=10)

    btn_login = ctk.CTkButton(
        frame_login,
        text="INGRESAR AL SISTEMA",
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color="#10b981",
        hover_color="#059669",
        width=280,
        height=45,
        corner_radius=10,
        command=self.validar_login,
    )
    btn_login.pack(pady=25)

  def validar_login(self):
    user = self.entry_user.get().strip()
    clave = self.entry_pass.get().strip()

    self.cursor.execute(
        "SELECT id, nombre, rol FROM usuarios WHERE usuario=? AND clave=?",
        (user, clave),
    )
    res = self.cursor.fetchone()

    if res:
      self.user_id_actual = res[0]
      self.usuario_actual = res[1]
      self.rol_actual = res[2]
      self.construir_interfaz_principal()
    else:
      messagebox.showerror("Error", "Usuario o contraseña incorrectos.")

  def construir_interfaz_principal(self):
    for widget in self.winfo_children():
      widget.destroy()

    header = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#1e293b")
    header.pack(fill="x", side="top")

    ctk.CTkLabel(
        header,
        text="⚡ FastFood POS Pro",
        font=ctk.CTkFont(size=20, weight="bold"),
        text_color="#10b981",
    ).pack(side="left", padx=20)

    btn_logout = ctk.CTkButton(
        header,
        text="Cerrar Sesión ➔",
        width=110,
        height=32,
        fg_color="#ef4444",
        hover_color="#dc2626",
        command=self.mostrar_login,
    )
    btn_logout.pack(side="right", padx=20)

    ctk.CTkLabel(
        header,
        text=f"👤 {self.usuario_actual} ({self.rol_actual.upper()})",
        font=ctk.CTkFont(size=14, weight="bold"),
        text_color="white",
    ).pack(side="right", padx=15)

    self.main_container = ctk.CTkFrame(self, fg_color="#0f172a")
    self.main_container.pack(fill="both", expand=True, padx=15, pady=15)

    if self.rol_actual == "mesero":
      self.vista_mesero()
    elif self.rol_actual == "cocina":
      self.vista_cocina()
    elif self.rol_actual == "caja":
      self.vista_caja()
    elif self.rol_actual == "admin":
      self.vista_admin_con_pestanas()

  # ==========================================
  # VISTA ADMINISTRADOR (CON FILTRO DE FECHAS)
  # ==========================================
  def vista_admin_con_pestanas(self):
    def al_cambiar_pestana(pestana_seleccionada):
      if pestana_seleccionada == "📊 Reportes":
        self.actualizar_reportes()
      elif pestana_seleccionada == "👥 Usuarios & Personal":
        self.actualizar_tabla_usuarios()
      elif pestana_seleccionada == "🍔 Gestión de Menú":
        self.actualizar_lista_menu_admin()

    self.tabview_admin = ctk.CTkTabview(
        self.main_container, command=al_cambiar_pestana
    )
    self.tabview_admin.pack(fill="both", expand=True)

    self.tabview_admin.add("📊 Reportes")
    self.tabview_admin.add("👥 Usuarios & Personal")
    self.tabview_admin.add("🍔 Gestión de Menú")

    self.scroll_reportes = ctk.CTkScrollableFrame(
        self.tabview_admin.tab("📊 Reportes"), fg_color="transparent"
    )
    self.scroll_reportes.pack(fill="both", expand=True)

    self.container_usuarios = ctk.CTkFrame(
        self.tabview_admin.tab("👥 Usuarios & Personal"), fg_color="transparent"
    )
    self.container_usuarios.pack(fill="both", expand=True)

    self.container_menu_admin = ctk.CTkFrame(
        self.tabview_admin.tab("🍔 Gestión de Menú"), fg_color="transparent"
    )
    self.container_menu_admin.pack(fill="both", expand=True)

    self.vista_reportes()
    self.vista_gestion_usuarios()
    self.vista_gestion_menu()

  # ==========================================
  # 📊 REPORTE GENERAL Y FILTRADO POR FECHA
  # ==========================================
  def vista_reportes(self):
    for w in self.scroll_reportes.winfo_children():
      w.destroy()

    filter_frame = ctk.CTkFrame(self.scroll_reportes, fg_color="#1e293b")
    filter_frame.pack(fill="x", pady=(0, 15), padx=5)

    ctk.CTkLabel(
        filter_frame,
        text="📅 Filtrar Reporte por Fecha:",
        font=ctk.CTkFont(size=14, weight="bold"),
    ).pack(side="left", padx=15, pady=10)

    self.combo_filtro_fecha = ctk.CTkOptionMenu(
        filter_frame,
        values=["Hoy", "Ayer", "Últimos 7 días", "Todos los Tiempos"],
        command=lambda _: self.actualizar_reportes(),
    )
    self.combo_filtro_fecha.pack(side="left", padx=10, pady=10)

    kpi_frame = ctk.CTkFrame(self.scroll_reportes, fg_color="transparent")
    kpi_frame.pack(fill="x", pady=(0, 20))

    self.card_caja = ctk.CTkFrame(
        kpi_frame, fg_color="#1e293b", border_width=1, border_color="#10b981"
    )
    self.card_caja.pack(side="left", fill="both", expand=True, padx=5)
    ctk.CTkLabel(
        self.card_caja, text="💵 Ventas Cobradas", font=ctk.CTkFont(size=14)
    ).pack(pady=(15, 5))
    self.lbl_kpi_caja = ctk.CTkLabel(
        self.card_caja,
        text="$0.00",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color="#10b981",
    )
    self.lbl_kpi_caja.pack(pady=(0, 15))

    self.card_anuladas = ctk.CTkFrame(
        kpi_frame, fg_color="#1e293b", border_width=1, border_color="#ef4444"
    )
    self.card_anuladas.pack(side="left", fill="both", expand=True, padx=5)
    ctk.CTkLabel(
        self.card_anuladas, text="🚫 Ventas Anuladas", font=ctk.CTkFont(size=14)
    ).pack(pady=(15, 5))
    self.lbl_kpi_anuladas = ctk.CTkLabel(
        self.card_anuladas,
        text="0 ($0.00)",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color="#ef4444",
    )
    self.lbl_kpi_anuladas.pack(pady=(0, 15))

    self.card_ordenes = ctk.CTkFrame(
        kpi_frame, fg_color="#1e293b", border_width=1, border_color="#38bdf8"
    )
    self.card_ordenes.pack(side="left", fill="both", expand=True, padx=5)
    ctk.CTkLabel(
        self.card_ordenes, text="📦 Total Pedidos", font=ctk.CTkFont(size=14)
    ).pack(pady=(15, 5))
    self.lbl_kpi_ordenes = ctk.CTkLabel(
        self.card_ordenes,
        text="0",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color="#38bdf8",
    )
    self.lbl_kpi_ordenes.pack(pady=(0, 15))

    ctk.CTkLabel(
        self.scroll_reportes,
        text="📋 Historial General de Órdenes",
        font=ctk.CTkFont(size=16, weight="bold"),
    ).pack(anchor="w", pady=(10, 10))
    self.frame_tabla_pedidos = ctk.CTkFrame(
        self.scroll_reportes, fg_color="#1e293b"
    )
    self.frame_tabla_pedidos.pack(fill="both", expand=True)

    self.actualizar_reportes()

  def obtener_query_filtro_fecha(self):
    opcion = self.combo_filtro_fecha.get()
    hoy = datetime.now()

    if opcion == "Hoy":
      fecha_str = hoy.strftime("%Y-%m-%d")
      return f"WHERE fecha_hora LIKE '{fecha_str}%'"
    elif opcion == "Ayer":
      ayer_str = (hoy - timedelta(days=1)).strftime("%Y-%m-%d")
      return f"WHERE fecha_hora LIKE '{ayer_str}%'"
    elif opcion == "Últimos 7 días":
      hace_7 = (hoy - timedelta(days=7)).strftime("%Y-%m-%d")
      return f"WHERE fecha_hora >= '{hace_7}'"
    else:
      return ""

  def actualizar_reportes(self):
    filtro_sql = self.obtener_query_filtro_fecha()

    and_cobrado = (
        "AND estado='cobrado'" if filtro_sql else "WHERE estado='cobrado'"
    )
    self.cursor.execute(
        f"SELECT SUM(total) FROM pedidos {filtro_sql} {and_cobrado}"
    )
    total_cobrado = self.cursor.fetchone()[0] or 0.0
    self.lbl_kpi_caja.configure(text=f"${total_cobrado:.2f}")

    and_anulado = (
        "AND estado='anulado'" if filtro_sql else "WHERE estado='anulado'"
    )
    self.cursor.execute(
        f"SELECT COUNT(*), SUM(total) FROM pedidos {filtro_sql} {and_anulado}"
    )
    res_anuladas = self.cursor.fetchone()
    cant_anuladas = res_anuladas[0] or 0
    monto_anulado = res_anuladas[1] or 0.0
    self.lbl_kpi_anuladas.configure(
        text=f"{cant_anuladas} (${monto_anulado:.2f})"
    )

    self.cursor.execute(f"SELECT COUNT(*) FROM pedidos {filtro_sql}")
    total_pedidos = self.cursor.fetchone()[0] or 0
    self.lbl_kpi_ordenes.configure(text=str(total_pedidos))

    for w in self.frame_tabla_pedidos.winfo_children():
      w.destroy()

    header_row = ctk.CTkFrame(self.frame_tabla_pedidos, fg_color="#334155")
    header_row.pack(fill="x", padx=5, pady=5)

    ctk.CTkLabel(
        header_row,
        text="ID",
        width=35,
        font=ctk.CTkFont(weight="bold"),
        anchor="w",
    ).pack(side="left", padx=5)
    ctk.CTkLabel(
        header_row,
        text="Fecha y Hora",
        width=130,
        font=ctk.CTkFont(weight="bold"),
        anchor="w",
    ).pack(side="left", padx=5)
    ctk.CTkLabel(
        header_row,
        text="Mesero",
        width=120,
        font=ctk.CTkFont(weight="bold"),
        anchor="w",
    ).pack(side="left", padx=5)
    ctk.CTkLabel(
        header_row,
        text="Cliente",
        width=110,
        font=ctk.CTkFont(weight="bold"),
        anchor="w",
    ).pack(side="left", padx=5)
    ctk.CTkLabel(
        header_row,
        text="Detalle",
        width=220,
        font=ctk.CTkFont(weight="bold"),
        anchor="w",
    ).pack(side="left", padx=5)
    ctk.CTkLabel(
        header_row,
        text="Total",
        width=70,
        font=ctk.CTkFont(weight="bold"),
        anchor="w",
    ).pack(side="left", padx=5)
    ctk.CTkLabel(
        header_row,
        text="Estado",
        width=90,
        font=ctk.CTkFont(weight="bold"),
        anchor="w",
    ).pack(side="left", padx=5)
    ctk.CTkLabel(
        header_row,
        text="Acción",
        width=80,
        font=ctk.CTkFont(weight="bold"),
        anchor="w",
    ).pack(side="left", padx=5)

    self.cursor.execute(
        f"SELECT id, cliente, items, total, estado, mesero, fecha_hora FROM"
        f" pedidos {filtro_sql} ORDER BY id DESC"
    )
    for p_id, cliente, items_raw, total, estado, mesero, fh in (
        self.cursor.fetchall()
    ):
      f_row = ctk.CTkFrame(self.frame_tabla_pedidos, fg_color="#0f172a")
      f_row.pack(fill="x", padx=5, pady=3)

      items = json.loads(items_raw)
      resumen_items = ", ".join([i["nombre"] for i in items])
      fecha_f = fh if fh else "N/A"

      ctk.CTkLabel(f_row, text=f"#{p_id}", width=35, anchor="w").pack(
          side="left", padx=5
      )
      ctk.CTkLabel(
          f_row,
          text=fecha_f,
          width=130,
          font=ctk.CTkFont(size=11),
          text_color="gray70",
          anchor="w",
      ).pack(side="left", padx=5)
      ctk.CTkLabel(
          f_row,
          text=mesero,
          width=120,
          font=ctk.CTkFont(weight="bold"),
          text_color="#10b981",
          anchor="w",
      ).pack(side="left", padx=5)
      ctk.CTkLabel(f_row, text=cliente, width=110, anchor="w").pack(
          side="left", padx=5
      )
      ctk.CTkLabel(
          f_row,
          text=resumen_items,
          width=220,
          anchor="w",
          text_color="gray70",
      ).pack(side="left", padx=5)
      ctk.CTkLabel(
          f_row,
          text=f"${total:.2f}",
          width=70,
          font=ctk.CTkFont(weight="bold"),
          anchor="w",
      ).pack(side="left", padx=5)

      color_est = "#10b981" if estado == "cobrado" else "#38bdf8"
      if estado == "anulado":
        color_est = "#ef4444"

      ctk.CTkLabel(
          f_row,
          text=estado.upper(),
          width=90,
          text_color=color_est,
          font=ctk.CTkFont(weight="bold"),
          anchor="w",
      ).pack(side="left", padx=5)

      if estado != "anulado":
        btn_anular = ctk.CTkButton(
            f_row,
            text="🚫 Anular",
            width=75,
            height=24,
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=lambda id_p=p_id: self.anular_orden(id_p),
        )
        btn_anular.pack(side="left", padx=5)

  def anular_orden(self, p_id):
    if messagebox.askyesno(
        "Confirmar Anulación", f"¿Anular la orden #{p_id}?"
    ):
      self.cursor.execute(
          "UPDATE pedidos SET estado = 'anulado' WHERE id = ?", (p_id,)
      )
      self.conn.commit()
      self.actualizar_reportes()

  # ==========================================
  # 👥 GESTIÓN DE USUARIOS
  # ==========================================
  def vista_gestion_usuarios(self):
    form_u = ctk.CTkFrame(self.container_usuarios, width=360, corner_radius=12)
    form_u.pack(side="left", fill="y", padx=(0, 10), pady=5)

    self.lbl_titulo_form_u = ctk.CTkLabel(
        form_u,
        text="➕ Registrar / Editar Usuario",
        font=ctk.CTkFont(size=16, weight="bold"),
    )
    self.lbl_titulo_form_u.pack(pady=15, padx=15, anchor="w")

    self.entry_u_nombre = ctk.CTkEntry(
        form_u, placeholder_text="Nombre Completo", height=40
    )
    self.entry_u_nombre.pack(fill="x", padx=15, pady=8)

    self.entry_u_user = ctk.CTkEntry(
        form_u, placeholder_text="Nombre de Usuario (Login)", height=40
    )
    self.entry_u_user.pack(fill="x", padx=15, pady=8)

    self.entry_u_clave = ctk.CTkEntry(
        form_u, placeholder_text="Contraseña", show="*", height=40
    )
    self.entry_u_clave.pack(fill="x", padx=15, pady=8)

    ctk.CTkLabel(
        form_u, text="Rol / Cargo:", font=ctk.CTkFont(size=12, weight="bold")
    ).pack(anchor="w", padx=15, pady=(5, 2))

    self.combo_u_rol = ctk.CTkOptionMenu(
        form_u, values=["mesero", "cocina", "caja", "admin"], height=38
    )
    self.combo_u_rol.pack(fill="x", padx=15, pady=(0, 12))

    self.btn_guardar_u = ctk.CTkButton(
        form_u,
        text="💾 GUARDAR USUARIO",
        fg_color="#10b981",
        hover_color="#059669",
        font=ctk.CTkFont(weight="bold"),
        height=42,
        command=self.guardar_usuario,
    )
    self.btn_guardar_u.pack(fill="x", padx=15, pady=8)

    self.btn_cancelar_u = ctk.CTkButton(
        form_u,
        text="✕ Cancelar Edición",
        fg_color="#64748b",
        hover_color="#475569",
        height=32,
        command=self.limpiar_form_usuario,
    )

    tabla_frame = ctk.CTkFrame(self.container_usuarios, corner_radius=12)
    tabla_frame.pack(side="right", fill="both", expand=True, pady=5)

    ctk.CTkLabel(
        tabla_frame,
        text="👥 Personal Registrado en el Sistema",
        font=ctk.CTkFont(size=16, weight="bold"),
    ).pack(pady=15, padx=15, anchor="w")

    self.scroll_tabla_u = ctk.CTkScrollableFrame(
        tabla_frame, fg_color="transparent"
    )
    self.scroll_tabla_u.pack(fill="both", expand=True, padx=10, pady=10)

    self.actualizar_tabla_usuarios()

  def guardar_usuario(self):
    nombre = self.entry_u_nombre.get().strip()
    user = self.entry_u_user.get().strip()
    clave = self.entry_u_clave.get().strip()
    rol = self.combo_u_rol.get()

    if not nombre or not user or not clave:
      return messagebox.showwarning(
          "Atención", "Por favor completa todos los campos."
      )

    try:
      if self.usuario_id_edicion:
        self.cursor.execute(
            "UPDATE usuarios SET nombre=?, usuario=?, clave=?, rol=? WHERE id=?",
            (nombre, user, clave, rol, self.usuario_id_edicion),
        )
        messagebox.showinfo("Éxito", "Usuario actualizado correctamente.")
      else:
        self.cursor.execute(
            "INSERT INTO usuarios (nombre, usuario, clave, rol) VALUES (?, ?,"
            " ?, ?)",
            (nombre, user, clave, rol),
        )
        messagebox.showinfo("Éxito", f"Usuario '{user}' creado exitosamente.")

      self.conn.commit()
      self.limpiar_form_usuario()
      self.actualizar_tabla_usuarios()

    except sqlite3.IntegrityError:
      messagebox.showerror(
          "Error", f"El nombre de usuario '{user}' ya existe."
      )

  def preparar_edicion_usuario(self, u_id, nombre, user, clave, rol):
    self.usuario_id_edicion = u_id
    self.lbl_titulo_form_u.configure(text="✏ Editando Usuario")

    self.entry_u_nombre.delete(0, "end")
    self.entry_u_nombre.insert(0, nombre)

    self.entry_u_user.delete(0, "end")
    self.entry_u_user.insert(0, user)

    self.entry_u_clave.delete(0, "end")
    self.entry_u_clave.insert(0, clave)

    self.combo_u_rol.set(rol)

    self.btn_guardar_u.configure(text="💾 ACTUALIZAR DATOS")
    self.btn_cancelar_u.pack(fill="x", padx=15, pady=5)

  def limpiar_form_usuario(self):
    self.usuario_id_edicion = None
    self.lbl_titulo_form_u.configure(text="➕ Registrar / Editar Usuario")

    self.entry_u_nombre.delete(0, "end")
    self.entry_u_user.delete(0, "end")
    self.entry_u_clave.delete(0, "end")
    self.combo_u_rol.set("mesero")

    self.btn_guardar_u.configure(text="💾 GUARDAR USUARIO")
    self.btn_cancelar_u.pack_forget()

  def actualizar_tabla_usuarios(self):
    for w in self.scroll_tabla_u.winfo_children():
      w.destroy()

    h_row = ctk.CTkFrame(self.scroll_tabla_u, fg_color="#334155")
    h_row.pack(fill="x", padx=5, pady=5)

    ctk.CTkLabel(
        h_row,
        text="Nombre",
        width=150,
        font=ctk.CTkFont(weight="bold"),
        anchor="w",
    ).pack(side="left", padx=5)
    ctk.CTkLabel(
        h_row,
        text="Usuario",
        width=120,
        font=ctk.CTkFont(weight="bold"),
        anchor="w",
    ).pack(side="left", padx=5)
    ctk.CTkLabel(
        h_row,
        text="Rol/Cargo",
        width=110,
        font=ctk.CTkFont(weight="bold"),
        anchor="w",
    ).pack(side="left", padx=5)
    ctk.CTkLabel(
        h_row,
        text="Acciones",
        width=180,
        font=ctk.CTkFont(weight="bold"),
        anchor="w",
    ).pack(side="left", padx=5)

    self.cursor.execute("SELECT id, nombre, usuario, clave, rol FROM usuarios")
    for u_id, nombre, user, clave, rol in self.cursor.fetchall():
      f_row = ctk.CTkFrame(self.scroll_tabla_u, fg_color="#0f172a")
      f_row.pack(fill="x", padx=5, pady=3)

      ctk.CTkLabel(f_row, text=nombre, width=150, anchor="w").pack(
          side="left", padx=5
      )
      ctk.CTkLabel(
          f_row, text=user, width=120, anchor="w", text_color="gray70"
      ).pack(side="left", padx=5)

      color_r = "#10b981" if rol == "mesero" else "#38bdf8"
      if rol == "cocina":
        color_r = "#f97316"
      elif rol == "admin":
        color_r = "#a855f7"

      ctk.CTkLabel(
          f_row,
          text=rol.upper(),
          width=110,
          text_color=color_r,
          font=ctk.CTkFont(weight="bold"),
          anchor="w",
      ).pack(side="left", padx=5)

      btn_edit = ctk.CTkButton(
          f_row,
          text="✏ Editar",
          width=75,
          height=26,
          fg_color="#0284c7",
          hover_color="#0369a1",
          command=lambda i=u_id, n=nombre, u=user, c=clave, r=rol: (
              self.preparar_edicion_usuario(i, n, u, c, r)
          ),
      )
      btn_edit.pack(side="left", padx=3)

      if u_id != self.user_id_actual:
        btn_del = ctk.CTkButton(
            f_row,
            text="🗑 Eliminar",
            width=75,
            height=26,
            fg_color="#ef4444",
            hover_color="#dc2626",
            command=lambda i=u_id, u=user: self.eliminar_usuario(i, u),
        )
        btn_del.pack(side="left", padx=3)

  def eliminar_usuario(self, u_id, user):
    if messagebox.askyesno(
        "Confirmar Eliminación",
        f"¿Seguro que deseas eliminar al usuario '{user}'?",
    ):
      self.cursor.execute("DELETE FROM usuarios WHERE id = ?", (u_id,))
      self.conn.commit()
      self.actualizar_tabla_usuarios()

  # ==========================================
  # 🍔 GESTIÓN DE MENÚ Y PRODUCTOS
  # ==========================================
  def vista_gestion_menu(self):
    for w in self.container_menu_admin.winfo_children():
      w.destroy()

    form_frame = ctk.CTkFrame(
        self.container_menu_admin, width=350, corner_radius=12
    )
    form_frame.pack(side="left", fill="y", padx=(0, 10), pady=5)

    ctk.CTkLabel(
        form_frame,
        text="➕ Registrar Nuevo Producto",
        font=ctk.CTkFont(size=16, weight="bold"),
    ).pack(pady=15, padx=15, anchor="w")

    self.entry_nom_prod = ctk.CTkEntry(
        form_frame, placeholder_text="Nombre del Producto", height=40
    )
    self.entry_nom_prod.pack(fill="x", padx=15, pady=8)

    self.entry_precio_prod = ctk.CTkEntry(
        form_frame, placeholder_text="Precio (ej: 4.50)", height=40
    )
    self.entry_precio_prod.pack(fill="x", padx=15, pady=8)

    self.btn_select_img = ctk.CTkButton(
        form_frame,
        text="📷 Seleccionar Imagen",
        fg_color="#334155",
        hover_color="#475569",
        command=self.seleccionar_imagen_producto,
    )
    self.btn_select_img.pack(fill="x", padx=15, pady=8)

    self.lbl_path_img = ctk.CTkLabel(
        form_frame, text="Sin imagen seleccionada", font=ctk.CTkFont(size=11)
    )
    self.lbl_path_img.pack(padx=15, pady=(0, 10))

    btn_guardar_prod = ctk.CTkButton(
        form_frame,
        text="💾 GUARDAR EN EL MENÚ",
        fg_color="#10b981",
        hover_color="#059669",
        font=ctk.CTkFont(weight="bold"),
        height=45,
        command=self.guardar_producto_menu,
    )
    btn_guardar_prod.pack(fill="x", padx=15, pady=15)

    list_frame = ctk.CTkFrame(self.container_menu_admin, corner_radius=12)
    list_frame.pack(side="right", fill="both", expand=True, pady=5)

    ctk.CTkLabel(
        list_frame,
        text="📋 Productos en el Menú Actual",
        font=ctk.CTkFont(size=16, weight="bold"),
    ).pack(pady=15, padx=15, anchor="w")

    self.scroll_lista_menu = ctk.CTkScrollableFrame(
        list_frame, fg_color="transparent"
    )
    self.scroll_lista_menu.pack(fill="both", expand=True, padx=10, pady=10)

    self.actualizar_lista_menu_admin()

  def seleccionar_imagen_producto(self):
    archivo = filedialog.askopenfilename(
        title="Selecciona la foto del producto",
        filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.webp")],
    )
    if archivo:
      self.ruta_imagen_seleccionada = archivo
      nom = os.path.basename(archivo)
      self.lbl_path_img.configure(
          text=f"Cargado: {nom[:20]}...", text_color="#10b981"
      )

  def guardar_producto_menu(self):
    nombre = self.entry_nom_prod.get().strip()
    precio_str = self.entry_precio_prod.get().strip()

    if not nombre or not precio_str:
      return messagebox.showwarning(
          "Atención", "Ingresa el nombre y el precio."
      )

    try:
      precio = float(precio_str)
    except ValueError:
      return messagebox.showerror(
          "Error", "El precio debe ser un número válido (ej: 5.00)."
      )

    dest_path = ""
    if self.ruta_imagen_seleccionada:
      try:
        ext = os.path.splitext(self.ruta_imagen_seleccionada)[1]
        nom_limpio = "".join(
            c for c in nombre if c.isalnum() or c in (" ", "_")
        ).rstrip()
        dest_path = os.path.join(
            "imagenes", f"prod_{nom_limpio.replace(' ', '_')}{ext}"
        )

        with Image.open(self.ruta_imagen_seleccionada) as img:
          img_rgb = img.convert("RGB")
          img_rgb.save(dest_path)
      except Exception as e:
        print(f"Error procesando imagen: {e}")
        dest_path = ""

    try:
      self.cursor.execute(
          "INSERT INTO productos (nombre, precio, categoria, icono,"
          " imagen_path) VALUES (?, ?, ?, ?, ?)",
          (nombre, precio, "General", "🍔", dest_path),
      )
      self.conn.commit()

      self.entry_nom_prod.delete(0, "end")
      self.entry_precio_prod.delete(0, "end")
      self.ruta_imagen_seleccionada = None
      self.lbl_path_img.configure(
          text="Sin imagen seleccionada", text_color="gray"
      )

      messagebox.showinfo("Éxito", f"¡Producto '{nombre}' guardado con éxito!")
      self.actualizar_lista_menu_admin()

    except Exception as err_db:
      messagebox.showerror(
          "Error DB", f"No se pudo guardar en la base de datos: {err_db}"
      )

  def actualizar_lista_menu_admin(self):
    for w in self.scroll_lista_menu.winfo_children():
      w.destroy()

    self.cursor.execute("SELECT id, nombre, precio, imagen_path FROM productos")
    prods = self.cursor.fetchall()

    for p_id, nombre, precio, img_path in prods:
      row = ctk.CTkFrame(self.scroll_lista_menu, fg_color="#1e293b", height=50)
      row.pack(fill="x", pady=4, padx=5)

      if img_path and os.path.exists(img_path):
        try:
          my_img = ctk.CTkImage(
              light_image=Image.open(img_path),
              dark_image=Image.open(img_path),
              size=(35, 35),
          )
          lbl_img = ctk.CTkLabel(row, image=my_img, text="")
          lbl_img.pack(side="left", padx=10)
        except:
          ctk.CTkLabel(
              row, text="🍔", font=ctk.CTkFont(size=20), width=35
          ).pack(side="left", padx=10)
      else:
        ctk.CTkLabel(row, text="🍔", font=ctk.CTkFont(size=20), width=35).pack(
            side="left", padx=10
        )

      ctk.CTkLabel(
          row, text=nombre, font=ctk.CTkFont(weight="bold"), width=200, anchor="w"
      ).pack(side="left", padx=10)
      ctk.CTkLabel(
          row,
          text=f"${precio:.2f}",
          text_color="#10b981",
          font=ctk.CTkFont(weight="bold"),
          width=100,
          anchor="w",
      ).pack(side="left", padx=10)

      btn_del = ctk.CTkButton(
          row,
          text="🗑 Eliminar",
          width=90,
          height=28,
          fg_color="#ef4444",
          hover_color="#dc2626",
          command=lambda id_p=p_id: self.eliminar_producto_menu(id_p),
      )
      btn_del.pack(side="right", padx=10)

  def eliminar_producto_menu(self, p_id):
    if messagebox.askyesno(
        "Confirmar", "¿Seguro que deseas eliminar este producto?"
    ):
      self.cursor.execute("DELETE FROM productos WHERE id = ?", (p_id,))
      self.conn.commit()
      self.actualizar_lista_menu_admin()

  # ==========================================
  # MÓDULOS OPERATIVOS (MESERO, COCINA, CAJA)
  # ==========================================
  def vista_mesero(self):
    left_p = ctk.CTkFrame(self.main_container, corner_radius=12)
    left_p.pack(side="left", fill="both", expand=True, padx=(0, 10))
    ctk.CTkLabel(
        left_p,
        text="Catálogo de Productos",
        font=ctk.CTkFont(size=16, weight="bold"),
    ).pack(anchor="w", padx=15, pady=15)
    self.scroll_menu = ctk.CTkScrollableFrame(left_p, fg_color="transparent")
    self.scroll_menu.pack(fill="both", expand=True, padx=10, pady=10)
    self.cargar_tarjetas_productos()

    right_p = ctk.CTkFrame(self.main_container, width=380, corner_radius=12)
    right_p.pack(side="right", fill="y", padx=(10, 0))
    ctk.CTkLabel(
        right_p,
        text="Orden del Cliente",
        font=ctk.CTkFont(size=16, weight="bold"),
    ).pack(anchor="w", padx=15, pady=15)
    self.entry_cliente = ctk.CTkEntry(
        right_p,
        placeholder_text="Nombre de Cliente / Mesa",
        height=40,
        corner_radius=8,
    )
    self.entry_cliente.pack(fill="x", padx=15, pady=(0, 10))
    self.frame_carrito_items = ctk.CTkScrollableFrame(
        right_p, height=320, fg_color="#0f172a"
    )
    self.frame_carrito_items.pack(fill="both", expand=True, padx=15, pady=5)
    self.lbl_total_mesero = ctk.CTkLabel(
        right_p,
        text="TOTAL: $0.00",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#10b981",
    )
    self.lbl_total_mesero.pack(anchor="e", padx=15, pady=10)
    btn_enviar = ctk.CTkButton(
        right_p,
        text="🚀 ENVIAR A COCINA Y CAJA",
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color="#10b981",
        hover_color="#059669",
        height=48,
        corner_radius=10,
        command=self.enviar_pedido,
    )
    btn_enviar.pack(fill="x", padx=15, pady=15)

  def cargar_tarjetas_productos(self):
    for w in self.scroll_menu.winfo_children():
      w.destroy()

    self.cursor.execute("SELECT nombre, precio, icono, imagen_path FROM productos")
    prods = self.cursor.fetchall()

    for i, (nombre, precio, icono, img_path) in enumerate(prods):
      row = i // 3
      col = i % 3

      card = ctk.CTkFrame(
          self.scroll_menu, corner_radius=10, fg_color="#1e293b"
      )
      card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

      if img_path and os.path.exists(img_path):
        try:
          my_img = ctk.CTkImage(
              light_image=Image.open(img_path),
              dark_image=Image.open(img_path),
              size=(90, 70),
          )
          lbl_img = ctk.CTkLabel(card, image=my_img, text="")
          lbl_img.pack(pady=(10, 5))
        except:
          ctk.CTkLabel(card, text=icono, font=ctk.CTkFont(size=35)).pack(
              pady=(12, 2)
          )
      else:
        ctk.CTkLabel(card, text=icono, font=ctk.CTkFont(size=35)).pack(
            pady=(12, 2)
        )

      ctk.CTkLabel(
          card, text=nombre, font=ctk.CTkFont(size=13, weight="bold")
      ).pack()
      ctk.CTkLabel(
          card,
          text=f"${precio:.2f}",
          font=ctk.CTkFont(size=13),
          text_color="#10b981",
      ).pack(pady=(0, 10))

      btn_add = ctk.CTkButton(
          card,
          text="Agregar +",
          width=120,
          height=28,
          fg_color="#334155",
          hover_color="#10b981",
          command=lambda n=nombre, p=precio: self.agregar_al_carrito(n, p),
      )
      btn_add.pack(pady=(0, 12))

  def agregar_al_carrito(self, nombre, precio):
    self.carrito.append({"nombre": nombre, "precio": precio})
    self.actualizar_carrito_ui()

  def actualizar_carrito_ui(self):
    for widget in self.frame_carrito_items.winfo_children():
      widget.destroy()

    total = 0.0
    for idx, item in enumerate(self.carrito):
      total += item["precio"]

      row = ctk.CTkFrame(
          self.frame_carrito_items, height=35, fg_color="#1e293b"
      )
      row.pack(fill="x", pady=3, padx=2)

      ctk.CTkLabel(
          row, text=item["nombre"], font=ctk.CTkFont(size=12)
      ).pack(side="left", padx=10)
      ctk.CTkLabel(
          row,
          text=f"${item['precio']:.2f}",
          font=ctk.CTkFont(size=12, weight="bold"),
          text_color="#10b981",
      ).pack(side="left", padx=5)

      btn_del = ctk.CTkButton(
          row,
          text="✕",
          width=25,
          height=22,
          fg_color="#ef4444",
          hover_color="#dc2626",
          command=lambda i=idx: self.quitar_del_carrito(i),
      )
      btn_del.pack(side="right", padx=5)

    self.lbl_total_mesero.configure(text=f"TOTAL: ${total:.2f}")

  def quitar_del_carrito(self, idx):
    self.carrito.pop(idx)
    self.actualizar_carrito_ui()

  def enviar_pedido(self):
    cliente = self.entry_cliente.get().strip()
    if not cliente or not self.carrito:
      return messagebox.showwarning(
          "Atención", "Escribe el nombre del cliente y agrega productos."
      )

    total = sum(i["precio"] for i in self.carrito)
    items_json = json.dumps(self.carrito)
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    self.cursor.execute(
        "INSERT INTO pedidos (cliente, items, total, mesero, fecha_hora) VALUES"
        " (?, ?, ?, ?, ?)",
        (cliente, items_json, total, self.usuario_actual, fecha_actual),
    )
    self.conn.commit()

    self.carrito.clear()
    self.entry_cliente.delete(0, "end")
    self.actualizar_carrito_ui()
    messagebox.showinfo("Éxito", "¡Orden registrada correctamente!")

  def vista_cocina(self):
    ctk.CTkLabel(
        self.main_container,
        text="🔥 Monitor de Cocina - Comandas Pendientes",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#f97316",
    ).pack(anchor="w", pady=(0, 15))
    self.scroll_cocina = ctk.CTkScrollableFrame(
        self.main_container, fg_color="transparent"
    )
    self.scroll_cocina.pack(fill="both", expand=True)
    self.actualizar_cocina()

  def actualizar_cocina(self):
    for widget in self.scroll_cocina.winfo_children():
      widget.destroy()

    self.cursor.execute(
        "SELECT id, cliente, items, mesero, fecha_hora FROM pedidos WHERE"
        " estado = 'pendiente'"
    )
    pedidos = self.cursor.fetchall()

    for i, (p_id, cliente, items_raw, mesero, fh) in enumerate(pedidos):
      items = json.loads(items_raw)
      row = i // 3
      col = i % 3

      card = ctk.CTkFrame(
          self.scroll_cocina,
          corner_radius=12,
          fg_color="#1e293b",
          border_width=1,
          border_color="#f97316",
      )
      card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

      ctk.CTkLabel(
          card,
          text=f"Orden #{p_id} - {cliente}",
          font=ctk.CTkFont(size=15, weight="bold"),
          text_color="#f97316",
      ).pack(pady=(10, 2), padx=15, anchor="w")
      ctk.CTkLabel(
          card,
          text=f"📱 Atendido: {mesero} | 🕒 {fh[11:16] if fh else ''}",
          font=ctk.CTkFont(size=11),
          text_color="gray70",
      ).pack(padx=15, anchor="w", pady=(0, 5))

      list_frame = ctk.CTkFrame(card, fg_color="#0f172a")
      list_frame.pack(fill="both", expand=True, padx=10, pady=5)

      for item in items:
        ctk.CTkLabel(
            list_frame,
            text=f"• {item['nombre']}",
            font=ctk.CTkFont(size=13),
            anchor="w",
        ).pack(fill="x", padx=10, pady=2)

      btn_listo = ctk.CTkButton(
          card,
          text="✔ MARCAR LISTO",
          fg_color="#f97316",
          hover_color="#ea580c",
          font=ctk.CTkFont(weight="bold"),
          command=lambda id_p=p_id: self.marcar_listo_cocina(id_p),
      )
      btn_listo.pack(fill="x", padx=10, pady=10)

  def marcar_listo_cocina(self, p_id):
    self.cursor.execute(
        "UPDATE pedidos SET estado = 'preparado' WHERE id = ?", (p_id,)
    )
    self.conn.commit()
    self.actualizar_cocina()

  # ==========================================
  # CAJA (APERTURA, CIERRE Y COBROS)
  # ==========================================
  def vista_caja(self):
    for w in self.main_container.winfo_children():
      w.destroy()

    self.cursor.execute(
        "SELECT id, monto_apertura FROM cajas WHERE cajero=? AND"
        " estado='abierta'",
        (self.usuario_actual,),
    )
    caja_abierta = self.cursor.fetchone()

    bar_caja = ctk.CTkFrame(self.main_container, height=50, fg_color="#1e293b")
    bar_caja.pack(fill="x", pady=(0, 10))

    if not caja_abierta:
      ctk.CTkLabel(
          bar_caja,
          text="⚠️ CAJA CERRADA",
          font=ctk.CTkFont(size=14, weight="bold"),
          text_color="#ef4444",
      ).pack(side="left", padx=15)
      btn_abrir = ctk.CTkButton(
          bar_caja,
          text="🔓 ABRIR CAJA",
          fg_color="#10b981",
          hover_color="#059669",
          command=self.dialogo_abrir_caja,
      )
      btn_abrir.pack(side="left", padx=10)
    else:
      ctk.CTkLabel(
          bar_caja,
          text=f"🟢 CAJA ABIERTA (Base: ${caja_abierta[1]:.2f})",
          font=ctk.CTkFont(size=14, weight="bold"),
          text_color="#10b981",
      ).pack(side="left", padx=15)
      btn_cerrar = ctk.CTkButton(
          bar_caja,
          text="🔒 CERRAR CAJA (ARQUEO)",
          fg_color="#ef4444",
          hover_color="#dc2626",
          command=lambda: self.dialogo_cerrar_caja(caja_abierta[0]),
      )
      btn_cerrar.pack(side="right", padx=15)

    ctk.CTkLabel(
        self.main_container,
        text="💰 Panel de Cobros",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#38bdf8",
    ).pack(anchor="w", pady=(0, 10))

    self.scroll_caja = ctk.CTkScrollableFrame(
        self.main_container, fg_color="transparent"
    )
    self.scroll_caja.pack(fill="both", expand=True)
    self.actualizar_caja()

  def dialogo_abrir_caja(self):
    dialogo = ctk.CTkInputDialog(
        text="Ingresa el monto base de dinero en caja ($):",
        title="Apertura de Caja",
    )
    monto_str = dialogo.get_input()

    if monto_str is not None:
      try:
        monto = float(monto_str)
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "INSERT INTO cajas (cajero, monto_apertura, fecha_apertura,"
            " estado) VALUES (?, ?, ?, 'abierta')",
            (self.usuario_actual, monto, fecha),
        )
        self.conn.commit()
        messagebox.showinfo("Éxito", f"Caja abierta con base de ${monto:.2f}")
        self.vista_caja()
      except ValueError:
        messagebox.showerror(
            "Error", "Ingresa un número válido para el monto base."
        )

  def dialogo_cerrar_caja(self, caja_id):
    self.cursor.execute(
        "SELECT SUM(total) FROM pedidos WHERE estado='cobrado'"
    )
    total_ventas = self.cursor.fetchone()[0] or 0.0

    self.cursor.execute(
        "SELECT monto_apertura FROM cajas WHERE id=?", (caja_id,)
    )
    base = self.cursor.fetchone()[0]

    esperado = base + total_ventas

    if messagebox.askyesno(
        "Cierre de Caja",
        f"📊 RESUMEN DE CIERRE:\n\n• Base Inicial: ${base:.2f}\n• Ventas"
        f" Cobradas: ${total_ventas:.2f}\n• TOTAL ESPERADO EN ENTRADA:"
        f" ${esperado:.2f}\n\n¿Deseas cerrar la caja ahora?",
    ):
      fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      self.cursor.execute(
          "UPDATE cajas SET monto_cierre=?, ventas_efectivo=?, fecha_cierre=?,"
          " estado='cerrada' WHERE id=?",
          (esperado, total_ventas, fecha, caja_id),
      )
      self.conn.commit()
      messagebox.showinfo(
          "Caja Cerrada", f"Caja cerrada exitosamente. Arqueo: ${esperado:.2f}"
      )
      self.vista_caja()

  def actualizar_caja(self):
    for widget in self.scroll_caja.winfo_children():
      widget.destroy()

    self.cursor.execute(
        "SELECT id, cliente, items, total, estado, mesero, fecha_hora FROM"
        " pedidos WHERE estado != 'cobrado' AND estado != 'anulado'"
    )
    pedidos = self.cursor.fetchall()

    for i, (p_id, cliente, items_raw, total, estado, mesero, fh) in enumerate(
        pedidos
    ):
      row = i // 3
      col = i % 3

      card = ctk.CTkFrame(
          self.scroll_caja,
          corner_radius=12,
          fg_color="#1e293b",
          border_width=1,
          border_color="#38bdf8",
      )
      card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

      ctk.CTkLabel(
          card,
          text=f"Orden #{p_id} - {cliente}",
          font=ctk.CTkFont(size=15, weight="bold"),
          text_color="#38bdf8",
      ).pack(pady=(5, 2), padx=15, anchor="w")
      ctk.CTkLabel(
          card,
          text=f"📱 Mesero: {mesero} | 🕒 {fh[11:16] if fh else ''}",
          font=ctk.CTkFont(size=11),
          text_color="gray70",
      ).pack(padx=15, anchor="w")

      estado_badge = (
          "¡LISTO PARA ENTREGAR!" if estado == "preparado" else "En preparación"
      )
      color_badge = "#10b981" if estado == "preparado" else "#eab308"
      ctk.CTkLabel(
          card,
          text=estado_badge,
          font=ctk.CTkFont(size=11, weight="bold"),
          text_color=color_badge,
      ).pack(padx=15, anchor="w", pady=(2, 0))

      btn_add_item = ctk.CTkButton(
          card,
          text="➕ Añadir Adicional",
          width=120,
          height=24,
          fg_color="#334155",
          hover_color="#0284c7",
          font=ctk.CTkFont(size=11),
          command=lambda id_p=p_id,
          it=items_raw,
          tot=total: self.agregar_item_desde_caja(id_p, it, tot),
      )
      btn_add_item.pack(anchor="e", padx=15, pady=(5, 0))

      ctk.CTkLabel(
          card,
          text=f"Total: ${total:.2f}",
          font=ctk.CTkFont(size=20, weight="bold"),
          text_color="#10b981",
      ).pack(pady=8)

      entry_pago = ctk.CTkEntry(
          card, placeholder_text=f"Efectivo (${total:.2f})", height=35
      )
      entry_pago.pack(fill="x", padx=10, pady=5)

      btn_cobrar = ctk.CTkButton(
          card,
          text="💵 COBRAR",
          fg_color="#0284c7",
          hover_color="#0369a1",
          font=ctk.CTkFont(weight="bold"),
          command=lambda id_p=p_id, t=total, e=entry_pago: self.procesar_cobro(
              id_p, t, e
          ),
      )
      btn_cobrar.pack(fill="x", padx=10, pady=(5, 10))

  def agregar_item_desde_caja(self, pedido_id, items_json_actual, total_actual):
    self.cursor.execute("SELECT nombre, precio FROM productos")
    productos = self.cursor.fetchall()

    if not productos:
      return messagebox.showwarning(
          "Atención", "No hay productos registrados en el menú."
      )

    ventana_add = ctk.CTkToplevel(self)
    ventana_add.title(f"Añadir Adicional - Orden #{pedido_id}")
    ventana_add.geometry("400x250")
    ventana_add.grab_set()

    ctk.CTkLabel(
        ventana_add,
        text="Selecciona el producto a añadir:",
        font=ctk.CTkFont(size=14, weight="bold"),
    ).pack(pady=15)

    nombres_prods = [f"{p[0]} - ${p[1]:.2f}" for p in productos]
    combo_prods = ctk.CTkOptionMenu(ventana_add, values=nombres_prods, width=280)
    combo_prods.pack(pady=10)

    def confirmar_adicion():
      seleccion = combo_prods.get()
      for nombre, precio in productos:
        if f"{nombre} - ${precio:.2f}" == seleccion:
          items_lista = json.loads(items_json_actual)
          items_lista.append({"nombre": nombre, "precio": precio})

          nuevo_total = total_actual + precio
          nuevo_json = json.dumps(items_lista)

          self.cursor.execute(
              "UPDATE pedidos SET items = ?, total = ? WHERE id = ?",
              (nuevo_json, nuevo_total, pedido_id),
          )
          self.conn.commit()

          messagebox.showinfo(
              "Éxito", f"¡Se añadió '{nombre}' a la orden #{pedido_id}!"
          )
          ventana_add.destroy()
          self.actualizar_caja()
          break

    btn_confirmar = ctk.CTkButton(
        ventana_add,
        text="✔ Agregar a la Cuenta",
        fg_color="#10b981",
        hover_color="#059669",
        command=confirmar_adicion,
    )
    btn_confirmar.pack(pady=20)

  def procesar_cobro(self, p_id, total, entry_widget):
    val = entry_widget.get().strip()
    monto_entregado = float(val) if val else total

    if monto_entregado < total:
      return messagebox.showerror(
          "Error", f"Monto insuficiente. Total: ${total:.2f}"
      )

    cambio = monto_entregado - total
    self.cursor.execute(
        "UPDATE pedidos SET estado = 'cobrado' WHERE id = ?", (p_id,)
    )
    self.conn.commit()

    messagebox.showinfo(
        "Cobro Exitoso",
        f"Cobro realizado con éxito.\nTotal: ${total:.2f}\nEntregado:"
        f" ${monto_entregado:.2f}\nCambio/Vueltas: ${cambio:.2f}",
    )
    self.actualizar_caja()


if __name__ == "__main__":
  app = SistemaPOSPro()
  app.mainloop()
