from django.db import models
from django.utils import timezone
from django.db.models import Max
from datetime import date, timedelta

from decimal import Decimal

class Cliente(models.Model):
    cedula = models.CharField(max_length=13, unique=True)
    nombre = models.CharField(max_length=100)
    telefono1 = models.CharField(max_length=15)
    telefono2 = models.CharField(max_length=15, blank=True, null=True)
    direccion = models.TextField()
    limite_credito = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clientes'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return f"{self.nombre} ({self.cedula})"
    



class Suplidor(models.Model):
    nombre = models.CharField(max_length=100)
    rnc = models.CharField(max_length=13, unique=True)
    telefono = models.CharField(max_length=15)
    email = models.EmailField()
    direccion = models.TextField()
    contacto = models.CharField(max_length=100, blank=True, null=True)
    categoria = models.CharField(max_length=50)
    terminos_pago = models.CharField(max_length=20, choices=[
        ('contado', 'Contado'),
        ('15dias', '15 días'),
        ('30dias', '30 días'),
        ('45dias', '45 días'),
        ('60dias', '60 días'),
    ], default='30dias')
    estado = models.CharField(max_length=10, choices=[
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    ], default='activo')
    notas = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'suplidores'
        verbose_name_plural = 'Suplidores'

    def __str__(self):
        return self.nombre
    





class EntradaProducto(models.Model):
    UNIDAD_CHOICES = [
        ('kg', 'Kilogramos (kg)'),
        ('ton', 'Toneladas (ton)'),
        ('L', 'Litros (L)'),
        ('unidad', 'Unidades'),
        ('saco', 'Sacos'),
    ]
    
    CATEGORIA_CHOICES = [
        ('Fertilizantes Nitrogenados', 'Fertilizantes Nitrogenados'),
        ('Fertilizantes Fosfatados', 'Fertilizantes Fosfatados'),
        ('Fertilizantes Potásicos', 'Fertilizantes Potásicos'),
        ('Fertilizantes Compuestos', 'Fertilizantes Compuestos'),
        ('Fertilizantes Orgánicos', 'Fertilizantes Orgánicos'),
        ('Micronutrientes', 'Micronutrientes'),
    ]
    
    # Nuevo campo para el código único
    codigo = models.CharField(max_length=50, unique=True, blank=True)
    fecha = models.DateField(default=timezone.now)
    proveedor = models.ForeignKey('Suplidor', on_delete=models.CASCADE)  # Asumiendo que Suplidor está en el mismo archivo
    producto = models.CharField(max_length=255)
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    unidad = models.CharField(max_length=20, choices=UNIDAD_CHOICES)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Precios de venta sin ITBIS
    precio_venta1 = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_venta3 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Precios de venta con ITBIS
    precio_venta1_con_itbis = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta2_con_itbis = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_venta3_con_itbis = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    itbis_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.codigo:
            # Obtener el último código de la misma categoría
            ultimo_codigo = EntradaProducto.objects.filter(
                categoria=self.categoria
            ).aggregate(Max('codigo'))['codigo__max']
            
            if ultimo_codigo:
                # Incrementar el número del código
                try:
                    numero = int(ultimo_codigo.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    numero = 1
            else:
                numero = 1
            
            # Generar prefijo según la categoría
            prefijos = {
                'Fertilizantes Nitrogenados': 'FN',
                'Fertilizantes Fosfatados': 'FF',
                'Fertilizantes Potásicos': 'FP',
                'Fertilizantes Compuestos': 'FC',
                'Fertilizantes Orgánicos': 'FO',
                'Micronutrientes': 'MI',
            }
            
            prefijo = prefijos.get(self.categoria, 'PR')
            self.codigo = f"{prefijo}-{numero:04d}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.codigo} - {self.producto} - {self.cantidad} {self.unidad} - {self.fecha}"
    
    class Meta:
        verbose_name = "Entrada de Producto"
        verbose_name_plural = "Entradas de Productos"



class Compra(models.Model):
    CONDICION_CHOICES = [
        ('Contado', 'Contado'),
        ('Crédito', 'Crédito'),
    ]
    
    ESTADO_CHOICES = [
        ('Pagado', 'Pagado'),
        ('Pendiente', 'Pendiente'),
        ('Vencido', 'Vencido'),
    ]
    
    METODO_PAGO_CHOICES = [
        ('Efectivo', 'Efectivo'),
        ('Transferencia', 'Transferencia'),
        ('Cheque', 'Cheque'),
    ]
    
    suplidor = models.ForeignKey('Suplidor', on_delete=models.CASCADE)
    numero_factura = models.CharField(max_length=100, unique=True)
    fecha_factura = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    condicion = models.CharField(max_length=10, choices=CONDICION_CHOICES)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='Pendiente')
    notas = models.TextField(blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Campos para el pago
    fecha_pago = models.DateField(null=True, blank=True)
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, null=True, blank=True)
    referencia_pago = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'compras'
        verbose_name_plural = 'Compras'
        ordering = ['-fecha_factura']

    def __str__(self):
        return f"{self.numero_factura} - {self.suplidor.nombre}"

    def save(self, *args, **kwargs):
        if self.condicion == 'Contado':
            self.estado = 'Pagado'
            self.fecha_vencimiento = self.fecha_factura
        elif self.condicion == 'Crédito' and not self.fecha_vencimiento:
            from datetime import timedelta
            self.fecha_vencimiento = self.fecha_factura + timedelta(days=30)
        
        super().save(*args, **kwargs)




