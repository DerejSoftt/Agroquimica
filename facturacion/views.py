from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET, require_POST, require_http_methods
import json
from .models import Cliente, Suplidor, EntradaProducto , Compra, DetalleCompra,Venta, DetalleVenta, CuentaPorCobrar, PagoCuentaCobrar, Devolucion, ItemDevolucion
import re
from django.utils.decorators import method_decorator
from datetime import datetime
from django.core import serializers
from django.views.decorators.http import require_http_methods
from datetime import date
from django.db import transaction
from django.db.models import Q, Max
from django.db import models  
from datetime import date, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from django.http import HttpResponse
from decimal import Decimal
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.conf import settings

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from django.urls import reverse
from django.db.models import Q, Sum, Count, F
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
import pandas as pd
import numpy as np
from django.utils import timezone
from django.contrib.humanize.templatetags.humanize import intcomma
#==============================================================
#           Login 
#==============================================================
def index(request):
    # Si el usuario ya está autenticado, redirigir al inventario
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('inventario')
    return render(request, "facturacion/index.html")

def login_view(request):
    if request.method == 'POST':
        try:
            # Para requests AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                data = json.loads(request.body)
                username = data.get('username')
                password = data.get('password')
            else:
                # Para form submission tradicional
                username = request.POST.get('username')
                password = request.POST.get('password')
            
            # Autenticar usuario
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # Verificar si es superusuario
                if user.is_superuser:
                    login(request, user)
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True, 
                            'redirect_url': 'inventario'
                        })
                    else:
                        return redirect('inventario')
                else:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False, 
                            'error': 'No tiene permisos de superusuario'
                        }, status=403)
                    else:
                        return render(request, 'facturacion/index.html', {
                            'error': 'No tiene permisos de superusuario'
                        })
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False, 
                        'error': 'Credenciales inválidas'
                    }, status=401)
                else:
                    return render(request, 'facturacion/index.html', {
                        'error': 'Credenciales inválidas'
                    })
                    
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False, 
                    'error': 'Error del servidor'
                }, status=500)
            else:
                return render(request, 'facturacion/index.html', {
                    'error': 'Error del servidor'
                })
    
    # Si es GET, mostrar el formulario de login
    return redirect('index')

def logout_view(request):
    logout(request)
    return redirect('index')


#==============================================================
#           Inventario  de productos
#==============================================================
def inventario(request):
    # Obtener todos los productos ordenados por fecha de creación
    productos = EntradaProducto.objects.all().order_by('-fecha_creacion')
    
    # Procesar eliminación de producto
    if request.method == 'POST' and 'eliminar_id' in request.POST:
        producto_id = request.POST.get('eliminar_id')
        try:
            producto = EntradaProducto.objects.get(id=producto_id)
            producto.delete()
            messages.success(request, 'Producto eliminado exitosamente')
        except EntradaProducto.DoesNotExist:
            messages.error(request, 'Producto no encontrado')
        return redirect('inventario')
    
    # Procesar actualización de producto
    if request.method == 'POST' and 'actualizar_id' in request.POST:
        producto_id = request.POST.get('actualizar_id')
        try:
            producto = EntradaProducto.objects.get(id=producto_id)
            producto.producto = request.POST.get('producto')
            producto.categoria = request.POST.get('categoria')
            producto.cantidad = request.POST.get('cantidad')
            producto.unidad = request.POST.get('unidad')
            producto.precio_unitario = request.POST.get('precio_unitario')
            producto.precio_venta1_con_itbis = request.POST.get('precio_venta1_con_itbis')
            
            # Campos opcionales
            precio_venta2 = request.POST.get('precio_venta2_con_itbis')
            if precio_venta2:
                producto.precio_venta2_con_itbis = precio_venta2
                
            precio_venta3 = request.POST.get('precio_venta3_con_itbis')
            if precio_venta3:
                producto.precio_venta3_con_itbis = precio_venta3
            
            producto.save()
            messages.success(request, 'Producto actualizado exitosamente')
        except EntradaProducto.DoesNotExist:
            messages.error(request, 'Producto no encontrado')
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
        return redirect('inventario')
    
    return render(request, "facturacion/inventario.html", {'productos': productos})
#==============================================================
#          Registro de clientes
#==============================================================
def registrodeclientes(request):
    return render(request, "facturacion/registrodeclientes.html")
