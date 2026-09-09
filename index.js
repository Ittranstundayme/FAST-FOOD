export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // --- ENDPOINTS API PARA PRODUCTOS ---
    if (url.pathname === "/api/productos" && request.method === "GET") {
      const { results } = await env.DB.prepare("SELECT * FROM productos").all();
      return Response.json(results);
    }

    if (url.pathname === "/api/productos" && request.method === "POST") {
      const data = await request.json();
      await env.DB.prepare(
        "INSERT INTO productos (nombre, precio, categoria, requiere_salsa, imagen) VALUES (?, ?, ?, ?, ?)"
      ).bind(data.nombre, data.precio, data.categoria, data.requiere_salsa ? 1 : 0, data.imagen || "").run();
      return Response.json({ success: true });
    }

    if (url.pathname.startsWith("/api/productos/") && request.method === "DELETE") {
      const id = url.pathname.split("/")[3];
      await env.DB.prepare("DELETE FROM productos WHERE id = ?").bind(id).run();
      return Response.json({ success: true });
    }

    // --- ENDPOINTS API PARA PEDIDOS ---
    if (url.pathname === "/api/pedidos" && request.method === "GET") {
      const { results } = await env.DB.prepare("SELECT * FROM pedidos").all();
      return Response.json(results);
    }

    if (url.pathname === "/api/pedidos" && request.method === "POST") {
      const p = await request.json();
      await env.DB.prepare(
        "INSERT INTO pedidos (cliente, fact_ruc, fact_razon, items, total, estado, mesero, metodo_pago, fecha_hora) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
      ).bind(p.cliente, p.fact_ruc, p.fact_razon, p.items, p.total, p.estado, p.mesero, p.metodo_pago, p.fecha_hora).run();
      return Response.json({ success: true });
    }

    // --- SIRVE TU HTML DESDE EL WORKER ---
    return new Response(HTML_CONTENT, {
      headers: { "content-type": "text/html;charset=UTF-8" },
    });
  }
};

const HTML_CONTENT = `
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>⚡ FastFood POS Pro Web</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-white p-6">
    <h1 class="text-2xl font-bold text-emerald-400">⚡ Sistema POS Conectado a Cloudflare D1</h1>
    <p class="text-slate-400 mt-2">Los cambios realizados desde cualquier dispositivo se guardan e impactan en tiempo real.</p>
</body>
</html>
`;
