from distutils.core import setup
import py2exe

setup(name="AFIP_RUSO",
      com_server=["afip_ruso"],
      options={"py2exe": {"includes": ["M2Crypto", "suds", "suds.client"]}}
      )