#==============================================================
#           GUARDAR CLIENTE
#==============================================================
@csrf_exempt
@require_POST
def guardar_cliente(request):
    try:
        data = json.loads(request.body)
        
        cedula = data.get('cedula', '').strip()
        nombre = data.get('nombre', '').strip()
        telefono1 = data.get('telefono1', '').strip()
        telefono2 = data.get('telefono2', '').strip()
        direccion = data.get('direccion', '').strip()
        limite_credito = data.get('limite_credito', 0)

        # Validaciones
        if not cedula:
            return JsonResponse({'success': False, 'message': 'La cédula es obligatoria'})
        
        if not validar_cedula(cedula):
            return JsonResponse({'success': False, 'message': 'Formato de cédula inválido. Use: 000-0000000-0'})
        
        if Cliente.objects.filter(cedula=cedula).exists():
            return JsonResponse({'success': False, 'message': 'Esta cédula ya está registrada'})

        if not nombre:
            return JsonResponse({'success': False, 'message': 'El nombre es obligatorio'})
        
        if not telefono1:
            return JsonResponse({'success': False, 'message': 'El teléfono 1 es obligatorio'})

        if not direccion:
            return JsonResponse({'success': False, 'message': 'La dirección es obligatoria'})

        if limite_credito < 0:
            return JsonResponse({'success': False, 'message': 'El límite de crédito no puede ser negativo'})

        # Crear cliente
        cliente = Cliente(
            cedula=cedula,
            nombre=nombre,
            telefono1=telefono1,
            telefono2=telefono2 if telefono2 else None,
            direccion=direccion,
            limite_credito=limite_credito
        )
        cliente.save()

        return JsonResponse({
            'success': True, 
            'message': 'Cliente registrado exitosamente'
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al guardar cliente: {str(e)}'})
#==============================================================
#           VALIDAR CEDULA CLIENTE
#==============================================================
def validar_cedula(cedula):
    # Validar formato de cédula dominicana: 000-0000000-0
    patron = r'^\d{3}-\d{7}-\d{1}$'
    return re.match(patron, cedula) is not None


#==============================================================
#           REGISTRO  DE CLIENTES
#==============================================================
def gestiondeclientes(request):
    return render(request, "facturacion/gestiondeclientes.html")
#==============================================================
#         OBTENER CLIENTES
#==============================================================
@require_GET
def obtener_clientes(request):
    try:
        clientes = Cliente.objects.all().order_by('-fecha_registro')
        
        clientes_data = []
        for cliente in clientes:
            clientes_data.append({
                'id': cliente.id,
                'cedula': cliente.cedula,
                'nombre': cliente.nombre,
                'telefono1': cliente.telefono1,
                'telefono2': cliente.telefono2 or '',
                'direccion': cliente.direccion,
                'limite_credito': float(cliente.limite_credito),
                'fecha_registro': cliente.fecha_registro.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return JsonResponse({'success': True, 'clientes': clientes_data})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al obtener clientes: {str(e)}'})
#==============================================================
#          ACTUALIZAR  CLIENTE
#==============================================================
@csrf_exempt
@require_POST
def actualizar_cliente(request, cliente_id):
    try:
        data = json.loads(request.body)
        
        cedula = data.get('cedula', '').strip()
        nombre = data.get('nombre', '').strip()
        telefono1 = data.get('telefono1', '').strip()
        telefono2 = data.get('telefono2', '').strip()
        direccion = data.get('direccion', '').strip()
        limite_credito = data.get('limite_credito', 0)

        # Validaciones
        if not cedula:
            return JsonResponse({'success': False, 'message': 'La cédula es obligatoria'})
        
        if not validar_cedula(cedula):
            return JsonResponse({'success': False, 'message': 'Formato de cédula inválido. Use: 000-0000000-0'})
        
        # Verificar si la cédula ya existe en otro cliente
        if Cliente.objects.filter(cedula=cedula).exclude(id=cliente_id).exists():
            return JsonResponse({'success': False, 'message': 'Esta cédula ya está registrada en otro cliente'})

        if not nombre:
            return JsonResponse({'success': False, 'message': 'El nombre es obligatorio'})
        
        if not telefono1:
            return JsonResponse({'success': False, 'message': 'El teléfono 1 es obligatorio'})

        if not direccion:
            return JsonResponse({'success': False, 'message': 'La dirección es obligatoria'})

        if limite_credito < 0:
            return JsonResponse({'success': False, 'message': 'El límite de crédito no puede ser negativo'})

        # Actualizar cliente
        cliente = Cliente.objects.get(id=cliente_id)
        cliente.cedula = cedula
        cliente.nombre = nombre
        cliente.telefono1 = telefono1
        cliente.telefono2 = telefono2 if telefono2 else None
        cliente.direccion = direccion
        cliente.limite_credito = limite_credito
        cliente.save()

        return JsonResponse({
            'success': True, 
            'message': 'Cliente actualizado exitosamente'
        })

    except Cliente.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Cliente no encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al actualizar cliente: {str(e)}'})

@csrf_exempt
@require_http_methods(["DELETE"])
#==============================================================
#           ELIMINAR  CLIENTE
#==============================================================
def eliminar_cliente(request, cliente_id):
    try:
        cliente = Cliente.objects.get(id=cliente_id)
        cliente.delete()
        
        return JsonResponse({
            'success': True, 
            'message': 'Cliente eliminado exitosamente'
        })

    except Cliente.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Cliente no encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al eliminar cliente: {str(e)}'})
    


#==============================================================
#          REGISTRO DE SUPLIDORES
#==============================================================
def resgistrodesuplidores(request):
    return render(request, "facturacion/resgistrodesuplidores.html")

#==============================================================
#           GUARDAR SUPLIDOR
#==============================================================
@csrf_exempt
@require_POST
def guardar_suplidor(request):
    try:
        data = json.loads(request.body)
        
        # Validar que el RNC no exista
        if Suplidor.objects.filter(rnc=data.get('rnc')).exists():
            return JsonResponse({'success': False, 'message': 'Este RNC ya está registrado'})

        suplidor = Suplidor(
            nombre=data.get('nombre'),
            rnc=data.get('rnc'),
            telefono=data.get('telefono'),
            email=data.get('email'),
            direccion=data.get('direccion'),
            contacto=data.get('contacto'),
            categoria=data.get('categoria'),
            terminos_pago=data.get('terminos_pago'),
            estado=data.get('estado'),
            notas=data.get('notas')
        )
        suplidor.save()

        return JsonResponse({'success': True, 'message': 'Suplidor registrado exitosamente'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al guardar suplidor: {str(e)}'})
    


#==============================================================
#          GESTION DE SUPLIDORES
#==============================================================
def gestiondesuplidores(request):
    return render(request, "facturacion/gestiondesuplidores.html")

#==============================================================
#          OBTENER SUPLIDORES
#==============================================================
@require_GET
def obtener_suplidores(request):
    try:
        suplidores = Suplidor.objects.all().order_by('-fecha_registro')
        
        suplidores_data = []
        for suplidor in suplidores:
            suplidores_data.append({
                'id': suplidor.id,
                'nombre': suplidor.nombre,
                'rnc': suplidor.rnc,
                'telefono': suplidor.telefono,
                'email': suplidor.email,
                'direccion': suplidor.direccion,
                'contacto': suplidor.contacto,
                'categoria': suplidor.categoria,
                'terminos_pago': suplidor.terminos_pago,
                'estado': suplidor.estado,
                'notas': suplidor.notas,
                'fecha_registro': suplidor.fecha_registro.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return JsonResponse({'success': True, 'suplidores': suplidores_data})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al obtener suplidores: {str(e)}'})

#==============================================================
#          ACTUALIZAR SUPLIDOR
#==============================================================
@csrf_exempt
@require_POST
def actualizar_suplidor(request, suplidor_id):
    try:
        data = json.loads(request.body)
        
        nombre = data.get('nombre', '').strip()
        rnc = data.get('rnc', '').strip()
        telefono = data.get('telefono', '').strip()
        email = data.get('email', '').strip()
        direccion = data.get('direccion', '').strip()
        contacto = data.get('contacto', '').strip()
        categoria = data.get('categoria', '')
        terminos_pago = data.get('terminos_pago', '30dias')
        estado = data.get('estado', 'activo')
        notas = data.get('notas', '').strip()

        # Validaciones
        if not nombre:
            return JsonResponse({'success': False, 'message': 'El nombre del suplidor es obligatorio'})
        
        if not rnc:
            return JsonResponse({'success': False, 'message': 'El RNC es obligatorio'})
        
        # Verificar si el RNC ya existe en otro suplidor
        if Suplidor.objects.filter(rnc=rnc).exclude(id=suplidor_id).exists():
            return JsonResponse({'success': False, 'message': 'Este RNC ya está registrado en otro suplidor'})

        if not telefono:
            return JsonResponse({'success': False, 'message': 'El teléfono es obligatorio'})

        if not email:
            return JsonResponse({'success': False, 'message': 'El email es obligatorio'})

        if not direccion:
            return JsonResponse({'success': False, 'message': 'La dirección es obligatoria'})

        if not categoria:
            return JsonResponse({'success': False, 'message': 'La categoría es obligatoria'})

        # Validar formato de email
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return JsonResponse({'success': False, 'message': 'Formato de email inválido'})

        # Actualizar suplidor
        suplidor = Suplidor.objects.get(id=suplidor_id)
        suplidor.nombre = nombre
        suplidor.rnc = rnc
        suplidor.telefono = telefono
        suplidor.email = email
        suplidor.direccion = direccion
        suplidor.contacto = contacto if contacto else None
        suplidor.categoria = categoria
        suplidor.terminos_pago = terminos_pago
        suplidor.estado = estado
        suplidor.notas = notas if notas else None
        suplidor.save()

        return JsonResponse({
            'success': True, 
            'message': 'Suplidor actualizado exitosamente'
        })

    except Suplidor.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Suplidor no encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al actualizar suplidor: {str(e)}'})

#==============================================================
#          ELIMINAR SUPLIDOR
#==============================================================
@csrf_exempt
@require_http_methods(["DELETE"])
def eliminar_suplidor(request, suplidor_id):
    try:
        suplidor = Suplidor.objects.get(id=suplidor_id)
        suplidor.delete()
        
        return JsonResponse({
            'success': True, 
            'message': 'Suplidor eliminado exitosamente'
        })

    except Suplidor.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Suplidor no encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error al eliminar suplidor: {str(e)}'})
    


#==============================================================
#           ENTRADA DE PRODUCTOS
#==============================================================
def entrada(request):
    # Obtener todos los suplidores activos para el dropdown
    suplidores = Suplidor.objects.filter(estado='activo')  # Filtramos por estado 'activo'
    
    context = {
        'proveedores': suplidores  # Mantenemos el nombre 'proveedores' en el contexto para el template
    }
    
    return render(request, "facturacion/entrada.html", context)

#==============================================================
#           GUARDAR ENTRADA DE PRODUCTOS
#==============================================================
@csrf_exempt
def guardar_entrada(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validar campos requeridos (sin invoiceNumber)
            campos_requeridos = ['entryDate', 'supplier', 'product', 
                               'category', 'quantity', 'unit', 'unitPrice', 'salePrice1']
            
            for campo in campos_requeridos:
                if not data.get(campo):
                    return JsonResponse({
                        'success': False, 
                        'error': f'El campo {campo} es requerido'
                    })
            
            # ELIMINADO: Verificación de número de factura duplicado
            # if EntradaProducto.objects.filter(numero_factura=data['invoiceNumber']).exists():
            #     return JsonResponse({
            #         'success': False,
            #         'error': 'Ya existe una entrada con este número de factura'
            #     })
            
            # Obtener el suplidor (proveedor)
            try:
                suplidor = Suplidor.objects.get(id=data['supplier'], estado='activo')
            except Suplidor.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'El suplidor seleccionado no existe o no está activo'
                })
            
            # Calcular precios con ITBIS
            itbis_rate = float(data.get('itbisRate', 18.00))
            itbis_multiplier = 1 + (itbis_rate / 100)
            
            precio_venta1 = float(data['salePrice1'])
            precio_venta2 = float(data.get('salePrice2', 0))
            precio_venta3 = float(data.get('salePrice3', 0))
            
            precio_venta1_con_itbis = precio_venta1 * itbis_multiplier
            precio_venta2_con_itbis = precio_venta2 * itbis_multiplier if precio_venta2 > 0 else 0
            precio_venta3_con_itbis = precio_venta3 * itbis_multiplier if precio_venta3 > 0 else 0
            
            # Crear la entrada de producto (sin numero_factura)
            entrada = EntradaProducto(
                # numero_factura=data['invoiceNumber'],  # ELIMINADO
                fecha=data['entryDate'],
                proveedor=suplidor,
                producto=data['product'],
                categoria=data['category'],
                cantidad=data['quantity'],
                unidad=data['unit'],
                precio_unitario=data['unitPrice'],
                precio_venta1=precio_venta1,
                precio_venta2=precio_venta2 if precio_venta2 > 0 else None,
                precio_venta3=precio_venta3 if precio_venta3 > 0 else None,
                precio_venta1_con_itbis=precio_venta1_con_itbis,
                precio_venta2_con_itbis=precio_venta2_con_itbis if precio_venta2 > 0 else None,
                precio_venta3_con_itbis=precio_venta3_con_itbis if precio_venta3 > 0 else None,
                itbis_porcentaje=itbis_rate
            )
            
            entrada.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Entrada de producto guardada exitosamente',
                'id': entrada.id,
                'precios_con_itbis': {
                    'precio1': round(precio_venta1_con_itbis, 2),
                    'precio2': round(precio_venta2_con_itbis, 2) if precio_venta2 > 0 else None,
                    'precio3': round(precio_venta3_con_itbis, 2) if precio_venta3 > 0 else None
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al guardar la entrada: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    })


#==============================================================
#           COMPRAS DE PRODUCTOS
#==============================================================
def compras(request):
    # Obtener suplidores y productos para el template
    suplidores = Suplidor.objects.filter(estado='activo')
    productos = EntradaProducto.objects.all()
    
    context = {
        'suplidores': suplidores,
        'productos': productos,
    }
    return render(request, "facturacion/compras.html", context)

#==============================================================
#          GUARDAR COMPRA DE PRODUCTOS
#==============================================================
@csrf_exempt
def guardar_compra(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Validaciones básicas
            required_fields = ['condicion', 'numeroFactura', 'fecha', 'proveedorId']
            if not all(data.get(field) for field in required_fields):
                return JsonResponse({'success': False, 'error': 'Faltan campos requeridos'})
            
            if not data.get('productos'):
                return JsonResponse({'success': False, 'error': 'Debe agregar al menos un producto'})
            
            # Verificar número de factura único
            if Compra.objects.filter(numero_factura=data['numeroFactura']).exists():
                return JsonResponse({'success': False, 'error': 'Esta factura ya ha sido registrada anteriormente'})
            
            # Convertir la fecha de string a objeto date
            try:
                fecha_factura = datetime.strptime(data['fecha'], '%Y-%m-%d').date()
            except ValueError as e:
                return JsonResponse({'success': False, 'error': f'Formato de fecha inválido: {str(e)}'})
            
            # Crear la compra
            compra = Compra(
                suplidor_id=data['proveedorId'],
                numero_factura=data['numeroFactura'],
                fecha_factura=fecha_factura,
                condicion=data['condicion'],
                total=0,
                estado='pagado' if data['condicion'].lower() == 'contado' else 'pendiente'
            )
            compra.save()
            
            # Procesar productos
            total_compra = 0
            for producto_data in data['productos']:
                try:
                    producto = EntradaProducto.objects.get(id=producto_data['id'])
                    
                    # Crear detalle
                    detalle = DetalleCompra(
                        compra=compra,
                        producto=producto,
                        cantidad=producto_data['cantidad'],
                        costo_unitario=producto_data['costoUnitario'],
                        subtotal=producto_data['subtotal']
                    )
                    detalle.save()
                    
                    # Actualizar inventario
                    producto.cantidad += producto_data['cantidad']
                    producto.save()
                    
                    total_compra += producto_data['subtotal']
                    
                except EntradaProducto.DoesNotExist:
                    print(f"Producto ID {producto_data['id']} no encontrado")
            
            # Actualizar total de la compra
            compra.total = total_compra
            compra.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Compra {compra.numero_factura} registrada exitosamente',
                'compra_id': compra.id
            })
            
        except Exception as e:
            print(f"Error: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'error': f'Error: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


#==============================================================
#          CUENTAS POR PAGAR
#==============================================================
def cuantaporpagar(request):
    """Vista principal para gestión de cuentas por pagar"""
    return render(request, "facturacion/cuantaporpagar.html")


#==============================================================
#         CUENTAS POR PAGAR DATOS
#==============================================================
@require_http_methods(["GET"])
def cuentas_por_pagar_datos(request):
    """API endpoint para obtener datos de compras - MEJORADA"""
    try:
        # Optimizar la consulta con prefetch_related
        compras = Compra.objects.all().order_by('-fecha_factura').select_related('suplidor').prefetch_related('detalles__producto')
        compras_data = []
        hoy = date.today()
        
        for compra in compras:
            try:
                estado = compra.estado
                if estado == 'Pendiente' and compra.fecha_vencimiento:
                    if compra.fecha_vencimiento < hoy:
                        estado = 'Vencido'
                
                # Obtener productos usando el nuevo método del modelo
                productos = []
                for detalle in compra.detalles.all():
                    productos.append(detalle.get_info_producto())
                
                compras_data.append({
                    'id': compra.id,
                    'numero_factura': compra.numero_factura or 'N/A',
                    'fecha_factura': compra.fecha_factura.isoformat() if compra.fecha_factura else None,
                    'fecha_vencimiento': compra.fecha_vencimiento.isoformat() if compra.fecha_vencimiento else None,
                    'suplidor_nombre': compra.suplidor.nombre if compra.suplidor else 'Proveedor no disponible',
                    'condicion': compra.condicion or 'N/A',
                    'total': float(compra.total) if compra.total else 0.0,
                    'estado': estado,
                    'fecha_pago': compra.fecha_pago.isoformat() if compra.fecha_pago else None,
                    'metodo_pago': compra.metodo_pago or '',
                    'referencia_pago': compra.referencia_pago or '',
                    'productos': productos,
                    'notas': compra.notas or ''  # Para edición
                })
                
            except Exception as e:
                print(f"❌ Error procesando compra {compra.id}: {e}")
                # Incluir compra con datos básicos incluso si hay error en detalles
                compras_data.append({
                    'id': compra.id,
                    'numero_factura': compra.numero_factura or 'N/A',
                    'fecha_factura': compra.fecha_factura.isoformat() if compra.fecha_factura else None,
                    'suplidor_nombre': compra.suplidor.nombre if compra.suplidor else 'Proveedor no disponible',
                    'condicion': compra.condicion or 'N/A',
                    'total': float(compra.total) if compra.total else 0.0,
                    'estado': estado,
                    'productos': [{'nombre': 'Error al cargar productos', 'cantidad': 0, 'costo_unitario': 0, 'subtotal': 0}]
                })
        
        return JsonResponse(compras_data, safe=False)
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

#==============================================================
#          OBTENER COMPRA PARA EDICION
# Para obtener datos de una compra específica para edición
#==============================================================
@require_http_methods(["GET"])
def obtener_compra_edicion(request, compra_id):
    """Obtener datos de una compra específica para edición"""
    try:
        compra = Compra.objects.get(id=compra_id)
        
        datos_compra = {
            'id': compra.id,
            'numero_factura': compra.numero_factura,
            'fecha_factura': compra.fecha_factura.isoformat(),
            'fecha_vencimiento': compra.fecha_vencimiento.isoformat() if compra.fecha_vencimiento else None,
            'suplidor_id': compra.suplidor.id,
            'suplidor_nombre': compra.suplidor.nombre,
            'condicion': compra.condicion,
            'total': float(compra.total),
            'estado': compra.estado,
            'notas': compra.notas or '',
            'productos': [detalle.get_info_producto() for detalle in compra.detalles.all()]
        }
        
        return JsonResponse({'success': True, 'compra': datos_compra})
        
    except Compra.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Compra no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
#==============================================================
#         ACTUALIZAR COMPRA PARA ACTUALIZACION LA COMPRA
#==============================================================
@csrf_exempt
@require_http_methods(["POST"])
def actualizar_compra(request, compra_id):
    """Actualizar una compra existente"""
    try:
        with transaction.atomic():
            compra = Compra.objects.get(id=compra_id)
            data = json.loads(request.body)
            
            # Validar que no esté pagada para editar
            if compra.estado == 'Pagado':
                return JsonResponse({
                    'success': False, 
                    'error': 'No se puede editar una compra ya pagada'
                }, status=400)
            
            # Actualizar campos básicos
            compra.numero_factura = data.get('numero_factura', compra.numero_factura)
            compra.fecha_factura = data.get('fecha_factura')
            compra.fecha_vencimiento = data.get('fecha_vencimiento')
            compra.condicion = data.get('condicion', compra.condicion)
            compra.notas = data.get('notas', compra.notas)
            
            # Recalcular estado si es necesario
            if compra.condicion == 'Contado':
                compra.estado = 'Pagado'
            elif compra.condicion == 'Crédito':
                if compra.fecha_vencimiento and compra.fecha_vencimiento < date.today():
                    compra.estado = 'Vencido'
                else:
                    compra.estado = 'Pendiente'
            
            compra.save()
            
            return JsonResponse({
                'success': True, 
                'message': 'Compra actualizada exitosamente',
                'compra_id': compra.id
            })
            
    except Compra.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Compra no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

#==============================================================
#          PROCESAR PAGO DE COMPRA
#==============================================================
@csrf_exempt
@require_http_methods(["POST"])
def procesar_pago_compra(request, compra_id):
    """Procesar el pago de una compra"""
    try:
        with transaction.atomic():
            compra = Compra.objects.get(id=compra_id)
            data = json.loads(request.body)
            
            # Validaciones
            if compra.estado == 'Pagado':
                return JsonResponse({
                    'success': False, 
                    'error': 'Esta compra ya ha sido pagada'
                }, status=400)
            
            fecha_pago_str = data.get('fecha_pago')
            if not fecha_pago_str:
                return JsonResponse({
                    'success': False, 
                    'error': 'La fecha de pago es requerida'
                }, status=400)
            
            # Convertir fecha de string a date
            try:
                fecha_pago = date.fromisoformat(fecha_pago_str)
            except ValueError:
                return JsonResponse({
                    'success': False, 
                    'error': 'Formato de fecha inválido'
                }, status=400)
            
            # Actualizar compra
            compra.estado = 'Pagado'
            compra.fecha_pago = fecha_pago
            compra.metodo_pago = data.get('metodo_pago', 'Efectivo')
            compra.referencia_pago = data.get('referencia_pago', '')
            compra.save()
            
            print(f"✅ Pago procesado para compra {compra.numero_factura}")
            
            return JsonResponse({
                'success': True, 
                'message': 'Pago registrado exitosamente',
                'compra_id': compra.id
            })
            
    except Compra.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': 'Compra no encontrada'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False, 
            'error': 'Datos JSON inválidos'
        }, status=400)
    except Exception as e:
        print(f"❌ Error al procesar pago: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': f'Error al procesar el pago: {str(e)}'
        }, status=500)

#==============================================================
#           ELIMINAR COMPRA
#==============================================================
@csrf_exempt
@require_http_methods(["POST"])
def eliminar_compra(request, compra_id):
    """Eliminar una compra (solo si está pagada)"""
    try:
        with transaction.atomic():
            compra = Compra.objects.get(id=compra_id)
            
            # Solo permitir eliminar compras pagadas
            if compra.estado != 'Pagado':
                return JsonResponse({
                    'success': False, 
                    'error': 'Solo se pueden eliminar compras pagadas'
                }, status=400)
            
            numero_factura = compra.numero_factura
            compra.delete()
            
            print(f"🗑️ Compra {numero_factura} eliminada")
            
            return JsonResponse({
                'success': True, 
                'message': f'Compra {numero_factura} eliminada exitosamente'
            })
            
    except Compra.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'error': 'Compra no encontrada'
        }, status=404)
    except Exception as e:
        print(f"❌ Error al eliminar compra: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': f'Error al eliminar la compra: {str(e)}'
        }, status=500)



