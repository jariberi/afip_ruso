# -*- coding: utf-8 -*-

"Módulo para obtener un ticket de autorización del web service WSAA de AFIP"

# Basado en wsaa.py de Mariano Reingart

__author__ = "Jorge Riberi (jariberi@gmail.com)"

import email, os, sys, warnings
from php import date
from pysimplesoap.client import SimpleXMLElement
from base import WebServiceAFIP

try:
    from M2Crypto import BIO, Rand, SMIME, SSL
except ImportError:
    warnings.warn("No es posible importar M2Crypto (OpenSSL)")
    BIO = Rand = SMIME = SSL = None
    # utilizar alternativa (ejecutar proceso por separado)
    from subprocess import Popen, PIPE
    from base64 import b64encode

# Constantes (si se usa el script de linea de comandos)
CERT_PROD = "C:\bases\prod.crt"  # El certificado X.509 obtenido de Seg. Inf.
CERT_TEST = "C:\bases\test.crt"  # El certificado X.509 obtenido de Seg. Inf.
PRIVATEKEY = "C:\bases\key.key"  # La clave privada del certificado CERT
SERVICE = "wsfe"  # El nombre del web service al que se le pide el TA

# WSAAURL: la URL para acceder al WSAA, verificar http/https y wsaa/wsaahomo
WSAAURL_PROD = "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl"  # PRODUCCION!!!
WSAAURL_TEST = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"  # homologacion (pruebas)

# Verificación del web server remoto, necesario para verificar canal seguro
CACERT = "conf/afip_ca_info.crt"  # WSAA CA Cert (Autoridades de Confiaza)


# No debería ser necesario modificar nada despues de esta linea

def create_tra(service=SERVICE, ttl=2400):
    "Crear un Ticket de Requerimiento de Acceso (TRA)"
    tra = SimpleXMLElement(
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<loginTicketRequest version="1.0">'
        '</loginTicketRequest>')
    tra.add_child('header')
    # El source es opcional. Si falta, toma la firma (recomendado).
    # tra.header.addChild('source','subject=...')
    # tra.header.addChild('destination','cn=wsaahomo,o=afip,c=ar,serialNumber=CUIT 33693450239')
    tra.header.add_child('uniqueId', str(date('U')))
    tra.header.add_child('generationTime', str(date('c', date('U') - ttl)))
    tra.header.add_child('expirationTime', str(date('c', date('U') + ttl)))
    tra.add_child('service', service)
    return tra.as_xml()


def sign_tra(tra, cert=CERT_TEST, privatekey=PRIVATEKEY, passphrase=""):
    "Firmar PKCS#7 el TRA y devolver CMS (recortando los headers SMIME)"

    if BIO:
        # Firmar el texto (tra) usando m2crypto (openssl bindings para python)
        buf = BIO.MemoryBuffer(tra)  # Crear un buffer desde el texto
        # Rand.load_file('randpool.dat', -1)     # Alimentar el PRNG
        s = SMIME.SMIME()  # Instanciar un SMIME
        # soporte de contraseña de encriptación (clave privada, opcional)
        callback = lambda *args, **kwarg: passphrase
        # Cargar clave privada y certificado
        if not privatekey.startswith("-----BEGIN RSA PRIVATE KEY-----"):
            # leer contenido desde archivo (evitar problemas Applink / MSVCRT)
            if os.path.exists(privatekey) and os.path.exists(cert):
                privatekey = open(privatekey).read()
                cert = open(cert).read()
            else:
                raise RuntimeError("Archivos no encontrados: %s, %s" % (privatekey, cert))
        # crear buffers en memoria de la clave privada y certificado:
        key_bio = BIO.MemoryBuffer(privatekey)
        crt_bio = BIO.MemoryBuffer(cert)
        s.load_key_bio(key_bio, crt_bio, callback)  # (desde buffer)
        p7 = s.sign(buf, 0)  # Firmar el buffer
        out = BIO.MemoryBuffer()  # Crear un buffer para la salida
        s.write(out, p7)  # Generar p7 en formato mail
        # Rand.save_file('randpool.dat')         # Guardar el estado del PRNG's

        # extraer el cuerpo del mensaje (parte firmada)
        msg = email.message_from_string(out.read())
        for part in msg.walk():
            filename = part.get_filename()
            if filename == "smime.p7m":  # es la parte firmada?
                return part.get_payload(decode=False)  # devolver CMS
    else:
        # Firmar el texto (tra) usando OPENSSL directamente
        try:
            if sys.platform == "linux2":
                openssl = "openssl"
            else:
                if sys.maxsize <= 2 ** 32:
                    openssl = r"c:\OpenSSL-Win32\bin\openssl.exe"
                else:
                    openssl = r"c:\OpenSSL-Win64\bin\openssl.exe"
            out = Popen([openssl, "smime", "-sign",
                         "-signer", cert, "-inkey", privatekey,
                         "-outform", "DER", "-nodetach"],
                        stdin=PIPE, stdout=PIPE, stderr=PIPE).communicate(tra)[0]
            return b64encode(out)
        except Exception, e:
            if e.errno == 2:
                warnings.warn("El ejecutable de OpenSSL no esta disponible en el PATH")
            raise


class WSAA(WebServiceAFIP):
    "Interfaz para el WebService de Autenticación y Autorización"

    def __init__(self, reintentos=1, produccion=False):
        WebServiceAFIP.__init__(self, reintentos, produccion)

    def CreateTRA(self, service="wsfe", ttl=2400):
        "Crear un Ticket de Requerimiento de Acceso (TRA)"
        return create_tra(service, ttl)

    def SignTRA(self, tra, cert, privatekey, passphrase=""):
        "Firmar el TRA y devolver CMS"
        return sign_tra(str(tra), cert.encode('latin1'), privatekey.encode('latin1'), passphrase.encode("utf8"))

    def Conectar(self):
        wsdl = WSAAURL_PROD if self.produccion else WSAAURL_TEST
        return WebServiceAFIP.Conectar(self, wsdl=wsdl, proxy="", wrapper=None, cacert=None, timeout=30,
                                       soap_server=None)

    def LoginCMS(self, cms):
        "Obtener ticket de autorización (TA)"
        results = self.client.loginCms(in0=str(cms))
        ta_xml = results['loginCmsReturn'].encode("utf-8")
        self.xml = ta = SimpleXMLElement(ta_xml)
        self.Token = str(ta.credentials.token)
        self.Sign = str(ta.credentials.sign)
        self.ExpirationTime = str(ta.header.expirationTime)
        return ta_xml


def obtener_permiso(ttl=120, servicio="wsfe", produccion=False):##Ruso: Factura electronica
    wsaa = WSAA(produccion=produccion)
    tra = wsaa.CreateTRA(service=servicio, ttl=ttl)
    cert = CERT_PROD if produccion else CERT_TEST
    cms = wsaa.SignTRA(tra, cert=cert, privatekey=PRIVATEKEY)
    try:
        if wsaa.Conectar():
            wsaa.LoginCMS(cms)
            return wsaa
        else:
            return None
    except Exception as e:
        print e
        return None