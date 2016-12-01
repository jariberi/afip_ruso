# -*- coding: utf-8 -*-

"""Módulo para obtener CAE/CAEA, código de autorización electrónico webservice 
WSFEv1 de AFIP (Factura Electrónica Nacional - Proyecto Version 1 - 2.5)
Según RG 2485/08, RG 2757/2010, RG 2904/2010 y RG2926/10 (CAE anticipado), 
RG 3067/2011 (RS - Monotributo), RG 3571/2013 (Responsables inscriptos IVA), 
RG 3668/2014 (Factura A IVA F.8001), RG 3749/2015 (R.I. y exentos)
"""
from wsaa import obtener_permiso

__author__ = "Jorge Riberi <jariberi@gmail.com>"

from base import WebServiceAFIP

LANZAR_EXCEPCIONES = False  # valor por defecto: True
WSFEV1_URL_PROD = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
WSFEV1_URL_TEST = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"


class WSFEv1(WebServiceAFIP):
    "Interfaz para el WebService de Factura Electrónica Version 1 - 2.5"
    # Variables globales para WebServiceAFIP:
    factura = None

    def __init__(self, reintentos=1, produccion=False, CUIT=None):
        WebServiceAFIP.__init__(self, reintentos)
        self.produccion = produccion
        self.Cuit = int(CUIT.replace("-", ""))
        if not self.Token or self.Sign:
            permiso = obtener_permiso(produccion=produccion)
            self.Token = permiso.Token
            self.Sign = permiso.Sign
        self.Errores = self.Observaciones = self.Eventos = []

    def resetearOperacion(self):
        WebServiceAFIP.resetearOperacion(self)
        self.AppServerStatus = self.DbServerStatus = self.AuthServerStatus = None
        self.Resultado = self.Motivo = self.Reproceso = ''
        self.LastID = self.LastCMP = self.CAE = self.CAEA = self.Vencimiento = ''
        self.CbteNro = self.CbtDesde = self.CbtHasta = self.PuntoVenta = None
        self.ImpTotal = self.ImpIVA = self.ImpOpEx = self.ImpNeto = self.ImptoLiq = self.ImpTrib = None
        self.EmisionTipo = self.Periodo = self.Orden = ""
        self.FechaCbte = self.FchVigDesde = self.FchVigHasta = self.FchTopeInf = self.FchProceso = ""

    def __analizar_errores(self, ret):
        "Comprueba y extrae errores si existen en la respuesta XML"
        if 'Errors' in ret:
            errores = ret['Errors']
            for error in errores:
                self.Errores.append("%s: %s" % (
                    error['Err']['Code'],
                    error['Err']['Msg'],
                ))
            self.ErrCode = ' '.join([str(error['Err']['Code']) for error in errores])
            self.ErrMsg = '\n'.join(self.Errores)
        if 'Events' in ret:
            events = ret['Events']
            self.Eventos = ['%s: %s' % (evt['Evt']['Code'], evt['Evt']['Msg']) for evt in events]

    def Conectar(self):
        wsdl = WSFEV1_URL_PROD if self.produccion else WSFEV1_URL_TEST
        return WebServiceAFIP.Conectar(self, wsdl=wsdl, proxy="", wrapper=None, cacert=None, timeout=30,
                                       soap_server=None)

    def Dummy(self):
        "Obtener el estado de los servidores de la AFIP"
        result = self.client.FEDummy()['FEDummyResult']
        self.AppServerStatus = result['AppServer']
        self.DbServerStatus = result['DbServer']
        self.AuthServerStatus = result['AuthServer']
        return True

    # los siguientes métodos no están decorados para no limpiar propiedades

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

    def EstablecerCampoFactura(self, campo, valor):
        if campo in self.factura or campo in ('fecha_serv_desde', 'fecha_serv_hasta', 'caea', 'fch_venc_cae'):
            self.factura[campo] = valor
            return True
        else:
            return False

    def AgregarCmpAsoc(self, tipo=1, pto_vta=0, nro=0, **kwarg):
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

    def AgregarIva(self, iva_id=0, base_imp=0.0, importe=0.0, **kwarg):
        "Agrego un tributo a una factura (interna)"
        iva = {'iva_id': iva_id, 'base_imp': base_imp, 'importe': importe}
        self.factura['iva'].append(iva)
        return True

    def AgregarOpcional(self, opcional_id=0, valor="", **kwarg):
        "Agrego un dato opcional a una factura (interna)"
        op = {'opcional_id': opcional_id, 'valor': valor}
        self.factura['opcionales'].append(op)
        return True

    def ObtenerCampoFactura(self, *campos):
        "Obtener el valor devuelto de AFIP para un campo de factura"
        # cada campo puede ser una clave string (dict) o una posición (list)
        ret = self.factura
        for campo in campos:
            if isinstance(ret, dict) and isinstance(campo, basestring):
                ret = ret.get(campo)
            elif isinstance(ret, list) and len(ret) > campo:
                ret = ret[campo]
            else:
                self.Excepcion = u"El campo %s solicitado no existe" % campo
                ret = None
            if ret is None:
                break
        return str(ret)

    # metodos principales para llamar remotamente a AFIP:

    def CAESolicitar(self):
        f = self.factura
        FeCAEReq = {
            'FeCabReq': {'CantReg': 1,
                         'PtoVta': f['punto_vta'],
                         'CbteTipo': f['tipo_cbte']},
            'FeDetReq': [{'FECAEDetRequest': {
                'Concepto': f['concepto'],
                'DocTipo': f['tipo_doc'],
                'DocNro': f['nro_doc'],
                'CbteDesde': f['cbt_desde'],
                'CbteHasta': f['cbt_hasta'],
                'CbteFch': f['fecha_cbte'],
                'ImpTotal': f['imp_total'],
                'ImpTotConc': f['imp_tot_conc'],
                'ImpNeto': f['imp_neto'],
                'ImpOpEx': f['imp_op_ex'],
                'ImpTrib': f['imp_trib'],
                'ImpIVA': f['imp_iva'],
                # Fechas solo se informan si Concepto in (2,3)
                'FchServDesde': f.get('fecha_serv_desde'),
                'FchServHasta': f.get('fecha_serv_hasta'),
                'FchVtoPago': f.get('fecha_venc_pago'),
                'FchServDesde': f.get('fecha_serv_desde'),
                'FchServHasta': f.get('fecha_serv_hasta'),
                'FchVtoPago': f['fecha_venc_pago'],
                'MonId': f['moneda_id'],
                'MonCotiz': f['moneda_ctz'],
                'CbtesAsoc': f['cbtes_asoc'] and [
                    {'CbteAsoc': {
                        'Tipo': cbte_asoc['tipo'],
                        'PtoVta': cbte_asoc['pto_vta'],
                        'Nro': cbte_asoc['nro']}}
                    for cbte_asoc in f['cbtes_asoc']] or None,
                'Tributos': f['tributos'] and [
                    {'Tributo': {
                        'Id': tributo['tributo_id'],
                        'Desc': tributo['desc'],
                        'BaseImp': tributo['base_imp'],
                        'Alic': tributo['alic'],
                        'Importe': tributo['importe'],
                    }}
                    for tributo in f['tributos']] or None,
                'Iva': f['iva'] and [
                    {'AlicIva': {
                        'Id': iva['iva_id'],
                        'BaseImp': iva['base_imp'],
                        'Importe': iva['importe'],
                    }}
                    for iva in f['iva']] or None,
                'Opcionales': [
                                  {'Opcional': {
                                      'Id': opcional['opcional_id'],
                                      'Valor': opcional['valor'],
                                  }} for opcional in f['opcionales']] or None,
            }
            }]
        }
        ret = self.client.FECAESolicitar(
            Auth={'Token': self.Token, 'Sign': self.Sign, 'Cuit': self.Cuit},
            FeCAEReq=FeCAEReq)
        print "!!!!!!!!!!!!RET:" + str(ret)
        result = ret['FECAESolicitarResult']
        if 'FeCabResp' in result:
            fecabresp = result['FeCabResp']
            fedetresp = result['FeDetResp'][0]['FECAEDetResponse']
            if 'Errors' in result or 'Observaciones' in fedetresp:
                for error in result.get('Errors', []):
                    self.Errores.append({'code': error['Err']['Code'], 'msg': error['Err']['Msg'].encode('latin-1')})
                for obs in fedetresp.get('Observaciones', []):
                    print obs
                    self.Observaciones.append({'code': obs['Obs']['Code'], 'msg': obs['Obs']['Msg'].encode('latin-1')})
            self.Resultado = fecabresp['Resultado']
            self.CAE = fedetresp['CAE'] and str(fedetresp['CAE']) or ""
            self.Vencimiento = fedetresp['CAEFchVto'] or ""
        return self.CAE

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