#==============================================================
#           Inventario  de productos
#==============================================================




#==============================================================
#           facturacion 




def facturacion(request):
    productos = EntradaProducto.objects.filter(cantidad__gt=0)
    clientes = Cliente.objects.all()
    
    # Convertir productos a formato JSON para el template
    productos_json = []
    for producto in productos:
        productos_json.append({
            'id': producto.id,
            'nombre': producto.producto,
            'categoria': producto.categoria,
            'precio1': float(producto.precio_venta1_con_itbis),
            'precio2': float(producto.precio_venta2_con_itbis) if producto.precio_venta2_con_itbis else float(producto.precio_venta1_con_itbis),
            'precio3': float(producto.precio_venta3_con_itbis) if producto.precio_venta3_con_itbis else float(producto.precio_venta1_con_itbis),
            'stock': float(producto.cantidad)
        })
    
    context = {
        'productos_json': json.dumps(productos_json),
        'clientes': clientes,
    }
    return render(request, "facturacion/facturacion.html", context)

@csrf_exempt
def buscar_clientes(request):
    if request.method == 'POST':
        search_term = request.POST.get('search_term', '')
        clientes = Cliente.objects.filter(
            models.Q(nombre__icontains=search_term) | 
            models.Q(cedula__icontains=search_term) |
            models.Q(telefono1__icontains=search_term) |
            models.Q(telefono2__icontains=search_term)
        )[:10]
        
        resultados = []
        for cliente in clientes:
            resultados.append({
                'id': cliente.id,
                'cedula': cliente.cedula,
                'nombre': cliente.nombre,
                'telefono': cliente.telefono1,
                'limite_credito': float(cliente.limite_credito)
            })
        
        return JsonResponse({'clientes': resultados})