# models.py - Agregar métodos útiles a los modelos

class DetalleCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey('EntradaProducto', on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'detalle_compra'

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.costo_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producto.producto} - {self.cantidad}"
    
    # NUEVO MÉTODO: Obtener nombre del producto de manera consistente
    def get_nombre_producto(self):
        """Obtiene el nombre del producto de manera segura"""
        if hasattr(self.producto, 'producto'):
            return self.producto.producto
        return "Producto no disponible"

    # NUEVO MÉTODO: Obtener información completa del producto
    def get_info_producto(self):
        """Retorna información completa del producto para JSON"""
        return {
            'nombre': self.get_nombre_producto(),
            'cantidad': float(self.cantidad),
            'costo_unitario': float(self.costo_unitario),
            'subtotal': float(self.subtotal),
            'unidad': getattr(self.producto, 'unidad', 'N/A')
        }


class CuentaPorCobrar(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('parcial', 'Parcialmente Pagada'),
        ('pagada', 'Pagada'),
        ('vencida', 'Vencida'),
        ('anulada', 'Anulada'),  # Nuevo estado
    ]
    
    venta = models.ForeignKey('Venta', on_delete=models.CASCADE, related_name='cuentas_por_cobrar')
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE)
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField()
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)
    saldo_pendiente = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'cuentas_por_cobrar'
        verbose_name_plural = 'Cuentas por Cobrar'
    
    def __str__(self):
        return f"Cuenta #{self.id} - {self.cliente.nombre} - RD$ {self.saldo_pendiente}"
    
    def actualizar_saldo(self, monto_pagado):
        """Actualiza el saldo pendiente cuando se realiza un pago"""
        if monto_pagado <= self.saldo_pendiente and self.estado != 'anulada':
            self.saldo_pendiente -= monto_pagado
            
            if self.saldo_pendiente == 0:
                self.estado = 'pagada'
            else:
                self.estado = 'parcial'
            
            self.save()
            return True
        return False
    
    def verificar_vencimiento(self):
        """Verifica si la cuenta está vencida"""
        if date.today() > self.fecha_vencimiento and self.estado not in ['pagada', 'anulada']:
            self.estado = 'vencida'
            self.save()



class PagoCuentaCobrar(models.Model):
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque'),
    ]
    
    ESTADO_PAGO_CHOICES = [
        ('activo', 'Activo'),
        ('anulado', 'Anulado'),
    ]
    
    cuenta = models.ForeignKey('CuentaPorCobrar', on_delete=models.CASCADE, related_name='pagos')
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateField(default=timezone.now)  # CORREGIDO: default agregado
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default='efectivo')
    numero_recibo = models.CharField(max_length=20, unique=True, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_PAGO_CHOICES, default='activo')
    fecha_anulacion = models.DateTimeField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)  # CORREGIDO
    
    class Meta:
        db_table = 'pagos_cuentas_cobrar'
        verbose_name = 'Pago de cuenta por cobrar'
        verbose_name_plural = 'Pagos de cuentas por cobrar'
    
    def __str__(self):
        return f"Recibo {self.numero_recibo} - RD$ {self.monto_pagado}"
    
    def save(self, *args, **kwargs):
        # Generar número de recibo automáticamente si no existe
        if not self.numero_recibo:
            self.numero_recibo = self.generar_numero_recibo()
            
        # Asegurar que fecha_pago tenga un valor
        if not self.fecha_pago:
            self.fecha_pago = timezone.now().date()
            
        super().save(*args, **kwargs)
    
    def generar_numero_recibo(self):
        """Genera un número de recibo único en formato REC-000001"""
        from django.db.models import Max
        
        # Buscar el último número de recibo
        ultimo_recibo = PagoCuentaCobrar.objects.filter(
            numero_recibo__startswith='REC-'
        ).aggregate(Max('numero_recibo'))
        
        if ultimo_recibo['numero_recibo__max']:
            try:
                ultimo_numero = int(ultimo_recibo['numero_recibo__max'].split('-')[1])
                nuevo_numero = ultimo_numero + 1
            except (ValueError, IndexError):
                nuevo_numero = 1
        else:
            nuevo_numero = 1
        
        return f"REC-{nuevo_numero:06d}"
    
    def anular(self):
        """Anula el pago y restaura el saldo pendiente"""
        if self.estado == 'anulado':
            return False
            
        # Restaurar el saldo pendiente en la cuenta
        self.cuenta.saldo_pendiente += self.monto_pagado
        
        # Actualizar estado de la cuenta
        if self.cuenta.saldo_pendiente > 0:
            if self.cuenta.saldo_pendiente == self.cuenta.monto_total:
                self.cuenta.estado = 'pendiente'
            else:
                self.cuenta.estado = 'parcial'
        else:
            self.cuenta.estado = 'pagada'
            
        self.cuenta.save()
        
        # Marcar el pago como anulado
        self.estado = 'anulado'
        self.fecha_anulacion = timezone.now()
        self.save()
        
        return True

