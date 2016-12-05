# -*- coding: utf8 -*-
from suds.client import Client
__author__ = "Jorge Riberi <jariberi@gmail.com>"

class WebServiceAFIP:
    "Infraestructura basica para interfaces webservices de AFIP"

    def __init__(self, produccion=False):
        self.produccion = produccion
        self.xml = self.client = None
        self.Token = self.Sign = self.ExpirationTime = None
        self.excMsg = self.excCode = None

    def Conectar(self, wsdl=None):
        self.client = Client(url=wsdl)
        return True
