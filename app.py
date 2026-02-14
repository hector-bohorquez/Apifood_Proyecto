from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
import MySQLdb.cursors

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import re
import os
import random
import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de la aplicación Flask y MySQL
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave_secreta_por_defecto')

app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'bd_app')

mysql = MySQL(app)

# Inicializar protección CSRF
csrf = CSRFProtect(app)

# Rutas de la aplicación
@app.route('/')
def index():
    return render_template('index.html')
     
# Inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_ingresada = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("""
                    SELECT u.idUsuario, u.nombre, u.password, r.nombreRol
                    FROM usuarios u
                    JOIN usuario_rol ur ON u.idUsuario = ur.idUsuario
                    JOIN roles r ON ur.idRol = r.idRol
                    WHERE u.username = %s
                    """, (username,))
        
        user = cur.fetchone()
       
        if user and check_password_hash(user[2], password_ingresada):
            session['idUsuario'] = user[0]
            session['usuario'] = user[1]
            session['rol'] = user[3]
            flash(f"Bienvenido, {user[1]}!")
            
            cur.execute("""
            INSERT INTO registro_login (idUsuario, fecha) 
            VALUES (%s, NOW())
            """, (user[0],))
            mysql.connection.commit()
            
            cur.close()
            
            if user[3] == 'Admin':
                return redirect(url_for('dashboard'))
            elif user[3] == 'Usuario':
                return redirect(url_for('index'))
            else:
                flash('Rol de usuario no reconocido.')
                return redirect(url_for('login'))
        else:
            flash('Usuario o contraseña incorrectos.')
          
    return render_template('login.html')

# Cerrar sesión
@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente')
    return redirect(url_for('index'))

# Registro
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        username = request.form['username']
        password = request.form['password']

        # Validación de contraseña segura
        password_regex = re.compile(
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@#$%^&+=!?.\-_])[A-Za-z\d@#$%^&+=!?.\-_]{8,}$'
        )
        if not password_regex.match(password):
            flash('La contraseña debe tener al menos 8 caracteres, incluir una mayúscula, una minúscula, un número y un carácter especial (@#$%^&+=!?.-_) y no puede contener espacios ni caracteres no permitidos.')
            return render_template('registro.html')

        hashed_password = generate_password_hash(password)

        cur = mysql.connection.cursor()
        try:
            cur.execute("INSERT INTO usuarios (nombre, apellido, username, password) VALUES (%s, %s, %s, %s)", (nombre, apellido, username, hashed_password))
            mysql.connection.commit()

            cur.execute("SELECT idUsuario FROM usuarios WHERE username = %s", (username,))
            nuevo_usuario = cur.fetchone()
            
            cur.execute("INSERT INTO usuario_rol (idUsuario, idRol) VALUES (%s, %s)", (nuevo_usuario[0], 2))  # Asignar rol 'Usuario' por defecto
            mysql.connection.commit()
            
            flash('Registro exitoso. Por favor inicia sesión.')
            return redirect(url_for('login'))
        except:
            flash('Este correo ya está registrado.')
        finally:
            cur.close()
            
    return render_template('registro.html')

# Recuperación de contraseña
@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form['email']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT idUsuario FROM usuarios WHERE username = %s", (email,)) 
        existe = cur.fetchone()
        cur.close()

        if not existe:
            flash('El correo electrónico no está registrado.')
            return redirect(url_for('forgot'))

        token = generate_token(email)
        enviar_correo_reset(email, token)
        flash('Se ha enviado un correo electrónico para restablecer la contraseña.')
        return redirect(url_for('login'))
    return render_template('forgot.html')

# Restablecer contraseña
@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset(token):
    cur = mysql.connection.cursor()
    cur.execute("SELECT idUsuario, token_expiry FROM usuarios WHERE reset_token = %s", (token,))
    usuario = cur.fetchone()
    cur.close()
    
    if not usuario or datetime.now() > usuario[1]:
        flash('Token inválido o ha expirado.')
        return redirect(url_for('forgot'))
    
    if request.method == 'POST':
        nueva_password = request.form['password']
        hash_nueva = generate_password_hash(nueva_password)
        
        cur = mysql.connection.cursor()
        cur.execute("UPDATE usuarios SET password = %s, reset_token = NULL, token_expiry = NULL WHERE idUsuario = %s", (hash_nueva, usuario[0]))
        mysql.connection.commit()
        cur.close()
        
        flash('Contraseña restablecida exitosamente.')
        return redirect(url_for('login'))
    
    return render_template('reset.html')

# Generar token y enviar correo
def generate_token(email):
    token = secrets.token_urlsafe(32)
    expiry = datetime.now() + timedelta(hours=1)
    cur = mysql.connection.cursor()
    cur.execute("UPDATE usuarios SET reset_token = %s, token_expiry = %s WHERE username = %s", (token, expiry, email))
    mysql.connection.commit()
    cur.close()
    return token

# Enviar correo de restablecimiento
def enviar_correo_reset(email, token):
    enlace = url_for('reset', token = token, _external=True)
    cuerpo = f"""Hola, Solicitaste recuperar tu contraseña. Haz clic en el siguiente enlace: para restablecerla:
    {enlace}
    Este enlace expira en 1 hora.
    Si no lo solicitaste, ignora este mensaje."""

    remitente = os.getenv('MAIL_USER')
    clave = os.getenv('MAIL_PASSWORD')
    mensaje = MIMEText(cuerpo)
    mensaje['Subject'] = 'Restablecer tu contraseña'
    mensaje['From'] = remitente
    mensaje['To'] = email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        server.starttls()
        server.login(remitente, clave)
        server.sendmail(remitente, email, mensaje.as_string())
        server.quit()
    except Exception as e:
        print(f"Error enviando correo de recuperación a {email}: {e}")
        flash('Ocurrió un error al enviar el correo de recuperación. Intenta más tarde.', 'danger')


# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para acceder al dashboard.')
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
                   SELECT u.idUsuario, u.nombre, u.apellido, u.username, r.nombreRol, ur.idRol
                   FROM usuarios u
                   LEFT JOIN usuario_rol ur ON u.idUsuario = ur.idUsuario
                   LEFT JOIN roles r ON ur.idRol = r.idRol
                   """)
    usuarios = cursor.fetchall()
    cursor.close()
    return render_template('dashboard.html', usuarios=usuarios)
    
