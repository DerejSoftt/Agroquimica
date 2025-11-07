from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET, require_POST, require_http_methods
import json
from .models import Cliente, Suplidor, EntradaProducto , Compra, DetalleCompra,Venta, DetalleVenta, CuentaPorCobrar, PagoCuentaCobrar
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
#==============================================================
#           Login 
#==============================================================
def index(request):
    return render(request, "facturacion/index.html")


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
                    tipo_venta=data['tipo_venta'],
                    metodo_pago=data['metodo_pago'],
                    subtotal=float(data['subtotal']),
                    descuento=float(data['descuento']),
                    total=float(data['total']),
                    observacion=data.get('observacion', '')
                )
                venta.save()
                
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
                        # Calcular fecha de vencimiento (30 días por defecto)
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
                        # Si no existe el cliente, continuamos sin crear la cuenta por cobrar
                        pass
                
                return JsonResponse({
                    'success': True,
                    'venta_id': venta.id,
                    'redirect_url': f'/facturas/{venta.id}/'
                })
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Error en el formato JSON de la solicitud'
            })
        except KeyError as e:
            return JsonResponse({
                'success': False,
                'error': f'Falta campo requerido: {str(e)}'
            })
        except Exception as e:
            print("Error completo:", str(e))  # Para debug
            return JsonResponse({
                'success': False,
                'error': f'Error al procesar la venta: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


def factura_detalle(request, venta_id):
    venta = Venta.objects.get(id=venta_id)
    detalles = venta.detalles.all()
    
    context = {
        'venta': venta,
        'detalles': detalles,
    }
    return render(request, "facturacion/factura_detalle.html", context)
#==============================================================

def cuentaporcobrar(request):
    return render(request, "facturacion/cuentaporcobrar.html")  



@csrf_exempt
def api_cuentas_por_cobrar(request):
    if request.method == 'GET':
        try:
            cuentas = CuentaPorCobrar.objects.select_related('cliente', 'venta').prefetch_related('pagos').all()
            
            # Actualizar estado de vencimiento
            for cuenta in cuentas:
                cuenta.verificar_vencimiento()
            
            data = []
            for cuenta in cuentas:
                # Obtener productos de la venta
                productos = []
                try:
                    if cuenta.venta and hasattr(cuenta.venta, 'detalles'):
                        detalles_venta = cuenta.venta.detalles.all()
                        for detalle in detalles_venta:
                            productos.append({
                                'nombre': getattr(detalle.producto, 'nombre', 'Producto no disponible') if detalle.producto else 'Producto no disponible',
                                'cantidad': detalle.cantidad,
                                'precio': float(detalle.precio_unitario)
                            })
                    else:
                        productos = [{'nombre': 'Información de productos no disponible', 'cantidad': 1, 'precio': float(cuenta.monto_total)}]
                except Exception as e:
                    productos = [{'nombre': 'Error al cargar productos', 'cantidad': 1, 'precio': float(cuenta.monto_total)}]
                
                # Obtener información del cliente
                client_name = getattr(cuenta.cliente, 'nombre', 'Cliente no disponible')
                client_phone = getattr(cuenta.cliente, 'telefono1', 'No disponible')
                
                # Obtener pagos de esta cuenta
                pagos = []
                for pago in cuenta.pagos.all():
                    pagos.append({
                        'id': pago.id,
                        'monto_pagado': float(pago.monto_pagado),
                        'fecha_pago': pago.fecha_pago.strftime('%Y-%m-%d'),
                        'metodo_pago': pago.metodo_pago,
                        'referencia': pago.observaciones or ''
                    })
                
                data.append({
                    'id': cuenta.id,
                    'clientName': client_name,
                    'clientPhone': client_phone,
                    'invoiceNumber': f"FAC-{cuenta.venta.id:05d}" if cuenta.venta else f"CTA-{cuenta.id:05d}",
                    'products': productos,
                    'saleDate': cuenta.fecha_emision.strftime('%Y-%m-%d'),
                    'dueDate': cuenta.fecha_vencimiento.strftime('%Y-%m-%d'),
                    'totalAmount': float(cuenta.monto_total),
                    'paidAmount': float(cuenta.monto_total - cuenta.saldo_pendiente),
                    'pendingBalance': float(cuenta.saldo_pendiente),
                    'status': cuenta.estado,
                    'observations': cuenta.observaciones or '',
                    'pagos': pagos  # Incluimos los pagos en la respuesta
                })
            
            return JsonResponse(data, safe=False)
            
        except Exception as e:
            return JsonResponse({'error': f'Error al cargar datos: {str(e)}'}, status=500)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            cuenta_id = data.get('cuenta_id')
            monto_pagado = float(data.get('monto_pagado'))
            metodo_pago = data.get('metodo_pago')
            referencia = data.get('referencia', '')
            
            cuenta = get_object_or_404(CuentaPorCobrar, id=cuenta_id)
            
            if monto_pagado <= 0:
                return JsonResponse({'error': 'El monto debe ser mayor a 0'}, status=400)
            
            if monto_pagado > cuenta.saldo_pendiente:
                return JsonResponse({'error': 'El monto excede el saldo pendiente'}, status=400)
            
            # Crear registro de pago
            pago = PagoCuentaCobrar(
                cuenta=cuenta,
                monto_pagado=monto_pagado,
                fecha_pago=date.today(),
                metodo_pago=metodo_pago,
                observaciones=referencia
            )
            pago.save()
            
            # Actualizar saldo de la cuenta
            cuenta.actualizar_saldo(monto_pagado)
            
            return JsonResponse({
                'success': True,
                'nuevo_saldo': float(cuenta.saldo_pendiente),
                'pago_id': pago.id
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def api_cuentas_por_cobrar_delete(request, cuenta_id):
    if request.method == 'DELETE':
        try:
            cuenta = get_object_or_404(CuentaPorCobrar, id=cuenta_id)
            
            if cuenta.estado != 'pagada':
                return JsonResponse({'error': 'Solo se pueden eliminar cuentas completamente pagadas'}, status=400)
            
            # Eliminar los pagos asociados primero
            cuenta.pagos.all().delete()
            cuenta.delete()
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

def obtener_pagos_cuenta(request, cuenta_id):
    """Obtiene todos los pagos de una cuenta específica"""
    try:
        cuenta = get_object_or_404(CuentaPorCobrar, id=cuenta_id)
        pagos = cuenta.pagos.all().order_by('-fecha_pago')
        
        pagos_data = []
        for pago in pagos:
            pagos_data.append({
                'id': pago.id,
                'monto_pagado': float(pago.monto_pagado),
                'fecha_pago': pago.fecha_pago.strftime('%d/%m/%Y'),
                'metodo_pago': pago.get_metodo_pago_display(),
                'referencia': pago.observaciones or 'N/A'
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
    """Genera un PDF con el comprobante de pago"""
    try:
        pago = get_object_or_404(PagoCuentaCobrar, id=pago_id)
        cuenta = pago.cuenta
        
        # Crear el PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        styles = getSampleStyleSheet()
        
        # Título
        title = Paragraph("COMPROBANTE DE PAGO", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        # Información del cliente
        client_name = getattr(cuenta.cliente, 'nombre', 'Cliente no disponible')
        client_phone = getattr(cuenta.cliente, 'telefono1', 'No disponible')
        
        # Información del pago
        data = [
            ['Número de Comprobante:', f"CP-{pago.id:05d}"],
            ['Fecha de Pago:', pago.fecha_pago.strftime('%d/%m/%Y')],
            ['Cliente:', client_name],
            ['Teléfono:', client_phone],
            ['Factura:', f"FAC-{cuenta.venta.id:05d}" if cuenta.venta else f"CTA-{cuenta.id:05d}"],
            ['Monto Pagado:', f"RD$ {pago.monto_pagado:,.2f}"],
            ['Método de Pago:', pago.get_metodo_pago_display()],
            ['Referencia:', pago.observaciones or 'N/A'],
            ['Saldo Anterior:', f"RD$ {(float(cuenta.saldo_pendiente) + float(pago.monto_pagado)):,.2f}"],
            ['Nuevo Saldo:', f"RD$ {cuenta.saldo_pendiente:,.2f}"],
        ]
        
        table = Table(data, colWidths=[200, 200])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 30))
        
        # Mensaje de agradecimiento
        thank_you = Paragraph("¡Gracias por su pago!", styles['Normal'])
        elements.append(thank_you)
        
        doc.build(elements)
        
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="comprobante_pago_{pago.id}.pdf"'
        
        return response
        
    except Exception as e:
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