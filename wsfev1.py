# -*- coding: utf-8 -*-

"""Módulo para obtener CAE/CAEA, código de autorización electrónico webservice 
WSFEv1 de AFIP (Factura Electrónica Nacional - Proyecto Version 1 - 2.5)
Según RG 2485/08, RG 2757/2010, RG 2904/2010 y RG2926/10 (CAE anticipado), 
RG 3067/2011 (RS - Monotributo), RG 3571/2013 (Responsables inscriptos IVA), 
RG 3668/2014 (Factura A IVA F.8001), RG 3749/2015 (R.I. y exentos)
"""

from wsaa import obtener_o_crear_permiso
from base import WebServiceAFIP

__author__ = "Jorge Riberi <jariberi@gmail.com>"

WSFEV1_URL_PROD = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
WSFEV1_URL_TEST = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"


class WSFEv1(WebServiceAFIP):
    "Interfaz para el WebService de Factura Electrónica Version 1 - 2.5"
    # Variables globales para WebServiceAFIP:
    factura = None

    def __init__(self, produccion=False, cuit=None):
        WebServiceAFIP.__init__(self, produccion=produccion)
        self.produccion = produccion
        self.Cuit = cuit
        self.CAE = self.Vencimiento = ""
        if not self.Token or self.Sign:
            permiso = obtener_o_crear_permiso(produccion=produccion)
            if permiso[0]:
                self.Token = permiso[1].Token
                self.Sign = permiso[1].Sign
                self.ExpirationTime = permiso[1].ExpirationTime
        self.Errores = self.Observaciones = self.Eventos = []

    def resetearOperacion(self):
        self.AppServerStatus = self.DbServerStatus = self.AuthServerStatus = None
        self.Resultado = ''
        self.LastID = self.LastCMP = self.CAE = self.CAEA = self.Vencimiento = ''
        self.CbteNro = self.CbtDesde = self.CbtHasta = self.PuntoVenta = None
        self.ImpTotal = self.ImpIVA = self.ImpOpEx = self.ImpNeto = self.ImptoLiq = self.ImpTrib = None
        self.EmisionTipo = self.Periodo = self.Orden = ""
        self.FechaCbte = self.FchVigDesde = self.FchVigHasta = self.FchTopeInf = self.FchProceso = ""

    def Conectar(self):
        wsdl = WSFEV1_URL_PROD if self.produccion else WSFEV1_URL_TEST
        return WebServiceAFIP.Conectar(self, wsdl=wsdl)

    def Dummy(self):
        "Obtener el estado de los servidores de la AFIP"
        result = self.client.service.FEDummy()['FEDummyResult']
        self.AppServerStatus = result['AppServer']
        self.DbServerStatus = result['DbServer']
        self.AuthServerStatus = result['AuthServer']
        return True

    def CrearFactura(self, concepto=1, tipo_doc=80, nro_doc="", tipo_cbte=1, punto_vta=0,
                     cbt_desde=0, cbt_hasta=0, imp_total=0.00, imp_tot_conc=0.00, imp_neto=0.00,
                     imp_iva=0.00, imp_trib=0.00, imp_op_ex=0.00, fecha_cbte="", fecha_venc_pago=None,
                     fecha_serv_desde=None, fecha_serv_hasta=None,  # --
                     moneda_id="PES", moneda_ctz="1.0000", caea=None, **kwargs
                     ):
        "Creo un objeto factura (interna)"
        # Creo una factura electronica de exportación 
        fact = {'tipo_doc': tipo_doc, 'nro_doc': nro_doc,
                'tipo_cbte': tipo_cbte, 'punto_vta': punto_vta,
                'cbt_desde': cbt_desde, 'cbt_hasta': cbt_hasta,
                'imp_total': imp_total, 'imp_tot_conc': imp_tot_conc,
                'imp_neto': imp_neto, 'imp_iva': imp_iva,
                'imp_trib': imp_trib, 'imp_op_ex': imp_op_ex,
                'fecha_cbte': fecha_cbte,
                'fecha_venc_pago': fecha_venc_pago,
                'moneda_id': moneda_id, 'moneda_ctz': moneda_ctz,
                'concepto': concepto,
                'cbtes_asoc': [],
                'tributos': [],
                'iva': [],
                'opcionales': [],
                }
        if fecha_serv_desde: fact['fecha_serv_desde'] = fecha_serv_desde
        if fecha_serv_hasta: fact['fecha_serv_hasta'] = fecha_serv_hasta
        if caea: fact['caea'] = caea

        self.factura = fact
        return True

    def AgregarCmpAsoc(self, tipo=1, pto_vta=0, nro=0):
        "Agrego un comprobante asociado a una factura (interna)"
        cmp_asoc = {'tipo': tipo, 'pto_vta': pto_vta, 'nro': nro}
        self.factura['cbtes_asoc'].append(cmp_asoc)
        return True

    def AgregarTributo(self, tributo_id=0, desc="", base_imp=0.00, alic=0, importe=0.00, **kwarg):
        "Agrego un tributo a una factura (interna)"
        tributo = {'tributo_id': tributo_id, 'desc': desc, 'base_imp': base_imp,
                   'alic': alic, 'importe': importe}
        self.factura['tributos'].append(tributo)
        return True

    def AgregarIva(self, iva_id=0, base_imp=0.0, importe=0.0):
        "Agrego un tributo a una factura (interna)"
        iva = {'iva_id': iva_id, 'base_imp': base_imp, 'importe': importe}
        self.factura['iva'].append(iva)
        return True

    def AgregarOpcional(self, opcional_id=0, valor=""):
        "Agrego un dato opcional a una factura (interna)"
        op = {'opcional_id': opcional_id, 'valor': valor}
        self.factura['opcionales'].append(op)
        return True

    # metodos principales para llamar remotamente a AFIP:

    def CAESolicitar(self):
        f = self.factura
        Auth = self.client.factory.create("FEAuthRequest")
        Auth.Token = self.Token
        Auth.Sign = self.Sign
        Auth.Cuit = self.Cuit  # YA esta sin guiones

        FeCAEReq = self.client.factory.create("FECAERequest")

        FeCabReq = self.client.factory.create("FECAECabRequest")
        FeCabReq.CantReg = 1
        FeCabReq.PtoVta = f['punto_vta']
        FeCabReq.CbteTipo = f['tipo_cbte']

        FeCAEReq.FeCabReq = FeCabReq

        FeDetReq = self.client.factory.create(
            "ArrayOfFECAEDetRequest")  # Array de detalles de comprobantes (FECAEDetRequest)

        FECAEDetRequest = self.client.factory.create("FECAEDetRequest")
        FECAEDetRequest.Concepto = f['concepto']
        FECAEDetRequest.DocTipo = f['tipo_doc']
        FECAEDetRequest.DocNro = f['nro_doc']
        FECAEDetRequest.CbteDesde = f['cbt_desde']
        FECAEDetRequest.CbteHasta = f['cbt_hasta']
        FECAEDetRequest.CbteFch = f['fecha_cbte']
        FECAEDetRequest.ImpTotal = f['imp_total']
        FECAEDetRequest.ImpTotConc = f['imp_tot_conc']
        FECAEDetRequest.ImpNeto = f['imp_neto']
        FECAEDetRequest.ImpOpEx = f['imp_op_ex']
        FECAEDetRequest.ImpTrib = f['imp_trib']
        FECAEDetRequest.ImpIVA = f['imp_iva']
        FECAEDetRequest.FchServDesde = f.get('fecha_serv_desde')
        FECAEDetRequest.FchServHasta = f.get('fecha_serv_hasta')
        FECAEDetRequest.FchVtoPago = f.get('fecha_venc_pago')
        FECAEDetRequest.MonId = f['moneda_id']
        FECAEDetRequest.MonCotiz = f['moneda_ctz']

        CbtesAsoc = self.client.factory.create("ArrayOfCbteAsoc")
        FECAEDetRequest.CbtesAsoc = CbtesAsoc

        Tributos = self.client.factory.create("ArrayOfTributo")
        FECAEDetRequest.Tributos = Tributos

        Iva = self.client.factory.create("ArrayOfAlicIva")
        for i in f['iva']:
            AlicIva = self.client.factory.create("AlicIva")
            AlicIva.Id = i['iva_id']
            AlicIva.BaseImp = i['base_imp']
            AlicIva.Importe = i['importe']
            Iva.AlicIva.append(AlicIva)
        FECAEDetRequest.Iva = Iva

        Opcionales = self.client.factory.create("ArrayOfOpcional")
        FECAEDetRequest.Opcionales = Opcionales

        FeDetReq.FECAEDetRequest.append(FECAEDetRequest)

        FeCAEReq.FeDetReq = FeDetReq

        FECAEResponse = self.client.service.FECAESolicitar(Auth=Auth,FeCAEReq=FeCAEReq)

        if "FeDetResp" in FECAEResponse:
            self.Resultado = FECAEResponse.FeDetResp.FECAEDetResponse[0].Resultado
            if self.Resultado == 'R':
                pass
            elif self.Resultado == 'A':
                self.CAE = FECAEResponse.FeDetResp.FECAEDetResponse[0].CAE
                self.Vencimiento = FECAEResponse.FeDetResp.FECAEDetResponse[0].CAEFchVto

            if 'Observaciones' in FECAEResponse.FeDetResp.FECAEDetResponse[0]:
                for obs in FECAEResponse.FeDetResp.FECAEDetResponse[0].Observaciones.Obs:
                    obser = {'code': obs.Code, 'msg': obs.Msg.encode('latin-1')}
                    self.Observaciones.append(obser)

        if "Errors" in FECAEResponse:
            for error in FECAEResponse.Errors.Err:
                err = {'code': error.Code, 'msg': error.Msg.encode('latin-1')}
                self.Errores.append(err)
            return False

        return True

    def CompTotXRequest(self):
        ret = self.client.FECompTotXRequest(
            Auth={'Token': self.Token, 'Sign': self.Sign, 'Cuit': self.Cuit},
        )

        result = ret['FECompTotXRequestResult']
        return result['RegXReq']

    def CompUltimoAutorizado(self, tipo_cbte, punto_vta):
        ret = self.client.FECompUltimoAutorizado(
            Auth={'Token': self.Token, 'Sign': self.Sign, 'Cuit': self.Cuit},
            PtoVta=punto_vta,
            CbteTipo=tipo_cbte,
        )

        result = ret['FECompUltimoAutorizadoResult']
        self.CbteNro = result['CbteNro']
        self.__analizar_errores(result)
        return self.CbteNro is not None and str(self.CbteNro) or ''

    def CompConsultar(self, tipo_cbte, punto_vta, cbte_nro):
        ret = self.client.FECompConsultar(
            Auth={'Token': self.Token, 'Sign': self.Sign, 'Cuit': self.Cuit},
            FeCompConsReq={
                'CbteTipo': tipo_cbte,
                'CbteNro': cbte_nro,
                'PtoVta': punto_vta,
            })

        result = ret['FECompConsultarResult']
        if 'ResultGet' in result:
            resultget = result['ResultGet']
            return resultget

    def ParamGetTiposCbte(self, sep="|"):
        "Recuperador de valores referenciales de códigos de Tipos de Comprobantes"
        ret = self.client.FEParamGetTiposCbte(
            Auth={'Token': self.Token, 'Sign': self.Sign, 'Cuit': self.Cuit},
        )
        res = ret['FEParamGetTiposCbteResult']
        return [(u"%(Id)s\t%(Desc)s\t%(FchDesde)s\t%(FchHasta)s" % p['CbteTipo']).replace("\t", sep)
                for p in res['ResultGet']]

    def ParamGetTiposConcepto(self, sep="|"):
        "Recuperador de valores referenciales de códigos de Tipos de Conceptos"
        ret = self.client.FEParamGetTiposConcepto(
            Auth={'Token': self.Token, 'Sign': self.Sign, 'Cuit': self.Cuit},
        )
        res = ret['FEParamGetTiposConceptoResult']
        return [(u"%(Id)s\t%(Desc)s\t%(FchDesde)s\t%(FchHasta)s" % p['ConceptoTipo']).replace("\t", sep)
                for p in res['ResultGet']]

    def ParamGetTiposDoc(self, sep="|"):
        "Recuperador de valores referenciales de códigos de Tipos de Documentos"
        ret = self.client.FEParamGetTiposDoc(
            Auth={'Token': self.Token, 'Sign': self.Sign, 'Cuit': self.Cuit},
        )
        res = ret['FEParamGetTiposDocResult']
        return [(u"%(Id)s\t%(Desc)s\t%(FchDesde)s\t%(FchHasta)s" % p['DocTipo']).replace("\t", sep)
                for p in res['ResultGet']]

    def ParamGetTiposIva(self, sep="|"):
        "Recuperador de valores referenciales de códigos de Tipos de Alícuotas"
        ret = self.client.FEParamGetTiposIva(
            Auth={'Token': self.Token, 'Sign': self.Sign, 'Cuit': self.Cuit},
        )
        res = ret['FEParamGetTiposIvaResult']
        return [(u"%(Id)s\t%(Desc)s\t%(FchDesde)s\t%(FchHasta)s" % p['IvaTipo']).replace("\t", sep)
                for p in res['ResultGet']]

    def ParamGetTiposMonedas(self, sep="|"):
        "Recuperador de valores referenciales de códigos de Monedas"
        ret = self.client.FEParamGetTiposMonedas(
            Auth={'Token': self.Token, 'Sign': self.Sign, 'Cuit': self.Cuit},
        )
        res = ret['FEParamGetTiposMonedasResult']
        return [(u"%(Id)s\t%(Desc)s\t%(FchDesde)s\t%(FchHasta)s" % p['Moneda']).replace("\t", sep)
                for p in res['ResultGet']]

    def ParamGetTiposOpcional(self, sep="|"):
        "Recuperador de valores referenciales de códigos de Tipos de datos opcionales"
        ret = self.client.FEParamGetTiposOpcional(
            Auth={'Token': self.Token, 'Sign': self.Sign, 'Cuit': self.Cuit},
        )
        res = ret['FEParamGetTiposOpcionalResult']
        return [(u"%(Id)s\t%(Desc)s\t%(FchDesde)s\t%(FchHasta)s" % p['OpcionalTipo']).replace("\t", sep)
                for p in res.get('ResultGet', [])]

    def ParamGetTiposTributos(self, sep="|"):
        "Recuperador de valores referenciales de códigos de Tipos de Tributos"
        "Este método permite consultar los tipos de tributos habilitados en este WS"
        ret = self.client.FEParamGetTiposTributos(
            Auth={'Token': self.Token, 'Sign': self.Sign, 'Cuit': self.Cuit},
        )
        res = ret['FEParamGetTiposTributosResult']
        return [(u"%(Id)s\t%(Desc)s\t%(FchDesde)s\t%(FchHasta)s" % p['TributoTipo']).replace("\t", sep)
                for p in res['ResultGet']]

    def ParamGetTiposPaises(self, sep="|"):
        "Recuperador de valores referenciales de códigos de Paises"
        "Este método permite consultar los tipos de tributos habilitados en este WS"
        ret = self.client.FEParamGetTiposPaises(
            Auth={'Token': self.Token, 'Sign': self.Sign, 'Cuit': self.Cuit},
        )
        res = ret['FEParamGetTiposPaisesResult']
        return [(u"%(Id)s\t%(Desc)s" % p['PaisTipo']).replace("\t", sep)
                for p in res['ResultGet']]

    def ParamGetCotizacion(self, moneda_id):
        "Recuperador de cotización de moneda"
        ret = self.client.FEParamGetCotizacion(
            Auth={'Token': self.Token, 'Sign': self.Sign, 'Cuit': self.Cuit},
            MonId=moneda_id,
        )
        self.__analizar_errores(ret)
        res = ret['FEParamGetCotizacionResult']['ResultGet']
        return str(res.get('MonCotiz', ""))

    def ParamGetPtosVenta(self, sep="|"):
        "Recuperador de valores referenciales Puntos de Venta registrados"
        ret = self.client.FEParamGetPtosVenta(
            Auth={'Token': self.Token, 'Sign': self.Sign, 'Cuit': self.Cuit},
        )
        res = ret.get('FEParamGetPtosVentaResult', {})
        return [(u"%(Nro)s\tEmisionTipo:%(EmisionTipo)s\tBloqueado:%(Bloqueado)s\tFchBaja:%(FchBaja)s" % p[
            'PtoVenta']).replace("\t", sep)
                for p in res.get('ResultGet', [])]
