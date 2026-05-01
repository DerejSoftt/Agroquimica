# Derej Agro - Sistema de Gestión Agroquímica

![Derej Agro](doc_img/Derej%20Agro.png)

## 📌 Descripción del Proyecto
**Derej Agro** es un sistema web integral desarrollado con Django, diseñado específicamente para la gestión eficiente de negocios agroquímicos. Permite la administración del inventario de productos químicos y fertilizantes, facturación, control de clientes y proveedores, y el manejo detallado de las finanzas mediante módulos de cuentas por cobrar y por pagar.

## 🚀 Características Principales

- **Gestión de Inventario:** Control detallado de productos agroquímicos (fertilizantes nitrogenados, fosfatados, micronutrientes, etc.), manejo de unidades (kg, litros, sacos) y control de costos y precios de venta (incluyendo impuestos e ITBIS y precios en USD).
- **Ventas y Facturación:** Sistema para procesar ventas al contado y a crédito. Emisión de facturas detalladas y exportación a PDF.
- **Manejo de Devoluciones:** Control de devoluciones de productos por diferentes motivos, con ajustes automáticos en el inventario y los saldos.
- **Cuentas por Cobrar y Pagar:** Control riguroso de deudas de clientes y obligaciones con proveedores, registro de pagos parciales/totales y manejo dinámico de estados (pendiente, pagado, vencido).
- **Gestión de Entidades:** Administración completa del directorio de Clientes y Suplidores/Proveedores.
- **Reportes y Analíticas:** Generación automática de reportes financieros, de inventario y facturas en formato PDF utilizando `xhtml2pdf` y `reportlab`.

## 🛠️ Tecnologías y Stack Técnico

- **Backend:** Python 3, Django 4.2.20
- **Base de Datos:** MySQL (`mysqlclient`)
- **Frontend:** HTML5, CSS3, JavaScript (AJAX para interactividad y peticiones asíncronas)
- **Generación de Reportes / PDF:** ReportLab, xhtml2pdf
- **Análisis de Datos:** Pandas, Numpy
- **Entorno / Configuración:** `python-dotenv` para la gestión de variables de entorno, `whitenoise` para archivos estáticos.

## ⚙️ Instalación y Configuración

Sigue estos pasos para desplegar el proyecto en un entorno de desarrollo local:

### 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd Agroquimica
```

### 2. Crear y activar un entorno virtual
```bash
python -m venv venv
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate
```

### 3. Instalar las dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar las Variables de Entorno
Crea un archivo `.env` en la raíz del proyecto (junto a `manage.py`) con las siguientes variables:
```env
SECRET_KEY=tu_clave_secreta_aqui
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
DB_NAME=agroquimica
DB_USER=root
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=3306
```

### 5. Configurar la Base de Datos
Asegúrate de tener un servidor MySQL en ejecución y crea una base de datos vacía (por ejemplo `agroquimica`, como configuraste en el archivo `.env`). Luego ejecuta las migraciones:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Crear un Superusuario (Administrador)
```bash
python manage.py createsuperuser
```

### 7. Ejecutar el Servidor de Desarrollo
```bash
python manage.py runserver
```
Accede al sistema desde tu navegador en `http://127.0.0.1:8000/`.

## 📂 Estructura del Proyecto

- `sistema/`: Carpeta de configuración principal del proyecto Django (`settings.py`, `urls.py`).
- `facturacion/`: Aplicación principal que contiene toda la lógica de negocio, modelos de base de datos (`models.py`), controladores (`views.py`) y el front-end.
- `facturacion/templates/`: Contiene las vistas en HTML del proyecto.
- `doc_img/`: Recursos y assets para la documentación técnica del proyecto.
- `static/`: Archivos estáticos como estilos CSS, JavaScript de front-end e imágenes de la interfaz.

## 🤝 Soporte y Contribución
Para reportar problemas o sugerir mejoras, por favor contactar al equipo de desarrollo de DerejSoftt o abrir un "Issue" en el repositorio correspondiente.