@csrf_exempt
def procesar_venta(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("Datos recibidos:", data)  # Para debug
            
            with transaction.atomic():
                # Validar datos requeridos
                if not data.get('items'):
                    return JsonResponse({
                        'success': False,
                        'error': 'No hay productos en la venta'
                    })
                
                # Crear la venta
                venta = Venta(
                    cliente_id=data.get('cliente_id'),
                    cliente_nombre=data.get('cliente_nombre'),  # Nuevo campo
                    tipo_venta=data['tipo_venta'],
                    metodo_pago=data['metodo_pago'],
                    subtotal=float(data['subtotal']),
                    descuento=float(data['descuento']),
                    total=float(data['total']),
                    observacion=data.get('observacion', '')
                )
                venta.save()
                
                print(f"Factura creada: {venta.numero_factura}")
                
                # Crear detalles de venta y actualizar stock
                for item in data['items']:
                    try:
                        producto = EntradaProducto.objects.get(id=item['producto_id'])
                    except EntradaProducto.DoesNotExist:
                        return JsonResponse({
                            'success': False,
                            'error': f'Producto con ID {item["producto_id"]} no encontrado'
                        })
                    
                    # Verificar stock suficiente
                    if producto.cantidad < item['cantidad']:
                        return JsonResponse({
                            'success': False,
                            'error': f'Stock insuficiente para {producto.producto}. Stock disponible: {producto.cantidad}'
                        })
                    
                    # Crear detalle
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=item['cantidad'],
                        precio_unitario=item['precio_unitario'],
                        subtotal=item['subtotal']
                    )
                    
                    # Actualizar stock
                    producto.cantidad -= item['cantidad']
                    producto.save()
                
                # CREAR CUENTA POR COBRAR SI ES VENTA A CRÉDITO
                if data['tipo_venta'] == 'credito' and data.get('cliente_id'):
                    try:
                        cliente = Cliente.objects.get(id=data['cliente_id'])
                        fecha_vencimiento = date.today() + timedelta(days=30)
                        
                        CuentaPorCobrar.objects.create(
                            venta=venta,
                            cliente=cliente,
                            fecha_vencimiento=fecha_vencimiento,
                            monto_total=float(data['total']),
                            saldo_pendiente=float(data['total']),
                            estado='pendiente',
                            observaciones=data.get('observacion', '')
                        )
                    except Cliente.DoesNotExist:
                        pass
                
                return JsonResponse({
                    'success': True,
                    'venta_id': venta.id,
                    'numero_factura': venta.numero_factura,
                    'redirect_url': f'/facturas/{venta.id}/'
                })
                
        except Exception as e:
            print("Error completo:", str(e))
            return JsonResponse({
                'success': False,
                'error': f'Error al procesar la venta: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})



def factura_detalle(request, venta_id):
    try:
        venta = Venta.objects.get(id=venta_id)
        detalles = venta.detalles.all()
        
        context = {
            'venta': venta,
            'detalles': detalles,
        }
        return render(request, "facturacion/factura_detalle.html", context)
    except Venta.DoesNotExist:
        return render(request, "404.html", status=404)
#==============================================================





def cuentaporcobrar(request):
    return render(request, "facturacion/cuentaporcobrar.html")  



@csrf_exempt
def api_cuentas_por_cobrar(request):
    if request.method == 'GET':
        try:
            # Optimizar la consulta con prefetch_related para detalles y productos
            cuentas = CuentaPorCobrar.objects.select_related(
                'cliente', 'venta'
            ).prefetch_related(
                'pagos',
                'venta__detalles__producto'
            ).exclude(estado='anulada').filter(saldo_pendiente__gt=0)
            
            data = []
            for cuenta in cuentas:
                # Verificar vencimiento
                if date.today() > cuenta.fecha_vencimiento and cuenta.estado not in ['pagada', 'vencida']:
                    cuenta.estado = 'vencida'
                    cuenta.save()
                
                # Obtener productos de la venta
                productos = []
                try:
                    if cuenta.venta:
                        detalles_venta = cuenta.venta.detalles.all()
                        for detalle in detalles_venta:
                            productos.append({
                                'nombre': detalle.producto.producto if detalle.producto else 'Producto no disponible',
                                'cantidad': float(detalle.cantidad),
                                'precio': float(detalle.precio_unitario)
                            })
                    else:
                        productos = [{'nombre': 'Venta no disponible', 'cantidad': 1, 'precio': float(cuenta.monto_total)}]
                except Exception as e:
                    productos = [{'nombre': f'Error: {str(e)}', 'cantidad': 1, 'precio': float(cuenta.monto_total)}]
                
                # Obtener información del cliente
                client_name = getattr(cuenta.cliente, 'nombre', 'Cliente no disponible') if cuenta.cliente else 'Cliente no disponible'
                client_phone = getattr(cuenta.cliente, 'telefono1', 'No disponible') if cuenta.cliente else 'No disponible'
                client_id = getattr(cuenta.cliente, 'id', None) if cuenta.cliente else None
                
                # Obtener pagos de esta cuenta
                pagos = []
                for pago in cuenta.pagos.all():
                    pagos.append({
                        'id': pago.id,
                        'numero_recibo': pago.numero_recibo or 'N/A',
                        'monto_pagado': float(pago.monto_pagado),
                        'fecha_pago': pago.fecha_pago.strftime('%Y-%m-%d'),
                        'metodo_pago': pago.metodo_pago,
                        'referencia': pago.observaciones or '',
                        'estado': pago.estado
                    })
                
                data.append({
                    'id': cuenta.id,
                    'clientId': client_id,
                    'clientName': client_name,
                    'clientPhone': client_phone,
                    'invoiceNumber': cuenta.venta.numero_factura if cuenta.venta else f"CTA-{cuenta.id:05d}",
                    'products': productos,
                    'saleDate': cuenta.fecha_emision.strftime('%Y-%m-%d'),
                    'dueDate': cuenta.fecha_vencimiento.strftime('%Y-%m-%d'),
                    'totalAmount': float(cuenta.monto_total),
                    'paidAmount': float(cuenta.monto_total - cuenta.saldo_pendiente),
                    'pendingBalance': float(cuenta.saldo_pendiente),
                    'status': cuenta.estado,
                    'observations': cuenta.observaciones or '',
                    'pagos': pagos
                })
            
            return JsonResponse(data, safe=False)
            
        except Exception as e:
            import traceback
            print(f"Error en GET: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({'error': f'Error al cargar datos: {str(e)}'}, status=500)
    
    elif request.method == 'POST':
        try:
            # Parsear los datos del pago
            data = json.loads(request.body)
            cuenta_id = data.get('cuenta_id')
            monto_pagado = data.get('monto_pagado')
            metodo_pago = data.get('metodo_pago')
            referencia = data.get('referencia', '')
            
            print(f"🔍 DEBUG: Procesando pago - cuenta_id={cuenta_id}, monto={monto_pagado}, metodo={metodo_pago}, referencia={referencia}")
            
            # Validar datos requeridos
            if not cuenta_id or not monto_pagado or not metodo_pago:
                return JsonResponse({
                    'success': False,
                    'error': 'Faltan datos requeridos: cuenta_id, monto_pagado, metodo_pago'
                }, status=400)
            
            # Obtener la cuenta por cobrar
            try:
                cuenta = CuentaPorCobrar.objects.get(id=cuenta_id)
                print(f"🔍 DEBUG: Cuenta encontrada - ID: {cuenta.id}, Saldo pendiente: {cuenta.saldo_pendiente}, Estado: {cuenta.estado}")
            except CuentaPorCobrar.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Cuenta por cobrar con ID {cuenta_id} no existe'
                }, status=404)
            
            # Validar que la cuenta no esté pagada
            if cuenta.estado == 'pagada':
                return JsonResponse({
                    'success': False,
                    'error': 'Esta cuenta ya está completamente pagada'
                }, status=400)
            
            # Validar que el monto no exceda el saldo pendiente
            monto_pagado_decimal = Decimal(str(monto_pagado))
            if monto_pagado_decimal > cuenta.saldo_pendiente:
                return JsonResponse({
                    'success': False,
                    'error': f'El monto pagado (${monto_pagado}) excede el saldo pendiente (${cuenta.saldo_pendiente})'
                }, status=400)
            
            # CORRECCIÓN: Usar transacción atómica para garantizar la consistencia
            from django.db import transaction
            
            with transaction.atomic():
                print(f"🔍 DEBUG: Creando objeto PagoCuentaCobrar...")
                
                # Crear el pago - CORREGIDO: No establecer fecha_creacion manualmente
                pago = PagoCuentaCobrar(
                    cuenta=cuenta,
                    monto_pagado=monto_pagado_decimal,
                    metodo_pago=metodo_pago,
                    observaciones=referencia,
                    fecha_pago=date.today()
                    # fecha_creacion se establecerá automáticamente por auto_now_add=True
                )
                
                print(f"🔍 DEBUG: Objeto pago creado - ID: {pago.id}, Número Recibo: {pago.numero_recibo}")
                
                # Guardar el pago para que se genere el número de recibo automáticamente
                pago.save()
                print(f"🔍 DEBUG: Pago guardado - ID: {pago.id}, Número Recibo: {pago.numero_recibo}")
                
                # Actualizar el saldo pendiente de la cuenta
                cuenta.saldo_pendiente -= monto_pagado_decimal
                print(f"🔍 DEBUG: Saldo actualizado - Nuevo saldo: {cuenta.saldo_pendiente}")
                
                # Actualizar el estado de la cuenta según el saldo pendiente
                if cuenta.saldo_pendiente == 0:
                    cuenta.estado = 'pagada'
                    print("🔍 DEBUG: Cuenta marcada como PAGADA")
                else:
                    # Si no está pagada completamente, verificar si está vencida
                    if date.today() > cuenta.fecha_vencimiento:
                        cuenta.estado = 'vencida'
                        print("🔍 DEBUG: Cuenta marcada como VENCIDA")
                    else:
                        # Si tiene pagos parciales pero no está vencida
                        cuenta.estado = 'parcial' if cuenta.pagos.exists() else 'pendiente'
                        print(f"🔍 DEBUG: Cuenta marcada como {cuenta.estado}")
                
                cuenta.save()
                print(f"🔍 DEBUG: Cuenta guardada - Estado final: {cuenta.estado}, Saldo final: {cuenta.saldo_pendiente}")
            
            # Preparar respuesta con información del pago
            response_data = {
                'success': True,
                'message': 'Pago registrado exitosamente',
                'pago': {
                    'id': pago.id,
                    'numero_recibo': pago.numero_recibo,
                    'monto_pagado': float(pago.monto_pagado),
                    'fecha_pago': pago.fecha_pago.strftime('%Y-%m-%d'),
                    'metodo_pago': pago.metodo_pago,
                    'referencia': pago.observaciones or '',
                    'estado': pago.estado,
                    'fecha_creacion': pago.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if pago.fecha_creacion else None
                },
                'cuenta_actualizada': {
                    'id': cuenta.id,
                    'saldo_pendiente': float(cuenta.saldo_pendiente),
                    'estado': cuenta.estado
                }
            }
            
            print(f"✅ Pago registrado exitosamente: Recibo #{pago.numero_recibo}, ID del pago: {pago.id}")
            return JsonResponse(response_data)
            
        except json.JSONDecodeError as e:
            print(f"❌ Error decodificando JSON: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Error en el formato JSON',
                'details': str(e)
            }, status=400)
        except Exception as e:
            print(f"❌ Error en POST: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                'success': False,
                'error': f'Error interno del servidor: {str(e)}'
            }, status=500)
    
    else:
        return JsonResponse({
            'success': False,
            'error': f'Método {request.method} no permitido. Use GET o POST.'
        }, status=405)



@csrf_exempt
def api_eliminar_cuenta(request, cuenta_id):
    """Eliminar una cuenta por cobrar completamente pagada"""
    if request.method == 'DELETE':
        try:
            cuenta = get_object_or_404(CuentaPorCobrar, id=cuenta_id)
            
            # Verificar que la cuenta esté completamente pagada
            if cuenta.saldo_pendiente > 0:
                return JsonResponse({
                    'error': 'No se puede eliminar una cuenta con saldo pendiente'
                }, status=400)
            
            # Verificar que no tenga pagos asociados (o los eliminamos también)
            if cuenta.pagos.exists():
                cuenta.pagos.all().delete()
            
            # Eliminar la cuenta
            cuenta.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Cuenta eliminada exitosamente'
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)