#Editar usuario
@app.route('/actualizar/<int:id>', methods=['POST'])
def actualizar(id):
    nombre = request.form['nombre']
    apellido = request.form['apellido']
    correo = request.form['correo']
    rol = request.form['rol']
    
    cursor = mysql.connection.cursor()
    cursor.execute("""UPDATE usuarios SET nombre=%s, apellido=%s, username=%s WHERE idUsuario=%s""", (nombre, apellido, correo, id))
    cursor.execute("SELECT * FROM usuario_rol WHERE idUsuario=%s", (id,))
    existe = cursor.fetchone()
    
    if existe:
        cursor.execute("UPDATE usuario_rol SET idRol=%s WHERE idUsuario=%s", (rol, id))
    else:
        cursor.execute("INSERT INTO usuario_rol (idUsuario, idRol) VALUES (%s, %s)", (id, rol))
    mysql.connection.commit()
    cursor.close()
    flash('Usuario actualizado correctamente.')
    
    return redirect(url_for('dashboard'))

#Eliminar usuario
@app.route('/eliminar/<int:id>')
def eliminar(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM usuarios WHERE idUsuario=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash('Usuario eliminado correctamente.')
    
    return redirect(url_for('dashboard'))

# Inventario de productos
@app.route('/inventario')
def inventario():
    if 'usuario' not in session or session['rol'] != 'Admin':
        flash('Acceso restringido solo para los administradores.')
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    cursor.close()
    return render_template('inventario.html', productos=productos)

@app.route('/agregar_producto', methods=['GET', 'POST'])
def agregar_producto():
    if 'usuario' not in session or session['rol'] != 'Admin':
        flash('Acceso restringido solo para los administradores.')
        return redirect(url_for('login'))
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        cantidad = request.form['cantidad']
        imagen = request.files['imagen']
        
        filename = secure_filename(imagen.filename)
        imagen.save(os.path.join('static/uploads', filename))
    
        cursor = mysql.connection.cursor()
        cursor.execute("""
             INSERT INTO productos (nombre_producto, descripcion, precio, cantidad, imagen) 
             VALUES (%s, %s, %s, %s, %s)          
        """, (nombre, descripcion, precio, cantidad, filename))
        mysql.connection.commit()
        cursor.close()
        
        flash('Producto agregado correctamente.')
        return redirect(url_for('inventario'))
    return render_template('agregar_producto.html')

#editar producto
@app.route('/actualizarProducto/<int:id>', methods=['POST'])
def actualizarProducto(id):
    nombre = request.form['nombre']
    precio = request.form['precio']
    descripcion = request.form['descripcion']
    cantidad = request.form['cantidad']
    imagen = request.files['imagen']

    cursor = mysql.connection.cursor()
    
    if imagen and imagen.filename != '':
        filename = secure_filename(imagen.filename)
        imagen.save(os.path.join('static/uploads', filename))
    
        cursor.execute("""
            UPDATE productos SET nombre_producto=%s, 
                precio=%s,
                descripcion=%s, 
                cantidad=%s,
                imagen=%s
                WHERE idProducto=%s
            """, (nombre, precio, descripcion, cantidad, filename, id))
    else:
        cursor.execute("""
        UPDATE productos SET nombre_producto=%s, 
            precio=%s,
            descripcion=%s, 
            cantidad=%s
        WHERE idProducto=%s
    """, (nombre, precio, descripcion, cantidad, id))
    
    mysql.connection.commit()
    cursor.close()

    flash('Producto actualizado correctamente.')
    return redirect(url_for('inventario'))

#Eliminar producto
@app.route('/eliminarProducto/<int:id>')
def eliminarProducto(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM productos WHERE idProducto=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash('Producto eliminado correctamente.')

    return redirect(url_for('inventario'))

# Catálogo y carrito de compras
@app.route('/catalogo')
def catalogo():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor) #Asegura que los resultados sean diccionarios
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    cursor.close()
    return render_template('catalogo.html', productos=productos)


@app.route('/agregarCarrito/<int:id>', methods=['POST'])
def agregarCarrito(id):
    if 'usuario' not in session:
        flash('Debes iniciar sesión para agregar productos al carrito.')
        return redirect(url_for('login'))

    cantidad = int(request.form['cantidad'])
    idUsuario = session.get('idUsuario')
    
    cursor = mysql.connection.cursor()
    # Buscar si el usuario ya tiene un carrito
    cursor.execute("SELECT cantidad FROM productos WHERE idProducto = %s", (id,))
    stock = cursor.fetchone()[0]
    cursor.execute("SELECT idCarrito FROM carrito WHERE idUsuario = %s", (idUsuario,))
    carrito = cursor.fetchone()

    if not carrito:
        # Si no tiene, crear uno y obtener el id
        cursor.execute("INSERT INTO carrito (idUsuario) VALUES (%s)", (idUsuario,))
        mysql.connection.commit()
        cursor.execute("SELECT LAST_INSERT_ID()")
        #cursor.execute("SELECT idCarrito FROM carrito WHERE idUsuario = %s", (idUsuario,))
        carrito = cursor.fetchone()

    idCarrito = carrito[0]

    # Buscar si el producto ya está en el carrito
    cursor.execute("SELECT cantidad FROM detalle_carrito WHERE idCarrito = %s AND idProducto = %s", (idCarrito, id))
    existente = cursor.fetchone()
    cantidad_total = cantidad
    
    if existente:
        cantidad_total += existente[0]
        
    if cantidad_total > stock:
        flash(f'Solo hay {stock} unidades disponibles en stock.', "warning")
        cursor.close()
        return redirect(url_for('catalogo'))    

    if existente:
        nueva_cantidad = existente[0] + cantidad
        cursor.execute("UPDATE detalle_carrito SET cantidad = %s WHERE idCarrito = %s AND idProducto = %s", (nueva_cantidad, idCarrito, id))
    else:
        cursor.execute("INSERT INTO detalle_carrito (idCarrito, idProducto, cantidad) VALUES (%s, %s, %s)", (idCarrito, id, cantidad))

    mysql.connection.commit()
    cursor.close()

    flash('Producto agregado al carrito.')
    return redirect(url_for('catalogo'))


@app.route('/carrito')
def carrito():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para agregar productos al carrito.')
        return redirect(url_for('login'))

    idUsuario = session.get('idUsuario')
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
                   SELECT p.idProducto, p.nombre_producto, p.precio, p.imagen, dc.cantidad, p.cantidad AS stock
                   FROM detalle_carrito dc
                   JOIN carrito c ON dc.idCarrito = c.idCarrito
                   JOIN productos p ON dc.idProducto = p.idProducto
                   WHERE c.idUsuario = %s
                   """, (idUsuario,))
    productos_carrito = cursor.fetchall()
    cursor.close()
    
    total = sum(item['precio'] * item['cantidad'] for item in productos_carrito)
    
    return render_template('carrito.html', productos=productos_carrito, total=total)


@app.route('/actualizar_carrito/<int:id>', methods=['POST'])
def actualizar_carrito(id):
    accion = request.form.get('accion')
    cantidad_actual = int(request.form.get('cantidad_actual', 1))
    idUsuario = session.get('idUsuario')
    
    if accion == "sumar":
        nueva_cantidad = cantidad_actual + 1
    elif accion == "restar":
        nueva_cantidad = max(1, cantidad_actual - 1)
    else:
        nueva_cantidad = int(request.form.get('cantidad_manual', cantidad_actual))

    cursor = mysql.connection.cursor()
    
    cursor.execute("SELECT cantidad FROM productos WHERE idProducto = %s", (id,))
    stock = cursor.fetchone()[0]
    
    if nueva_cantidad > stock:
        flash(f'Solo hay {stock} unidades disponibles en stock.', "warning")
        cursor.close()
        return redirect(url_for('carrito'))
    if nueva_cantidad > 0:
        cursor.execute("""
                       UPDATE detalle_carrito dc
                       JOIN carrito c ON dc.idCarrito = c.idCarrito
                       SET dc.cantidad = %s
                       WHERE c.idUsuario = %s AND dc.idProducto = %s
                       """, (nueva_cantidad, idUsuario, id))
    else:
        cursor.execute("""
                       DELETE dc FROM detalle_carrito dc
                       JOIN carrito c ON dc.idCarrito = c.idCarrito
                       WHERE c.idUsuario = %s AND dc.idProducto = %s
                       """, (idUsuario, id))
    mysql.connection.commit()
    cursor.close()
    
    flash('Carrito actualizado.', "info")
    return redirect(url_for('carrito'))

@app.route('/eliminar_del_carrito/<int:id>')
def eliminar_del_carrito(id):
    idUsuario = session.get('idUsuario')
    cursor = mysql.connection.cursor()
    cursor.execute("""
                   DELETE dc FROM detalle_carrito dc
                   JOIN carrito c ON dc.idCarrito = c.idCarrito
                   WHERE c.idUsuario = %s AND dc.idProducto = %s
                   """, (idUsuario, id))
    mysql.connection.commit()
    cursor.close()
    flash('Producto eliminado del carrito.', "danger")
    return redirect(url_for('carrito'))

@app.route("/vaciar_carrito")
def vaciar_carrito():
    idUsuario = session.get('idUsuario')
    cursor = mysql.connection.cursor()
    cursor.execute("""
                   DELETE dc FROM detalle_carrito dc
                   JOIN carrito c ON dc.idCarrito = c.idCarrito
                   WHERE c.idUsuario = %s
                   """, (idUsuario,))
    mysql.connection.commit()
    cursor.close()
    flash('Carrito vaciado.', "warning")
    return redirect(url_for('carrito'))

# Context processor para contar items en el carrito
@app.context_processor
def contar_items_carrito():
    if 'idUsuario' in session:
        idUsuario = session['idUsuario']
        cursor = mysql.connection.cursor()
        cursor.execute("""
                    SELECT SUM(dc.cantidad) 
                    FROM detalle_carrito dc
                    JOIN carrito c ON dc.idCarrito = c.idCarrito
                    WHERE c.idUsuario = %s
                    """, (idUsuario,))
        cantidad = cursor.fetchone()[0]
        cursor.close()
        return dict(carrito_cantidad=cantidad if cantidad else 0)
    return dict(carrito_cantidad=0)

# Pago
@app.route('/pago', methods=['GET', 'POST'])
def pago():
    if 'usuario' not in session:
        flash('Debes iniciar sesión para agregar productos al carrito.')
        return redirect(url_for('login'))

    idUsuario = session.get('idUsuario')
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
                   SELECT p.idProducto, p.nombre_producto, p.precio, p.imagen, dc.cantidad, p.cantidad AS stock
                   FROM detalle_carrito dc
                   JOIN carrito c ON dc.idCarrito = c.idCarrito
                   JOIN productos p ON dc.idProducto = p.idProducto
                   WHERE c.idUsuario = %s
                   """, (idUsuario,))
    productos = cursor.fetchall()

    total = sum(p['precio'] * p['cantidad'] for p in productos)

    if request.method == 'POST':
        metodo = request.form.get('metodo_pago')
        errores = []
        for p in productos:
            if p['cantidad'] > p['stock']:
                errores.append(f'{p["nombre_producto"]} exede el stock disponeble.')
        if errores:
            flash("Error en el pago: " + ", ".join(errores), 'danger')
            return redirect(url_for('carrito')) 
        
        codigo_transaccion = f"TX-{random.randint(100000, 999999)}"
        flash(f"Pago realizado con {metodo}. Código de transacción: {codigo_transaccion}", 'success')
        
        for p in productos:
            nueva_cantidad = p['stock'] - p['cantidad']
            
            cursor.execute("""
                       UPDATE productos
                       SET cantidad = %s
                       WHERE idProducto = %s
                       """, (nueva_cantidad, p['idProducto']))
        
        cursor.execute("""
                       DELETE dc FROM detalle_carrito dc
                       JOIN carrito c ON dc.idCarrito = c.idCarrito
                          WHERE c.idUsuario = %s
                          """, (idUsuario,))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('confirmar_pago', metodo=metodo, codigo=codigo_transaccion, total=total))
    cursor.close()
    return render_template('pago.html', productos=productos, total=total)                   
           
@app.route('/confirmar_pago')
def confirmar_pago():
    metodo = request.args.get('metodo')
    codigo = request.args.get('codigo')
    total = request.args.get('total')
    return render_template('comfirmacion_pago.html', metodo=metodo, codigo=codigo, total=float(total))     


@app.route("/contacto")
def contacto():
    return render_template("contacto.html")

@app.route("/sobre_apifood")
def sobre_apifood():
    return render_template("sobre_apifood.html")

def pagina_no_encontrada(error):
    return render_template('errores/404.html'), 404

def contacto_no_disponible(error):
    return render_template('errores/405.html'), 405


# Ejecutar la aplicación
if __name__ == '__main__':
    app.register_error_handler(404, pagina_no_encontrada)
    app.register_error_handler(405, contacto_no_disponible)
    app.run(debug=True, host='0.0.0.0', port=3000)