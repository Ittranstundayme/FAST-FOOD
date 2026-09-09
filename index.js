export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Endpoint para obtener todos los productos
    if (url.pathname === "/api/productos" && request.method === "GET") {
      const { results } = await env.DB.prepare("SELECT * FROM productos").all();
      return Response.json(results);
    }

    // Endpoint para agregar un nuevo producto
    if (url.pathname === "/api/productos" && request.method === "POST") {
      const data = await request.json();
      await env.DB.prepare(
        "INSERT INTO productos (nombre, precio, categoria, requiere_salsa, imagen) VALUES (?, ?, ?, ?, ?)"
      ).bind(data.nombre, data.precio, data.categoria, data.requiere_salsa ? 1 : 0, data.imagen || "").run();
      
      return Response.json({ success: true, message: "Producto guardado en Cloudflare D1" });
    }

    // Sirve el archivo HTML estático si no es una ruta API
    return env.ASSETS.fetch(request);
  }
};