def obtener_pagos_cuenta(request, cuenta_id):
    """Obtiene todos los pagos de una cuenta específica"""
    try:
        cuenta = get_object_or_404(CuentaPorCobrar, id=cuenta_id)
        pagos = cuenta.pagos.all().order_by('-fecha_pago')
        
        pagos_data = []
        for pago in pagos:
            pagos_data.append({
                'id': pago.id,
                'numero_recibo': pago.numero_recibo or 'N/A',
                'monto_pagado': float(pago.monto_pagado),
                'fecha_pago': pago.fecha_pago.strftime('%d/%m/%Y'),
                'metodo_pago': pago.get_metodo_pago_display(),
                'referencia': pago.observaciones or 'N/A',
                'estado': pago.estado
            })
        
        return JsonResponse({
            'cuenta_id': cuenta.id,
            'factura': f"FAC-{cuenta.venta.id:05d}" if cuenta.venta else f"CTA-{cuenta.id:05d}",
            'total_amount': float(cuenta.monto_total),
            'paid_amount': float(cuenta.monto_total - cuenta.saldo_pendiente),
            'pending_balance': float(cuenta.saldo_pendiente),
            'pagos': pagos_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def generar_comprobante_pago(request, pago_id):
    """Genera un PDF con el comprobante de pago - CORREGIDO para devolver PDF directamente"""
    try:
        pago = get_object_or_404(PagoCuentaCobrar, id=pago_id)
        cuenta = pago.cuenta
        
        # Determinar si es formato 80mm basado en la URL
        is_80mm = '80mm' in request.path
        
        # Crear el buffer para el PDF
        buffer = BytesIO()
        
        # Configurar el tamaño de página según el formato
        if is_80mm:
            # Formato 80mm (226.77 puntos de ancho)
            width = 226.77
            height = 550
            page_size = (width, height)
            doc = SimpleDocTemplate(buffer, pagesize=page_size, 
                                  topMargin=10, bottomMargin=10, 
                                  leftMargin=5, rightMargin=5)
        else:
            # Formato normal (A4)
            page_size = A4
            doc = SimpleDocTemplate(buffer, pagesize=page_size,
                                  topMargin=20, bottomMargin=20,
                                  leftMargin=20, rightMargin=20)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Crear estilos personalizados según el formato
        if is_80mm:
            styles.add(ParagraphStyle(
                name='Center80', 
                alignment=TA_CENTER, 
                fontSize=10, 
                spaceAfter=6, 
                fontName='Helvetica-Bold'
            ))
            styles.add(ParagraphStyle(
                name='Left80', 
                alignment=TA_LEFT, 
                fontSize=8, 
                spaceAfter=4
            ))
            styles.add(ParagraphStyle(
                name='Right80', 
                alignment=TA_RIGHT, 
                fontSize=8, 
                spaceAfter=4
            ))
            styles.add(ParagraphStyle(
                name='SmallCenter80', 
                alignment=TA_CENTER, 
                fontSize=8, 
                spaceAfter=4
            ))
            styles.add(ParagraphStyle(
                name='Bold80', 
                alignment=TA_LEFT, 
                fontSize=8, 
                spaceAfter=4,
                fontName='Helvetica-Bold'
            ))
            
            title = Paragraph("COMPROBANTE DE PAGO", styles['Center80'])
        else:
            styles.add(ParagraphStyle(
                name='Center', 
                alignment=TA_CENTER, 
                fontSize=16, 
                spaceAfter=12, 
                fontName='Helvetica-Bold'
            ))
            styles.add(ParagraphStyle(
                name='Left', 
                alignment=TA_LEFT, 
                fontSize=10, 
                spaceAfter=6
            ))
            styles.add(ParagraphStyle(
                name='Right', 
                alignment=TA_RIGHT, 
                fontSize=10, 
                spaceAfter=6
            ))
            styles.add(ParagraphStyle(
                name='Bold', 
                alignment=TA_LEFT, 
                fontSize=10, 
                spaceAfter=6,
                fontName='Helvetica-Bold'
            ))
            
            title = Paragraph("COMPROBANTE DE PAGO", styles['Center'])
        
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Información del cliente
        client_name = getattr(cuenta.cliente, 'nombre', 'Cliente no disponible')
        client_phone = getattr(cuenta.cliente, 'telefono1', 'No disponible')
        
        # Calcular saldos
        saldo_anterior = cuenta.saldo_pendiente + pago.monto_pagado
        saldo_actual = cuenta.saldo_pendiente
        
        # Información del pago
        data = [
            ['Número de Recibo:', pago.numero_recibo or 'N/A'],
            ['Fecha de Pago:', pago.fecha_pago.strftime('%d/%m/%Y')],
            ['Cliente:', client_name],
            ['Teléfono:', client_phone],
            ['Factura:', f"FAC-{cuenta.venta.id:05d}" if cuenta.venta else f"CTA-{cuenta.id:05d}"],
            ['Monto Total Factura:', f"RD$ {float(cuenta.monto_total):,.2f}"],
            ['Saldo Anterior:', f"RD$ {float(saldo_anterior):,.2f}"],
            ['Monto Pagado:', f"RD$ {float(pago.monto_pagado):,.2f}"],
            ['Nuevo Saldo:', f"RD$ {float(saldo_actual):,.2f}"],
            ['Método de Pago:', pago.get_metodo_pago_display()],
            ['Referencia:', pago.observaciones or 'N/A'],
        ]
        
        # Crear tabla según el formato
        if is_80mm:
            table = Table(data, colWidths=[80, 120])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Helvetica', 7),
                ('FONT', (0, 0), (0, 0), 'Helvetica-Bold', 7),
                ('FONT', (1, 0), (1, 0), 'Helvetica-Bold', 7),
                ('FONT', (0, 5), (0, 8), 'Helvetica-Bold', 7),
                ('FONT', (1, 5), (1, 8), 'Helvetica-Bold', 7),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
                ('LINEABOVE', (0, 5), (-1, 5), 1, colors.black),
                ('LINEBELOW', (0, 8), (-1, 8), 1, colors.black),
            ]))
        else:
            table = Table(data, colWidths=[120, 400])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
                ('FONT', (0, 0), (0, 0), 'Helvetica-Bold', 10),
                ('FONT', (1, 0), (1, 0), 'Helvetica-Bold', 10),
                ('FONT', (0, 5), (0, 8), 'Helvetica-Bold', 10),
                ('FONT', (1, 5), (1, 8), 'Helvetica-Bold', 10),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, 5), (-1, 8), colors.lightgrey),
            ]))
        
        elements.append(table)
        elements.append(Spacer(1, 15))
        
        # Estado de la cuenta
        estado_texto = "CUENTA PAGADA COMPLETAMENTE" if saldo_actual == 0 else f"SALDO PENDIENTE: RD$ {float(saldo_actual):,.2f}"
        
        if is_80mm:
            estado_style = styles['Center80'] if saldo_actual == 0 else styles['Bold80']
            elements.append(Paragraph(estado_texto, estado_style))
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("_________________________", styles['SmallCenter80']))
            elements.append(Paragraph("Firma del Cliente", styles['SmallCenter80']))
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("¡Gracias por su pago!", styles['SmallCenter80']))
        else:
            estado_style = styles['Center'] if saldo_actual == 0 else styles['Bold']
            elements.append(Paragraph(estado_texto, estado_style))
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("_________________________", styles['Center']))
            elements.append(Paragraph("Firma del Cliente", styles['Center']))
        
        # Construir el PDF
        doc.build(elements)
        
        buffer.seek(0)
        
        # CORREGIDO: Devolver el PDF directamente
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        filename = f"comprobante_pago_{pago.numero_recibo or pago.id}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response
        
    except Exception as e:
        import traceback
        print(f"Error al generar comprobante: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': f'Error al generar comprobante: {str(e)}'}, status=500)

def generar_comprobante_pago_normal(request, pago_id):
    """Genera un PDF con el comprobante de pago en formato normal"""
    try:
        pago = get_object_or_404(PagoCuentaCobrar, id=pago_id)
        cuenta = pago.cuenta
        
        # Crear el buffer para el PDF
        buffer = BytesIO()
        
        # Configurar el tamaño de página A4
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                              topMargin=20, bottomMargin=20,
                              leftMargin=20, rightMargin=20)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Crear estilos personalizados
        styles.add(ParagraphStyle(
            name='Center', 
            alignment=TA_CENTER, 
            fontSize=16, 
            spaceAfter=12, 
            fontName='Helvetica-Bold'
        ))
        styles.add(ParagraphStyle(
            name='Left', 
            alignment=TA_LEFT, 
            fontSize=10, 
            spaceAfter=6
        ))
        styles.add(ParagraphStyle(
            name='Right', 
            alignment=TA_RIGHT, 
            fontSize=10, 
            spaceAfter=6
        ))
        styles.add(ParagraphStyle(
            name='Bold', 
            alignment=TA_LEFT, 
            fontSize=10, 
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))
        
        # Título
        title = Paragraph("COMPROBANTE DE PAGO", styles['Center'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Información del cliente
        client_name = getattr(cuenta.cliente, 'nombre', 'Cliente no disponible')
        client_phone = getattr(cuenta.cliente, 'telefono1', 'No disponible')
        
        # Calcular saldos
        saldo_anterior = cuenta.saldo_pendiente + pago.monto_pagado
        saldo_actual = cuenta.saldo_pendiente
        
        # Información del pago
        data = [
            ['Número de Recibo:', pago.numero_recibo or 'N/A'],
            ['Fecha de Pago:', pago.fecha_pago.strftime('%d/%m/%Y')],
            ['Cliente:', client_name],
            ['Teléfono:', client_phone],
            ['Factura:', f"FAC-{cuenta.venta.id:05d}" if cuenta.venta else f"CTA-{cuenta.id:05d}"],
            ['Monto Total Factura:', f"RD$ {float(cuenta.monto_total):,.2f}"],
            ['Saldo Anterior:', f"RD$ {float(saldo_anterior):,.2f}"],
            ['Monto Pagado:', f"RD$ {float(pago.monto_pagado):,.2f}"],
            ['Nuevo Saldo:', f"RD$ {float(saldo_actual):,.2f}"],
            ['Método de Pago:', pago.get_metodo_pago_display()],
            ['Referencia:', pago.observaciones or 'N/A'],
        ]
        
        # Crear tabla
        table = Table(data, colWidths=[120, 400])
        table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('FONT', (0, 0), (0, 0), 'Helvetica-Bold', 10),
            ('FONT', (1, 0), (1, 0), 'Helvetica-Bold', 10),
            ('FONT', (0, 5), (0, 8), 'Helvetica-Bold', 10),
            ('FONT', (1, 5), (1, 8), 'Helvetica-Bold', 10),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('BACKGROUND', (0, 5), (-1, 8), colors.lightgrey),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        # Estado de la cuenta
        estado_texto = "CUENTA PAGADA COMPLETAMENTE" if saldo_actual == 0 else f"SALDO PENDIENTE: RD$ {float(saldo_actual):,.2f}"
        estado_style = styles['Center'] if saldo_actual == 0 else styles['Bold']
        elements.append(Paragraph(estado_texto, estado_style))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("_________________________", styles['Center']))
        elements.append(Paragraph("Firma del Cliente", styles['Center']))
        
        # Construir el PDF
        doc.build(elements)
        
        buffer.seek(0)
        
        # CORREGIDO: Devolver el PDF directamente
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        filename = f"comprobante_pago_{pago.numero_recibo or pago.id}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response
        
    except Exception as e:
        import traceback
        print(f"Error al generar comprobante normal: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': f'Error al generar comprobante: {str(e)}'}, status=500)

def obtener_ultimo_pago(request, cuenta_id):
    """Obtiene el ID del último pago de una cuenta"""
    try:
        cuenta = get_object_or_404(CuentaPorCobrar, id=cuenta_id)
        ultimo_pago = cuenta.pagos.order_by('-id').first()
        
        if ultimo_pago:
            return JsonResponse({'pago_id': ultimo_pago.id})
        else:
            return JsonResponse({'error': 'No se encontraron pagos para esta cuenta'}, status=404)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def api_obtener_detalles_cliente(request, cliente_id):
    """Obtiene todos los detalles de las cuentas por cobrar de un cliente"""
    try:
        cliente = get_object_or_404(Cliente, id=cliente_id)
        cuentas = CuentaPorCobrar.objects.filter(cliente=cliente).select_related('venta').prefetch_related('pagos')
        
        datos_cliente = {
            'id': cliente.id,
            'nombre': cliente.nombre,
            'telefono': cliente.telefono1,
            'cuentas': []
        }
        
        for cuenta in cuentas:
            # Obtener productos de la venta
            productos = []
            if cuenta.venta and hasattr(cuenta.venta, 'detalles'):
                for detalle in cuenta.venta.detalles.all():
                    productos.append({
                        'nombre': detalle.producto.producto.nombre if detalle.producto and detalle.producto.producto else 'Producto no disponible',
                        'cantidad': float(detalle.cantidad),
                        'precio': float(detalle.precio_unitario),
                        'subtotal': float(detalle.subtotal)
                    })
            
            # Obtener pagos
            pagos = []
            for pago in cuenta.pagos.all().order_by('-fecha_pago'):
                pagos.append({
                    'id': pago.id,
                    'numero_recibo': pago.numero_recibo or 'N/A',
                    'monto_pagado': float(pago.monto_pagado),
                    'fecha_pago': pago.fecha_pago.strftime('%d/%m/%Y'),
                    'metodo_pago': pago.get_metodo_pago_display(),
                    'referencia': pago.observaciones or 'N/A',
                    'estado': pago.estado
                })
            
            datos_cliente['cuentas'].append({
                'id': cuenta.id,
                'factura': f"FAC-{cuenta.venta.id:05d}" if cuenta.venta else f"CTA-{cuenta.id:05d}",
                'fecha_emision': cuenta.fecha_emision.strftime('%d/%m/%Y'),
                'fecha_vencimiento': cuenta.fecha_vencimiento.strftime('%d/%m/%Y'),
                'monto_total': float(cuenta.monto_total),
                'monto_pagado': float(cuenta.monto_total - cuenta.saldo_pendiente),
                'saldo_pendiente': float(cuenta.saldo_pendiente),
                'estado': cuenta.estado,
                'productos': productos,
                'pagos': pagos
            })
        
        return JsonResponse(datos_cliente)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)






def anulacionesdefactura(request):
    return render(request, "facturacion/anulacionesdefactura.html")

@csrf_exempt
@require_http_methods(["POST"])
def buscar_factura_ajax(request):
    """Vista AJAX para buscar una factura por número"""
    try:
        data = json.loads(request.body)
        numero_factura = data.get('numero_factura', '').strip()
        
        # Limpiar y formatear el número de factura
        numero_factura = numero_factura.upper().replace('FAC-', 'F-')
        
        try:
            # Buscar por número de factura exacto
            venta = Venta.objects.get(numero_factura=numero_factura)
        except Venta.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'No se encontró la factura {numero_factura}'
            })
        
        # Verificar si la venta tiene el campo estado y si está anulada
        if hasattr(venta, 'estado') and venta.estado == 'anulada':
            return JsonResponse({
                'success': False,
                'error': 'Esta factura ya ha sido anulada'
            })
        
        # Obtener detalles de la venta
        detalles = DetalleVenta.objects.filter(venta=venta)
        detalles_data = []
        for detalle in detalles:
            detalles_data.append({
                'producto': detalle.producto.producto if detalle.producto and hasattr(detalle.producto, 'producto') else 'Producto no disponible',
                'cantidad': float(detalle.cantidad),
                'precio_unitario': float(detalle.precio_unitario),
                'subtotal': float(detalle.subtotal)
            })
        
        # Verificar si tiene cuenta por cobrar
        cuenta_por_cobrar = None
        if venta.tipo_venta == 'credito':
            try:
                cuenta = CuentaPorCobrar.objects.get(venta=venta)
                # Verificar si la cuenta por cobrar ya está anulada
                if cuenta.estado == 'anulada':
                    return JsonResponse({
                        'success': False,
                        'error': 'La cuenta por cobrar asociada ya está anulada'
                    })
                    
                cuenta_por_cobrar = {
                    'id': cuenta.id,
                    'saldo_pendiente': float(cuenta.saldo_pendiente),
                    'estado': cuenta.estado
                }
            except CuentaPorCobrar.DoesNotExist:
                pass
        
        # Obtener el estado de la venta (si existe el campo)
        estado_venta = getattr(venta, 'estado', 'activa')
        
        response_data = {
            'success': True,
            'factura': {
                'id': venta.id,
                'numero': venta.numero_factura,  # Usar el número real de la base de datos
                'fecha': venta.fecha.strftime('%d/%m/%Y'),
                'cliente': venta.cliente.nombre if venta.cliente else (venta.cliente_nombre or 'Cliente no especificado'),
                'total': float(venta.total),
                'tipo': venta.get_tipo_venta_display(),
                'estado': estado_venta,
                'metodo_pago': venta.get_metodo_pago_display(),
            },
            'detalles': detalles_data,
            'cuenta_por_cobrar': cuenta_por_cobrar
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al buscar la factura: {str(e)}'
        })

