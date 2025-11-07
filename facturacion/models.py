from django.db import models
from django.utils import timezone
from django.db.models import Max
from datetime import date, timedelta

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
        if monto_pagado <= self.saldo_pendiente:
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
        if date.today() > self.fecha_vencimiento and self.estado != 'pagada':
            self.estado = 'vencida'
            self.save()



class PagoCuentaCobrar(models.Model):
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque'),
    ]
    
    cuenta = models.ForeignKey('CuentaPorCobrar', on_delete=models.CASCADE, related_name='pagos')
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateField()
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES, default='efectivo')
    observaciones = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'pagos_cuentas_cobrar'
    
    def __str__(self):
        return f"Pago de RD$ {self.monto_pagado} - {self.fecha_pago}"



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
    
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    tipo_venta = models.CharField(max_length=10, choices=TIPO_VENTA_CHOICES)
    metodo_pago = models.CharField(max_length=15, choices=METODO_PAGO_CHOICES)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    observacion = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'ventas'
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
    
    def __str__(self):
        return f"Venta #{self.id} - {self.fecha.strftime('%Y-%m-%d')}"

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