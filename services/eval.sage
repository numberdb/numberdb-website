'''
How to run service:
1. Run name server:
  sage -python -m Pyro5.nameserver
2. Run eval service:
  sage eval.sage
3. From separate project (running via sage or sage -python):
  import Pyro5.api
  E = Pyro5.api.Proxy("PYRONAME:eval")
  response = E.eval("24")
  result = loads(bytes(response,encoding='cp437'))
'''

import Pyro5.api
from sage.all import *
from sage.rings.all import *
import json

@Pyro5.api.expose
class SafeEval(object):
    def eval(self, source_sage):
        source_python = preparse(source_sage)
        e = eval(source_python)
        b = dumps(e) #of type bytes
        #s = b.hex() #long but should be fine
        #s = str(b,'utf-8','backslashreplace') #works but lot of backslashes
        s = str(b,'cp437') #good old Code Page 437
        return s
        
daemon = Pyro5.server.Daemon()         # make a Pyro daemon
ns = Pyro5.api.locate_ns()             # find the name server
uri = daemon.register(SafeEval)   # register the greeting maker as a Pyro object
ns.register("eval", uri)   # register the object with a name in the name server

print("Ready.")
daemon.requestLoop()