@csrf_exempt
@require_http_methods(["POST"])
def anular_factura_ajax(request):
    """Vista AJAX para anular una factura"""
    try:
        data = json.loads(request.body)
        factura_id = data.get('factura_id')
        motivo = data.get('motivo')
        observaciones = data.get('observaciones', '')
        
        venta = Venta.objects.get(id=factura_id)
        
        # Verificar si la venta ya está anulada (si tiene el campo estado)
        if hasattr(venta, 'estado') and venta.estado == 'anulada':
            return JsonResponse({
                'success': False,
                'error': 'Esta factura ya ha sido anulada'
            })
        
        # Anular la venta (si tiene el campo estado)
        if hasattr(venta, 'estado'):
            venta.estado = 'anulada'
            venta.save()
        
        # Si es venta a crédito, anular la cuenta por cobrar
        if venta.tipo_venta == 'credito':
            try:
                cuenta = CuentaPorCobrar.objects.get(venta=venta)
                cuenta.estado = 'anulada'
                cuenta.saldo_pendiente = 0  # Importante: establecer saldo en 0
                cuenta.observaciones = f"Anulada por: {motivo}. {observaciones}"
                cuenta.save()
                
                # Mensaje adicional para indicar que la cuenta por cobrar fue anulada
                message = 'Factura y cuenta por cobrar anuladas exitosamente'
            except CuentaPorCobrar.DoesNotExist:
                message = 'Factura anulada exitosamente (no tenía cuenta por cobrar asociada)'
        else:
            message = 'Factura anulada exitosamente'
        
        return JsonResponse({
            'success': True,
            'message': message
        })
        
    except Venta.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Factura no encontrada'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al anular la factura: {str(e)}'
        })

@csrf_exempt
@require_http_methods(["POST"])
def buscar_ultima_factura(request):
    """Vista AJAX para buscar la última factura emitida"""
    try:
        data = json.loads(request.body)
        tipo_venta = data.get('tipo_venta', '')  # 'credito' o 'contado'
        
        # Buscar la última venta activa del tipo especificado
        # Si el campo estado existe, filtrar por estado activa
        if hasattr(Venta, 'estado'):
            filtros = {'estado': 'activa'}
        else:
            filtros = {}
            
        if tipo_venta:
            filtros['tipo_venta'] = tipo_venta
            
        ultima_venta = Venta.objects.filter(**filtros).order_by('-id').first()
        
        if not ultima_venta:
            tipo_desc = 'del tipo especificado' if tipo_venta else ''
            return JsonResponse({
                'success': False,
                'error': f'No se encontraron facturas activas {tipo_desc}'
            })
        
        # Obtener detalles de la venta
        detalles = DetalleVenta.objects.filter(venta=ultima_venta)
        detalles_data = []
        for detalle in detalles:
            detalles_data.append({
                'producto': detalle.producto.producto if detalle.producto and hasattr(detalle.producto, 'producto') else 'Producto no disponible',
                'cantidad': float(detalle.cantidad),
                'precio_unitario': float(detalle.precio_unitario),
                'subtotal': float(detalle.subtotal)
            })
        
        # Verificar si tiene cuenta por cobrar
        cuenta_por_cobrar = None
        if ultima_venta.tipo_venta == 'credito':
            try:
                cuenta = CuentaPorCobrar.objects.get(venta=ultima_venta)
                # Verificar si la cuenta por cobrar está anulada
                if cuenta.estado != 'anulada':
                    cuenta_por_cobrar = {
                        'id': cuenta.id,
                        'saldo_pendiente': float(cuenta.saldo_pendiente),
                        'estado': cuenta.estado
                    }
            except CuentaPorCobrar.DoesNotExist:
                pass
        
        # Obtener el estado de la venta (si existe el campo)
        estado_venta = getattr(ultima_venta, 'estado', 'activa')
        
        response_data = {
            'success': True,
            'factura': {
                'id': ultima_venta.id,
                'numero': ultima_venta.numero_factura,  # Usar el número real de la base de datos
                'fecha': ultima_venta.fecha.strftime('%d/%m/%Y'),
                'cliente': ultima_venta.cliente.nombre if ultima_venta.cliente else (ultima_venta.cliente_nombre or 'Cliente no especificado'),
                'total': float(ultima_venta.total),
                'tipo': ultima_venta.get_tipo_venta_display(),
                'estado': estado_venta,
                'metodo_pago': ultima_venta.get_metodo_pago_display(),
            },
            'detalles': detalles_data,
            'cuenta_por_cobrar': cuenta_por_cobrar
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al buscar la última factura: {str(e)}'
        })

@csrf_exempt
@require_http_methods(["POST"])
def buscar_recibo_ajax(request):
    """Vista AJAX para buscar un recibo de pago"""
    try:
        data = json.loads(request.body)
        numero_recibo = data.get('numero_recibo', '').strip()
        
        if not numero_recibo:
            return JsonResponse({
                'success': False,
                'error': 'Por favor, ingrese un número de recibo'
            })
        
        # Buscar el recibo
        try:
            recibo = PagoCuentaCobrar.objects.select_related('cuenta', 'cuenta__cliente').get(
                numero_recibo=numero_recibo,
                estado='activo'
            )
        except PagoCuentaCobrar.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Recibo no encontrado. Verifique el número o el recibo ya ha sido anulado.'
            })
        
        cuenta = recibo.cuenta
        
        return JsonResponse({
            'success': True,
            'recibo': {
                'id': recibo.id,
                'numero': recibo.numero_recibo,
                'monto_pagado': float(recibo.monto_pagado),
                'fecha_pago': recibo.fecha_pago.strftime('%d/%m/%Y'),
                'metodo_pago': recibo.get_metodo_pago_display(),
                'observaciones': recibo.observaciones,
                'estado': recibo.estado,
            },
            'cuenta': {
                'id': cuenta.id,
                'cliente': cuenta.cliente.nombre,
                'saldo_actual': float(cuenta.saldo_pendiente),
                'saldo_original': float(cuenta.monto_total),
                'estado': cuenta.estado,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al buscar el recibo: {str(e)}'
        })

@csrf_exempt
@require_http_methods(["POST"])
def anular_recibo_ajax(request):
    """Vista AJAX para anular un recibo de pago"""
    try:
        data = json.loads(request.body)
        recibo_id = data.get('recibo_id')
        motivo = data.get('motivo')
        observaciones = data.get('observaciones', '')
        
        if not recibo_id:
            return JsonResponse({
                'success': False,
                'error': 'ID de recibo no proporcionado'
            })
        
        if not motivo:
            return JsonResponse({
                'success': False,
                'error': 'Debe seleccionar un motivo de anulación'
            })
        
        # Buscar y anular el recibo
        try:
            recibo = PagoCuentaCobrar.objects.get(id=recibo_id, estado='activo')
        except PagoCuentaCobrar.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Recibo no encontrado o ya ha sido anulado'
            })
        
        if recibo.anular():
            # Registrar la anulación
            observaciones_anulacion = f"ANULADO - Motivo: {motivo}"
            if observaciones:
                observaciones_anulacion += f". {observaciones}"
            
            recibo.observaciones = observaciones_anulacion
            recibo.save()
            
            nuevo_saldo = recibo.cuenta.saldo_pendiente
            
            return JsonResponse({
                'success': True,
                'message': f'Recibo {recibo.numero_recibo} anulado exitosamente. La deuda ha sido restaurada a RD$ {nuevo_saldo:,.2f}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No se pudo anular el recibo. Puede que ya esté anulado.'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al anular el recibo: {str(e)}'
        })



def devoluciones(request):
    return render(request, "facturacion/devoluciones.html")

@csrf_exempt
@require_http_methods(["POST"])
def buscar_factura_devolucion(request):
    try:
        data = json.loads(request.body)
        invoice_number = data.get('invoiceNumber', '').strip()
        print(f"🔍 Buscando factura: {invoice_number}")
        
        # Buscar la venta por diferentes formatos
        venta = None
        
        try:
            # Intentar buscar por número de factura exacto (nuevo formato F-000001)
            if invoice_number.startswith('F-'):
                venta = Venta.objects.get(numero_factura=invoice_number)
                print(f"✅ Venta encontrada por número_factura: {venta.id}")
            
            # Intentar buscar por formato antiguo FAC-2024-001
            elif invoice_number.startswith('FAC-'):
                parts = invoice_number.split('-')
                if len(parts) >= 3:
                    venta_id = int(parts[2])
                    venta = Venta.objects.get(id=venta_id)
                    print(f"✅ Venta encontrada por ID (formato FAC): {venta.id}")
            
            # Intentar buscar por ID directo
            else:
                try:
                    venta_id = int(invoice_number)
                    venta = Venta.objects.get(id=venta_id)
                    print(f"✅ Venta encontrada por ID directo: {venta.id}")
                except ValueError:
                    # Si no es número, buscar por número de factura
                    venta = Venta.objects.get(numero_factura=invoice_number)
                    print(f"✅ Venta encontrada por número_factura: {venta.id}")
                    
        except Venta.DoesNotExist:
            print(f"❌ No se encontró venta con: {invoice_number}")
            return JsonResponse({
                'success': False,
                'error': 'No se encontró ninguna factura con ese número'
            })
        
        # VERIFICAR SI LA FACTURA ESTÁ ANULADA
        if venta.estado == 'anulada':
            return JsonResponse({
                'success': False,
                'error': '❌ Esta factura ha sido ANULADA y no se pueden procesar devoluciones sobre facturas anuladas.'
            })
        
        # Verificar que la venta tenga detalles
        if not venta.detalles.exists():
            return JsonResponse({
                'success': False,
                'error': 'La factura no tiene productos asociados'
            })
        
        # Construir respuesta con datos reales - USANDO FLOAT PARA JSON
        items = []
        for detalle in venta.detalles.all():
            items.append({
                'code': detalle.producto.codigo,
                'description': detalle.producto.producto,
                'quantity': float(detalle.cantidad),
                'unitPrice': float(detalle.precio_unitario),
                'total': float(detalle.subtotal),
                'max_quantity': float(detalle.cantidad)  # Cantidad máxima que se puede devolver
            })
        
        # Determinar estado para la interfaz
        if venta.estado == 'anulada':
            status = 'overdue'
            status_text = 'Anulada'
        elif venta.tipo_venta == 'contado':
            status = 'paid'
            status_text = 'Pagada'
        else:
            status = 'pending'
            status_text = 'Pendiente'
        
        # Usar el número de factura real del modelo
        invoice_data = {
            'id': venta.id,
            'number': venta.numero_factura,
            'client': {
                'name': venta.cliente.nombre if venta.cliente else (venta.cliente_nombre or 'Cliente General'),
                'email': venta.cliente.correo_electronico if venta.cliente and hasattr(venta.cliente, 'correo_electronico') else '',
                'phone': venta.cliente.telefono if venta.cliente and hasattr(venta.cliente, 'telefono') else ''
            },
            'date': venta.fecha.strftime('%d/%m/%Y'),
            'dueDate': venta.fecha.strftime('%d/%m/%Y'),
            'paymentMethod': venta.get_metodo_pago_display(),
            'status': status,
            'status_text': status_text,
            'subtotal': float(venta.subtotal),
            'tax': 0,
            'total': float(venta.total),
            'items': items
        }
        
        return JsonResponse({
            'success': True,
            'invoice': invoice_data
        })
            
    except Exception as e:
        print(f"❌ Error general en buscar_factura_devolucion: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error al buscar la factura: {str(e)}'
        })





