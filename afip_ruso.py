from wsfev1 import WSFEv1

__author__ = 'JORGE RIBERI'


class AFIP_RUSO:
    _public_methods_ = ['getToken', 'getSign', 'crearFactura', 'agregarIva', 'aprobar', 'getErrores',
                        'getObservaciones', 'setCUIT', 'setProduccion', 'consultarUltimoComprobante']
    _public_attrs_ = ['CAE', 'vencimiento', 'aprobado']
    _reg_progid_ = "AFIP_RUSO"
    _reg_clsid_ = "{13CA094F-068E-446E-A0C9-4938263E5F8E}"

    def __init__(self):
        self.CUIT = None
        self.produccion = False
        self.wsfev1 = None
        self.CAE = self.vencimiento = None
        self.errores = self.observaciones = None
        self.aprobado = None

    def setCUIT(self, cuit):
        self.CUIT = cuit

    def setProduccion(self, produccion):
        self.produccion = produccion

    def getSign(self):
        return self.wsfev1.Sign

    def getToken(self):
        return self.wsfev1.Token

    def getErrores(self):
        if self.wsfev1.Errores:
            return str(
                reduce(lambda x, y: str(x['code']) + ";" + str(x['msg']) + ";" + str(y['code']) + ";" + str(y['msg']),
                       self.wsfev1.Errores))
        return ""

    def getObservaciones(self):
        if self.wsfev1.Observaciones:
            return str(
                reduce(lambda x, y: str(x['code']) + ";" + str(x['msg']) + ";" + str(y['code']) + ";" + str(y['msg']),
                       self.wsfev1.Observaciones))
        return ""

    def crearFactura(self, concepto=None, tipo_doc=None, nro_doc=None, tipo_cbte=None,
                     punto_vta=None, cbt_desde=None, cbt_hasta=None, imp_total=None,
                     imp_tot_conc=None, imp_neto=None, imp_iva=None,
                     fecha_cbte=None, fecha_venc_pago=None, fecha_serv_hasta=None,
                     moneda_id=None, moneda_ctz=None):
        self.wsfev1 = WSFEv1(produccion=self.produccion, cuit=self.CUIT)
        self.wsfev1.CrearFactura(concepto=concepto, tipo_doc=tipo_doc, nro_doc=nro_doc, tipo_cbte=tipo_cbte,
                                 punto_vta=punto_vta, cbt_desde=cbt_desde, cbt_hasta=cbt_hasta, imp_total=imp_total,
                                 imp_tot_conc=imp_tot_conc, imp_neto=imp_neto, imp_iva=imp_iva, fecha_cbte=fecha_cbte,
                                 fecha_venc_pago=fecha_venc_pago, fecha_serv_hasta=fecha_serv_hasta,
                                 moneda_id=moneda_id,
                                 moneda_ctz=moneda_ctz)

    def agregarIva(self, iva_id=None, base_imp=None, importe=None):
        self.wsfev1.AgregarIva(iva_id=iva_id, base_imp=base_imp, importe=importe)

    def aprobar(self):
        self.wsfev1.Conectar()
        if self.wsfev1.CAESolicitar():
            self.CAE = self.wsfev1.CAE
            self.vencimiento = self.wsfev1.Vencimiento
            self.observaciones = self.wsfev1.Observaciones
            self.aprobado = True
            return True
        else:
            self.aprobado = False
            self.errores = self.wsfev1.Errores
            self.observaciones = self.wsfev1.Observaciones
            return False

    def consultarUltimoComprobante(self, tipo_cbte, punto_vta):
        if not self.wsfev1.client:
            self.wsfev1.Conectar()
        return self.wsfev1.CompUltimoAutorizado(tipo_cbte=tipo_cbte, punto_vta=punto_vta)


if __name__ == '__main__':
    import win32com.server.register

    win32com.server.register.UseCommandLine(AFIP_RUSO)
