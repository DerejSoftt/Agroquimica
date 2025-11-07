from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),
    path('inventario', views.inventario, name='inventario'),
    path('registrodeclientes', views.registrodeclientes, name='registrodeclientes'),
    path('guardar-cliente/', views.guardar_cliente, name='guardar_cliente'),
    path('gestiondeclientes', views.gestiondeclientes, name='gestiondeclientes'),
    path('obtener-clientes/', views.obtener_clientes, name='obtener_clientes'),
    path('actualizar-cliente/<int:cliente_id>/', views.actualizar_cliente, name='actualizar_cliente'),
    path('eliminar-cliente/<int:cliente_id>/', views.eliminar_cliente, name='eliminar_cliente'),

    path('resgistrodesuplidores', views.resgistrodesuplidores, name='resgistrodesuplidores'),
    path('guardar-suplidor/', views.guardar_suplidor, name='guardar_suplidor'),
    path('gestiondesuplidores', views.gestiondesuplidores, name='gestiondesuplidores'),
    path('obtener-suplidores/', views.obtener_suplidores, name='obtener_suplidores'),
     path('actualizar_suplidor/<int:suplidor_id>/', views.actualizar_suplidor, name='actualizar_suplidor'),
    path('eliminar-suplidor/<int:suplidor_id>/', views.eliminar_suplidor, name='eliminar_suplidor'),
    path('entrada', views.entrada, name='entrada'),
     path('guardar-entrada/', views.guardar_entrada, name='guardar_entrada'),
     path('compras', views.compras, name='compras'),
   path('guardar-compra/', views.guardar_compra, name='guardar_compra'),
   path('cuantaporpagar', views.cuantaporpagar, name='cuantaporpagar'),
       path('cuentas-por-pagar/datos/', views.cuentas_por_pagar_datos, name='cuentas_por_pagar_datos'),
    path('cuentas-por-pagar/procesar-pago/<int:compra_id>/', views.procesar_pago_compra, name='procesar_pago_compra'),
    path('cuentas-por-pagar/eliminar/<int:compra_id>/', views.eliminar_compra, name='eliminar_compra'),
    path('cuentas-por-pagar/obtener/<int:compra_id>/', views.obtener_compra_edicion, name='obtener_compra_edicion'),
    path('cuentas-por-pagar/actualizar/<int:compra_id>/', views.actualizar_compra, name='actualizar_compra'),
    path('facturacion', views.facturacion, name='facturacion'),
    path('buscar_clientes/', views.buscar_clientes, name='buscar_clientes'),
    path('procesar_venta/', views.procesar_venta, name='procesar_venta'),
    path('facturas/<int:venta_id>/', views.factura_detalle, name='factura_detalle'),
    path('cuentaporcobrar', views.cuentaporcobrar, name='cuentaporcobrar'),
    path('api/cuentas-por-cobrar/', views.api_cuentas_por_cobrar, name='api_cuentas_por_cobrar'),
    path('api/cuentas-por-cobrar/<int:cuenta_id>/', views.api_cuentas_por_cobrar_delete, name='api_cuentas_por_cobrar_delete'),
    path('comprobante-pago/<int:pago_id>/', views.generar_comprobante_pago, name='generar_comprobante_pago'),
     path('api/obtener-ultimo-pago/<int:cuenta_id>/', views.obtener_ultimo_pago, name='obtener_ultimo_pago'),
    ]