@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def procesar_devolucion(request):
    try:
        data = json.loads(request.body)
        print(f"🔄 Procesando devolución: {data}")
        
        # Validar datos requeridos
        required_fields = ['invoiceNumber', 'items', 'reason', 'totalAmount']
        for field in required_fields:
            if field not in data:
                return JsonResponse({
                    'success': False,
                    'error': f'Campo requerido faltante: {field}'
                })
        
        # Buscar la venta por diferentes formatos
        venta = None
        invoice_number = data['invoiceNumber']
        
        try:
            # Intentar buscar por número de factura exacto (nuevo formato F-000001)
            if invoice_number.startswith('F-'):
                venta = Venta.objects.get(numero_factura=invoice_number)
                print(f"✅ Venta encontrada por número_factura: {venta.id}")
            
            # Intentar buscar por formato antiguo FAC-2024-001
            elif invoice_number.startswith('FAC-'):
                parts = invoice_number.split('-')
                if len(parts) >= 3:
                    venta_id = int(parts[2])
                    venta = Venta.objects.get(id=venta_id)
                    print(f"✅ Venta encontrada por ID (formato FAC): {venta.id}")
            
            # Intentar buscar por ID directo
            else:
                try:
                    venta_id = int(invoice_number)
                    venta = Venta.objects.get(id=venta_id)
                    print(f"✅ Venta encontrada por ID directo: {venta.id}")
                except ValueError:
                    # Si no es número, buscar por número de factura
                    venta = Venta.objects.get(numero_factura=invoice_number)
                    print(f"✅ Venta encontrada por número_factura: {venta.id}")
                    
        except Venta.DoesNotExist:
            print(f"❌ Error al buscar venta: {invoice_number}")
            return JsonResponse({
                'success': False,
                'error': 'La factura no existe'
            })
        
        # Verificar que la venta no esté anulada (doble verificación)
        if venta.estado == 'anulada':
            return JsonResponse({
                'success': False,
                'error': 'No se puede procesar devolución para una factura anulada'
            })
        
        # Crear la devolución
        devolucion = Devolucion(
            venta=venta,
            motivo=data['reason'],
            comentarios=data.get('comments', ''),
            total_devolucion=data['totalAmount'],
            estado='procesada'
        )
        devolucion.save()
        print(f"✅ Devolución creada: {devolucion.numero_devolucion}")
        
        # Procesar los items de devolución
        items_procesados = 0
        productos_actualizados = []
        
        for item_data in data['items']:
            try:
                print(f"📦 Procesando item: {item_data}")
                
                # Buscar el producto en el inventario por código
                producto = EntradaProducto.objects.get(codigo=item_data['code'])
                print(f"✅ Producto encontrado: {producto.codigo} - {producto.producto}")
                print(f"📊 Cantidad actual en inventario: {producto.cantidad}")
                
                # Buscar el detalle de venta original
                detalle_venta = DetalleVenta.objects.get(
                    venta=venta,
                    producto=producto
                )
                print(f"✅ Detalle de venta encontrado: {detalle_venta.id}")
                
                # Verificar que la cantidad a devolver no exceda la cantidad vendida
                cantidad_float = min(float(item_data['quantity']), float(detalle_venta.cantidad))
                
                # CONVERTIR A DECIMAL
                from decimal import Decimal
                cantidad_devuelta = Decimal(str(cantidad_float))
                
                print(f"📦 Cantidad a devolver: {cantidad_devuelta} (tipo: {type(cantidad_devuelta)})")
                
                if cantidad_devuelta > 0:
                    # Crear item de devolución
                    item_devolucion = ItemDevolucion(
                        devolucion=devolucion,
                        detalle_venta=detalle_venta,
                        producto=producto,
                        cantidad=cantidad_devuelta,
                        precio_unitario=Decimal(str(item_data['unitPrice']))
                    )
                    item_devolucion.save()
                    print(f"✅ Item de devolución guardado: {item_devolucion.id}")
                    
                    # REPONER EN INVENTARIO
                    producto.cantidad += cantidad_devuelta
                    producto.save()
                    
                    productos_actualizados.append({
                        'producto': producto.codigo,
                        'cantidad_agregada': float(cantidad_devuelta),
                        'nueva_cantidad': float(producto.cantidad)
                    })
                    print(f"📊 Nueva cantidad en inventario: {producto.cantidad}")
                    
                    items_procesados += 1
                else:
                    print("⚠️ Cantidad a devolver es 0, saltando item")
                
            except EntradaProducto.DoesNotExist:
                print(f"❌ Producto no encontrado con código: {item_data['code']}")
                continue
            except DetalleVenta.DoesNotExist:
                print(f"❌ Detalle de venta no encontrado para producto: {item_data['code']}")
                continue
            except Exception as e:
                print(f"❌ Error al procesar item {item_data['code']}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"📊 Items procesados: {items_procesados}")
        print(f"📊 Productos actualizados: {productos_actualizados}")
        
        if items_procesados == 0:
            # Si no se procesó ningún item, eliminar la devolución
            devolucion.delete()
            return JsonResponse({
                'success': False,
                'error': 'No se pudo procesar ningún item. Verifique que los productos existan en el inventario.'
            })
        
        return JsonResponse({
            'success': True,
            'devolucion_numero': devolucion.numero_devolucion,
            'message': f'Devolución procesada correctamente. Número: {devolucion.numero_devolucion}. Se repusieron {items_procesados} productos en el inventario.',
            'productos_actualizados': productos_actualizados
        })
        
    except Exception as e:
        print(f"❌ Error general en procesar_devolucion: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'error': f'Error al procesar la devolución: {str(e)}'
        })



def estadodecuenta(request):    
    clientes = Cliente.objects.all().values('id', 'cedula', 'nombre', 'telefono1', 'direccion')
    
    context = {
        'clientes': list(clientes),
        'search_url': reverse('buscar_clientes_estado_cuenta'),
        'data_url_pattern': '/cliente/{id}/datos-estado-cuenta/',
        'pdf_url_pattern': '/cliente/{id}/pdf-estado-cuenta/'
    }
    return render(request, "facturacion/estadodecuenta.html", context)

def buscar_clientes_estado_cuenta(request):
    """Vista para búsqueda de clientes via AJAX específica para estado de cuenta"""
    if request.method == 'GET' and 'q' in request.GET:
        query = request.GET.get('q', '').strip()
        
        if query:
            # Buscar por nombre o cédula
            clientes = Cliente.objects.filter(
                Q(nombre__icontains=query) | Q(cedula__icontains=query)
            ).values('id', 'cedula', 'nombre', 'telefono1', 'direccion')[:10]
            
            return JsonResponse(list(clientes), safe=False)
    
    return JsonResponse([], safe=False)

