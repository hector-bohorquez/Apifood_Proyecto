**Manual Técnico — Proyecto_AA2_EV01**

Última actualización: 12/02/2026

**Resumen:**
- **Proyecto:** Aplicación web basada en Flask para catálogo, carrito y gestión de inventario (e-commerce ligero).
- **Tecnologías principales:** Python, Flask, MySQL (flask_mysqldb / mysqlclient), HTML templates Jinja2, CSS, JavaScript.

**Índice**
- Resumen
- Requisitos
- Estructura del repositorio
- Configuración y despliegue local
- Esquema de base de datos
- Rutas principales y vistas
- Archivos clave y plantillas
- Seguridad y buenas prácticas
- Mantenimiento y pruebas
- Contacto / autores

---

**Requisitos**
- Python 3.8+ (recomendado 3.10/3.11)
- MySQL server (o MariaDB)
- Paquetes Python (instalación via pip):

```bash
python -m venv venv
venv\Scripts\activate    # Windows
pip install --upgrade pip
pip install Flask flask-mysqldb mysqlclient
```

Nota: si `mysqlclient` da problemas en Windows, instalar ruedas binarios apropiadas o usar WSL / contenedor.

**Dependencias detectadas** (extraídas de [app.py](app.py)):
- `flask`, `flask_mysqldb`, `MySQLdb` (cursor), `werkzeug.security`, `werkzeug.utils`, `smtplib`, `email.mime.text`.

---

**Estructura del repositorio**
- Archivo principal de la aplicación: [app.py](app.py)
- Script de creación de BD: [scriptDB.sql](scriptDB.sql)
- Plantillas HTML: [templates/](templates/)
  - ejemplo: [templates/index.html](templates/index.html), [templates/catalogo.html](templates/catalogo.html)
- Archivos estáticos: [static/](static/)
  - CSS: [static/css/style.css](static/css/style.css)
  - JS: [static/js/script.js](static/js/script.js)
  - Uploads: [static/uploads](static/uploads) (directorio de subida de imágenes)

---

**Configuración (valores por defecto en `app.py`)**
- `app.secret_key` se define en `app.py` (cambiar para producción).
- Configuración MySQL por defecto en `app.py`:
  - HOST: `localhost`
  - USER: `root`
  - PASSWORD: `1234`
  - DB: `bd_app`

IMPORTANTE: Cambiar credenciales y secretos antes de publicar. Use variables de entorno en producción.

**Creación de la base de datos**
- Ejecutar el script SQL incluido: [scriptDB.sql](scriptDB.sql)

Ejemplo (línea de comandos MySQL):

```bash
mysql -u root -p < scriptDB.sql
```

El proyecto usa tablas (entre otras): `usuarios`, `usuario_rol`, `roles`, `registro_login`, `productos`, `carrito`, `detalle_carrito`.

---

**Rutas principales (extraídas de `app.py`)**
- `/` → `index()` -> [templates/index.html](templates/index.html)
- `/login` (GET, POST) → `login()` -> [templates/login.html](templates/login.html)
- `/logout` → `logout()`
- `/registro` (GET, POST) → `registro()` -> [templates/registro.html](templates/registro.html)
- `/forgot` (GET, POST) → `forgot()` -> [templates/forgot.html](templates/forgot.html)
- `/reset/<token>` (GET, POST) → `reset(token)` -> [templates/reset.html](templates/reset.html)
- `/dashboard` → `dashboard()` -> [templates/dashboard.html](templates/dashboard.html)
- `/actualizar/<int:id>` (POST) → `actualizar(id)`
- `/eliminar/<int:id>` → `eliminar(id)`
- `/inventario` → `inventario()` -> [templates/inventario.html](templates/inventario.html)
- `/agregar_producto` (GET, POST) → `agregar_producto()` -> [templates/agregar_producto.html] (verificar existencia)
- `/actualizarProducto/<int:id>` (POST) → `actualizarProducto(id)`
- `/eliminarProducto/<int:id>` → `eliminarProducto(id)`
- `/catalogo` → `catalogo()` -> [templates/catalogo.html](templates/catalogo.html)
- `/agregarCarrito/<int:id>` (POST) → `agregarCarrito(id)`
- `/carrito` → `carrito()` -> [templates/carrito.html](templates/carrito.html)
- `/actualizar_carrito/<int:id>` (POST) → `actualizar_carrito(id)`
- `/eliminar_del_carrito/<int:id>` → `eliminar_del_carrito(id)`
- `/vaciar_carrito` → `vaciar_carrito()`
- `/pago` (GET, POST) → `pago()` -> [templates/pago.html](templates/pago.html)
- `/confirmar_pago` → `confirmar_pago()` -> [templates/comfirmacion_pago.html](templates/comfirmacion_pago.html)
- `/contacto` → `contacto()` -> [templates/contacto.html](templates/contacto.html)
- `/sobre_apifood` → `sobre_apifood()` -> [templates/sobre_apifood.html](templates/sobre_apifood.html)

Además: manejo de errores registrado con `app.register_error_handler(404, ...)` y `405`.

---

**Flujo de datos y lógica principal**
- Autenticación: `usuarios` con `password` hasheado (werkzeug `generate_password_hash` / `check_password_hash`).
- Roles: relación `usuario_rol` + tabla `roles` para diferenciar `Admin` y `Usuario`.
- Carrito: tabla `carrito` y `detalle_carrito` para ítems por usuario.
- Inventario: control de stock en `productos` y actualización al pagar.

**Validaciones importantes**
- Registro: regex de contraseña fuerte en `registro()`.
- Al agregar al carrito y pagar: comprobación de stock antes de aceptar cantidades.

---

**Seguridad y recomendaciones**
- No dejar `app.secret_key` y credenciales (DB y correo) en el código. Usar variables de entorno:

```bash
set FLASK_APP=app.py
set FLASK_ENV=development
set SECRET_KEY="valor-secreto"
set MYSQL_USER=...
set MYSQL_PASSWORD=...
```

- Evitar en producción `debug=True` (actualmente en `app.run(debug=True, ...)`).
- El envío de correos en `enviar_correo_reset` usa credenciales en claro: migrar a servicio de correo seguro o a variables de entorno.
- Manejar subida de archivos con validación de extensiones y límites de tamaño; hoy se usa `secure_filename` y se guarda en `static/uploads`.

---

**Pruebas locales y verificación rápida**
1. Crear entorno virtual e instalar dependencias.
2. Crear la base de datos con `scriptDB.sql`.
3. Ajustar credenciales en `app.py` o configurar variables de entorno.
4. Ejecutar la app:

```bash
python app.py
# o
flask run --port 3000
```

La aplicación por defecto expone `host=0.0.0.0` y `port=3000` según `app.py`.

---

**Mantenimiento y próximos pasos sugeridos**
- Extraer configuración sensible a un archivo `.env` y usar `python-dotenv` o variables de entorno.
- Añadir `requirements.txt` con versiones fijas: `pip freeze > requirements.txt`.
- Añadir pruebas unitarias mínimo para: registro/login, agregar al carrito, cálculo de total, pago.
- Revisar y completar plantillas faltantes (por ejemplo `agregar_producto.html` si no existe).
- Considerar contenedor Docker para facilitar despliegue.

---

**Contacto / Autores**
- Proyecto en: carpeta raíz del workspace.

Si desea, genero un `requirements.txt`, agrego variables de entorno y preparo un `README.md` con pasos resumidos para despliegue.

Fin del manual técnico provisional