# models.py
class Venta(models.Model):
    TIPO_VENTA_CHOICES = [
        ('contado', 'Al Contado'),
        ('credito', 'A Crédito'),
    ]
    
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
    ]

    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('anulada', 'Anulada'),
    ]
    
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    cliente_nombre = models.CharField(max_length=255, blank=True, null=True)  # Nuevo campo para cliente no registrado
    fecha = models.DateTimeField(auto_now_add=True)
    tipo_venta = models.CharField(max_length=10, choices=TIPO_VENTA_CHOICES)
    metodo_pago = models.CharField(max_length=15, choices=METODO_PAGO_CHOICES)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    observacion = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activa')
    numero_factura = models.CharField(max_length=20, unique=True, blank=True, null=True)
    
    class Meta:
        db_table = 'ventas'
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
    
    def __str__(self):
        return f"Factura #{self.numero_factura} - {self.fecha.strftime('%Y-%m-%d')}"

    def save(self, *args, **kwargs):
        if not self.numero_factura:
            # Generar número de factura secuencial
            ultima_factura = Venta.objects.order_by('-id').first()
            if ultima_factura and ultima_factura.numero_factura:
                try:
                    ultimo_numero = int(ultima_factura.numero_factura.split('-')[1])
                    nuevo_numero = ultimo_numero + 1
                except (IndexError, ValueError):
                    nuevo_numero = 1
            else:
                nuevo_numero = 1
            
            self.numero_factura = f"F-{nuevo_numero:06d}"
        
        super().save(*args, **kwargs)
class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(EntradaProducto, on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'detalle_ventas'
        verbose_name = 'Detalle de Venta'
        verbose_name_plural = 'Detalles de Ventas'
    
    def __str__(self):
        return f"Detalle {self.id} - {self.producto.producto}"
    




# models.py
class Devolucion(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('procesada', 'Procesada'),
        ('rechazada', 'Rechazada'),
    ]
    
    MOTIVO_CHOICES = [
        ('defective', 'Producto defectuoso'),
        ('wrong_item', 'Artículo incorrecto'),
        ('not_as_described', 'No coincide con la descripción'),
        ('damaged', 'Producto dañado'),
        ('customer_change', 'Cambio de opinión del cliente'),
        ('other', 'Otro motivo'),
    ]
    
    venta = models.ForeignKey('Venta', on_delete=models.CASCADE, related_name='devoluciones')
    numero_devolucion = models.CharField(max_length=50, unique=True)
    fecha_devolucion = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    motivo = models.CharField(max_length=50, choices=MOTIVO_CHOICES)
    comentarios = models.TextField(blank=True)
    total_devolucion = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        if not self.numero_devolucion:
            # Generar número de devolución automático
            ultima_devolucion = Devolucion.objects.aggregate(Max('id'))['id__max'] or 0
            self.numero_devolucion = f'DEV-{timezone.now().year}-{ultima_devolucion + 1:04d}'
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.numero_devolucion} - Venta #{self.venta.id}"
    
    class Meta:
        verbose_name = "Devolución"
        verbose_name_plural = "Devoluciones"


class ItemDevolucion(models.Model):
    devolucion = models.ForeignKey(Devolucion, on_delete=models.CASCADE, related_name='items')
    detalle_venta = models.ForeignKey('DetalleVenta', on_delete=models.CASCADE)
    producto = models.ForeignKey('EntradaProducto', on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total_linea = models.DecimalField(max_digits=10, decimal_places=2)
    
    def save(self, *args, **kwargs):
        # Calcular el total de la línea
        self.total_linea = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.producto.codigo} - {self.cantidad}"