def obtener_datos_estado_cuenta(request, cliente_id):
    """Obtiene los datos del cliente y sus cuentas por cobrar para estado de cuenta"""
    try:
        print(f"Buscando cliente con ID: {cliente_id}")
        cliente = get_object_or_404(Cliente, id=cliente_id)
        print(f"Cliente encontrado: {cliente.nombre}")
        
        # Obtener cuentas por cobrar - SOLUCIÓN: Manejar el caso donde estado pueda ser None
        cuentas = CuentaPorCobrar.objects.filter(cliente=cliente)
        
        # Excluir cuentas anuladas de manera segura
        cuentas = cuentas.exclude(estado='anulada') if cuentas.exists() else cuentas
        
        print(f"Cuentas encontradas: {cuentas.count()}")
        
        # Si no hay cuentas, retornar datos vacíos
        if not cuentas.exists():
            data = {
                'cliente': {
                    'id': cliente.id,
                    'cedula': cliente.cedula,
                    'nombre': cliente.nombre,
                    'telefono': cliente.telefono1 or '-',
                    'direccion': cliente.direccion or '-',
                    'limite_credito': float(cliente.limite_credito) if cliente.limite_credito else 0.0
                },
                'resumen': {
                    'total_facturas': 0,
                    'monto_total': 0.0,
                    'saldo_pendiente': 0.0,
                    'monto_pagado': 0.0
                },
                'cuentas': []
            }
            return JsonResponse(data)
        
        # Calcular totales
        total_facturas = cuentas.count()
        monto_total = cuentas.aggregate(total=Sum('monto_total'))['total'] or Decimal('0.00')
        saldo_pendiente = cuentas.aggregate(total=Sum('saldo_pendiente'))['total'] or Decimal('0.00')
        monto_pagado = monto_total - saldo_pendiente
        
        print(f"Resumen - Total: {monto_total}, Pendiente: {saldo_pendiente}, Pagado: {monto_pagado}")
        
        # Preparar datos de las cuentas
        cuentas_data = []
        for cuenta in cuentas:
            numero_factura = f"CTE-{cuenta.id}"
            # Verificar si existe la relación venta de manera segura
            try:
                if hasattr(cuenta, 'venta') and cuenta.venta and hasattr(cuenta.venta, 'numero_factura'):
                    numero_factura = cuenta.venta.numero_factura
            except Exception as e:
                print(f"Error obteniendo número de factura para cuenta {cuenta.id}: {e}")
            
            dias_vencimiento = 0
            if cuenta.fecha_vencimiento and cuenta.fecha_vencimiento < date.today():
                dias_vencimiento = (date.today() - cuenta.fecha_vencimiento).days
                
            cuentas_data.append({
                'id': cuenta.id,
                'numero_factura': numero_factura,
                'fecha_emision': cuenta.fecha_emision.isoformat() if cuenta.fecha_emision else None,
                'fecha_vencimiento': cuenta.fecha_vencimiento.isoformat() if cuenta.fecha_vencimiento else None,
                'monto_total': float(cuenta.monto_total) if cuenta.monto_total else 0.0,
                'saldo_pendiente': float(cuenta.saldo_pendiente) if cuenta.saldo_pendiente else 0.0,
                'estado': cuenta.estado or 'pendiente',  # Asegurar que estado no sea None
                'estado_display': cuenta.get_estado_display() if cuenta.estado else 'Pendiente',
                'dias_vencimiento': dias_vencimiento
            })
        
        data = {
            'cliente': {
                'id': cliente.id,
                'cedula': cliente.cedula,
                'nombre': cliente.nombre,
                'telefono': cliente.telefono1 or '-',
                'direccion': cliente.direccion or '-',
                'limite_credito': float(cliente.limite_credito) if cliente.limite_credito else 0.0
            },
            'resumen': {
                'total_facturas': total_facturas,
                'monto_total': float(monto_total),
                'saldo_pendiente': float(saldo_pendiente),
                'monto_pagado': float(monto_pagado)
            },
            'cuentas': cuentas_data
        }
        
        print(f"Datos preparados exitosamente")
        return JsonResponse(data)
        
    except Exception as e:
        print(f"Error completo: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)

def generar_pdf_estado_cuenta(request, cliente_id):
    """Genera un PDF con el estado de cuenta del cliente optimizado para A4"""
    try:
        cliente = get_object_or_404(Cliente, id=cliente_id)
        
        # Obtener todas las cuentas por cobrar del cliente
        cuentas = CuentaPorCobrar.objects.filter(cliente=cliente)
        
        # Excluir cuentas anuladas
        cuentas = cuentas.exclude(estado='anulada')
        
        # Preparar datos de las cuentas para el PDF
        cuentas_data = []
        for cuenta in cuentas:
            numero_factura = f"CTE-{cuenta.id}"
            try:
                if hasattr(cuenta, 'venta') and cuenta.venta and hasattr(cuenta.venta, 'numero_factura'):
                    numero_factura = cuenta.venta.numero_factura
            except Exception:
                pass
            
            dias_vencimiento = 0
            if cuenta.fecha_vencimiento and cuenta.fecha_vencimiento < date.today():
                dias_vencimiento = (date.today() - cuenta.fecha_vencimiento).days
                
            cuentas_data.append({
                'numero_factura': numero_factura,
                'fecha_emision': cuenta.fecha_emision,
                'fecha_vencimiento': cuenta.fecha_vencimiento,
                'monto_total': cuenta.monto_total or Decimal('0.00'),
                'saldo_pendiente': cuenta.saldo_pendiente or Decimal('0.00'),
                'estado': cuenta.estado or 'pendiente',
                'estado_display': cuenta.get_estado_display() if cuenta.estado else 'Pendiente',
                'dias_vencimiento': dias_vencimiento
            })
        
        # Calcular totales
        total_facturas = cuentas.count()
        monto_total = cuentas.aggregate(total=Sum('monto_total'))['total'] or Decimal('0.00')
        saldo_pendiente = cuentas.aggregate(total=Sum('saldo_pendiente'))['total'] or Decimal('0.00')
        monto_pagado = monto_total - saldo_pendiente
        
        # Contexto para el template
        context = {
            'cliente': cliente,
            'cuentas': cuentas_data,
            'total_facturas': total_facturas,
            'monto_total': monto_total,
            'saldo_pendiente': saldo_pendiente,
            'monto_pagado': monto_pagado,
            'fecha_actual': datetime.now(),
        }
        
        # Crear el PDF
        template_path = 'facturacion/estado_cuenta_pdf.html'
        template = get_template(template_path)
        html = template.render(context)
        
        response = HttpResponse(content_type='application/pdf')
        filename = f"estado_cuenta_{cliente.cedula}_{date.today().strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Configuración para PDF A4
        pdf_options = {
            'page-size': 'A4',
            'margin-top': '1.5cm',
            'margin-right': '1.5cm',
            'margin-bottom': '1.5cm',
            'margin-left': '1.5cm',
            'encoding': "UTF-8",
            'no-outline': None
        }
        
        # Generar PDF
        pisa_status = pisa.CreatePDF(
            html, 
            dest=response,
            **pdf_options
        )
        
        if pisa_status.err:
            return HttpResponse('Error al generar el PDF', status=500)
        
        return response
        
    except Exception as e:
        import traceback
        print(f"Error generando PDF: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return HttpResponse(f'Error al generar el PDF: {str(e)}', status=500)
    



def generar_pdf_estado_cuenta(request, cliente_id):
    """Genera un PDF con el estado de cuenta del cliente"""
    try:
        cliente = get_object_or_404(Cliente, id=cliente_id)
        
        # Obtener todas las cuentas por cobrar del cliente
        cuentas = CuentaPorCobrar.objects.filter(cliente=cliente)
        
        # Excluir cuentas anuladas de manera segura
        cuentas = cuentas.exclude(estado='anulada') if cuentas.exists() else cuentas
        
        # Preparar datos de las cuentas para el PDF
        cuentas_data = []
        for cuenta in cuentas:
            numero_factura = f"CTE-{cuenta.id}"
            try:
                if hasattr(cuenta, 'venta') and cuenta.venta and hasattr(cuenta.venta, 'numero_factura'):
                    numero_factura = cuenta.venta.numero_factura
            except Exception as e:
                print(f"Error obteniendo número de factura para cuenta {cuenta.id}: {e}")
            
            dias_vencimiento = 0
            if cuenta.fecha_vencimiento and cuenta.fecha_vencimiento < date.today():
                dias_vencimiento = (date.today() - cuenta.fecha_vencimiento).days
                
            cuentas_data.append({
                'numero_factura': numero_factura,
                'fecha_emision': cuenta.fecha_emision,
                'fecha_vencimiento': cuenta.fecha_vencimiento,
                'monto_total': cuenta.monto_total or Decimal('0.00'),
                'saldo_pendiente': cuenta.saldo_pendiente or Decimal('0.00'),
                'estado': cuenta.estado or 'pendiente',
                'estado_display': cuenta.get_estado_display() if cuenta.estado else 'Pendiente',
                'dias_vencimiento': dias_vencimiento
            })
        
        # Calcular totales
        total_facturas = cuentas.count()
        monto_total = cuentas.aggregate(total=Sum('monto_total'))['total'] or Decimal('0.00')
        saldo_pendiente = cuentas.aggregate(total=Sum('saldo_pendiente'))['total'] or Decimal('0.00')
        monto_pagado = monto_total - saldo_pendiente
        
        # Contexto para el template
        context = {
            'cliente': cliente,
            'cuentas': cuentas_data,  # Usar los datos preparados
            'total_facturas': total_facturas,
            'monto_total': monto_total,
            'saldo_pendiente': saldo_pendiente,
            'monto_pagado': monto_pagado,
            'fecha_actual': datetime.now(),  # Usar datetime para incluir hora
        }
        
        # Crear el PDF
        template_path = 'facturacion/estado_cuenta_pdf.html'
        template = get_template(template_path)
        html = template.render(context)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="estado_cuenta_{cliente.cedula}_{date.today()}.pdf"'
        
        # Generar PDF
        pisa_status = pisa.CreatePDF(html, dest=response)
        
        if pisa_status.err:
            return HttpResponse('Error al generar el PDF', status=500)
        
        return response
    except Exception as e:
        import traceback
        print(f"Error generando PDF: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return HttpResponse(f'Error: {str(e)}', status=500)






def dashboard(request):
    # Obtener la fecha actual y rangos de fechas
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    
    # Ventas del día actual usando pandas
    ventas_hoy = Venta.objects.filter(fecha__date=hoy)
    df_ventas_hoy = pd.DataFrame(list(ventas_hoy.values('total')))
    ventas_hoy_total = df_ventas_hoy['total'].sum() if not df_ventas_hoy.empty else 0
    
    # Ventas del mes actual
    ventas_mes = Venta.objects.filter(fecha__date__gte=inicio_mes)
    df_ventas_mes = pd.DataFrame(list(ventas_mes.values('total')))
    ventas_mes_total = df_ventas_mes['total'].sum() if not df_ventas_mes.empty else 0
    
    # Total de créditos pendientes
    creditos_pendientes = CuentaPorCobrar.objects.filter(estado__in=['pendiente', 'parcial'])
    df_creditos = pd.DataFrame(list(creditos_pendientes.values('saldo_pendiente')))
    total_creditos = df_creditos['saldo_pendiente'].sum() if not df_creditos.empty else 0
    
    # Calcular ganancia (simplificado - diferencia entre precio venta y costo)
    detalles_mes = DetalleVenta.objects.filter(venta__fecha__date__gte=inicio_mes)
    
    if detalles_mes.exists():
        df_detalles = pd.DataFrame(list(
            detalles_mes.annotate(
                costo=F('producto__precio_unitario'),
                ganancia_unitaria=F('precio_unitario') - F('producto__precio_unitario')
            ).values('cantidad', 'ganancia_unitaria')
        ))
        df_detalles['ganancia_total'] = df_detalles['cantidad'] * df_detalles['ganancia_unitaria']
        ganancia_total = df_detalles['ganancia_total'].sum()
    else:
        ganancia_total = 0
    
    # Valor del inventario
    inventario = EntradaProducto.objects.all()
    df_inventario = pd.DataFrame(list(inventario.values('cantidad', 'precio_unitario')))
    if not df_inventario.empty:
        df_inventario['valor_total'] = df_inventario['cantidad'] * df_inventario['precio_unitario']
        valor_inventario = df_inventario['valor_total'].sum()
    else:
        valor_inventario = 0
    
    # Datos para gráfico semanal
    fecha_7_dias = hoy - timedelta(days=6)
    ventas_semanales = Venta.objects.filter(fecha__date__gte=fecha_7_dias)
    
    # Crear DataFrame con ventas de la semana
    df_semana = pd.DataFrame(list(
        ventas_semanales.extra({'fecha_simple': "date(fecha)"}).values('fecha_simple', 'total')
    ))
    
    if not df_semana.empty:
        # Agrupar por día y sumar ventas
        ventas_por_dia = df_semana.groupby('fecha_simple')['total'].sum()
        
        # Crear rango completo de días de la semana
        dias_semana = [hoy - timedelta(days=i) for i in range(6, -1, -1)]
        ventas_semana_completa = []
        
        for dia in dias_semana:
            venta_dia = ventas_por_dia.get(dia, 0)
            ventas_semana_completa.append(float(venta_dia))
        
        labels_semana = [dia.strftime('%a') for dia in dias_semana]
    else:
        ventas_semana_completa = [0] * 7
        labels_semana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    
    # Datos para gráfico mensual (últimos 6 meses)
    meses_data = []
    labels_meses = []
    
    for i in range(5, -1, -1):
        mes_fecha = hoy.replace(day=1) - timedelta(days=30*i)
        inicio_mes_calc = mes_fecha.replace(day=1)
        
        if i == 0:
            fin_mes_calc = hoy
        else:
            siguiente_mes = inicio_mes_calc + timedelta(days=32)
            fin_mes_calc = siguiente_mes.replace(day=1) - timedelta(days=1)
        
        ventas_mes_calc = Venta.objects.filter(
            fecha__date__gte=inicio_mes_calc, 
            fecha__date__lte=fin_mes_calc
        )
        
        df_mes_calc = pd.DataFrame(list(ventas_mes_calc.values('total')))
        total_mes = df_mes_calc['total'].sum() if not df_mes_calc.empty else 0
        
        meses_data.append(float(total_mes))
        labels_meses.append(inicio_mes_calc.strftime('%b'))
    
    # Productos más vendidos (últimos 30 días)
    fecha_30_dias = hoy - timedelta(days=30)
    top_productos = DetalleVenta.objects.filter(
        venta__fecha__date__gte=fecha_30_dias
    ).values(
        'producto__producto'
    ).annotate(
        total_vendido=Sum('cantidad')
    ).order_by('-total_vendido')[:5]
    
    productos_data = []
    for producto in top_productos:
        productos_data.append({
            'name': producto['producto__producto'],
            'sales': int(producto['total_vendido'])
        })
    
    # Si no hay productos, usar datos de ejemplo
    if not productos_data:
        productos_data = [
            {'name': 'Fertilizante NPK 15-15-15', 'sales': 45},
            {'name': 'Urea 46%', 'sales': 38},
            {'name': 'Sulfato de Amonio', 'sales': 32},
            {'name': 'Herbicida Glifosato', 'sales': 28},
            {'name': 'Insecticida Cipermetrina', 'sales': 25}
        ]
    
    # Últimas ventas (hoy)
    ultimas_ventas = DetalleVenta.objects.filter(
        venta__fecha__date=hoy
    ).select_related('venta', 'producto')[:5]
    
    # Preparar datos para el template
    dashboard_data = {
        'sales': {
            'daily': float(ventas_hoy_total),
            'monthly': float(ventas_mes_total),
            'credits': float(total_creditos),
            'profit': float(ganancia_total),
            'weekly': ventas_semana_completa,
            'weekLabels': labels_semana,
            'monthlyTrend': meses_data,
            'monthLabels': labels_meses,
            'inventory': float(valor_inventario)
        },
        'topProducts': productos_data
    }
    
    # Formatear los valores numéricos con comas
    ventas_hoy_formatted = intcomma(int(ventas_hoy_total))
    ventas_mes_formatted = intcomma(int(ventas_mes_total))
    total_creditos_formatted = intcomma(int(total_creditos))
    ganancia_total_formatted = intcomma(int(ganancia_total))
    valor_inventario_formatted = intcomma(int(valor_inventario))
    
    context = {
        'dashboard_data': dashboard_data,
        'ultimas_ventas': ultimas_ventas,
        'ventas_hoy_formatted': ventas_hoy_formatted,
        'ventas_mes_formatted': ventas_mes_formatted,
        'total_creditos_formatted': total_creditos_formatted,
        'ganancia_total_formatted': ganancia_total_formatted,
        'valor_inventario_formatted': valor_inventario_formatted,
    }
    
    return render(request, "facturacion/dashboard.html", context)