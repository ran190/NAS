import json
import os

from models import Router, Interface, Igp, Neighbor, Network, AdjRib, RouteMap, AsPathAccessList, PrefixList, Community

from jinja2 import Environment, FileSystemLoader
def handle_network(network):
    ASList = {}
    for As in network['AS']:
        routerAsList = {}
        ipNetworkUsed = {}
        lastSubnetId = 0
        for router in As['routers']:
            routerObj = Router()
            routerObj.id = router['id']
            routerObj.hostname = router['name']
            intLoopback = Interface()
            intLoopback.name = 'Loopback0'
            intLoopback.add = As['IpLoopbackRange']['start']+router['id']
            intLoopback.prefix = 32
            intLoopback.mask= "255.255.255.255"
            if As['igp']['type'] == 'ospf':
                intLoopback.ospf = True
                intLoopback.ospfArea = "0"
                intLoopback.ospfCost = "0"
            elif As['igp']['type'] == 'rip':
                intLoopback.rip = True
            routerObj.loopback = intLoopback
            routerObj.interfaces = []
            for connection in router['connections']:
                inter = Interface()
                inter.name = "GigabitEthernet"+connection['interface']+"/0"
                #Si routeur def dans tab  
                if router['id'] in ipNetworkUsed:
                    #Si conx avec autre routeur def
                    if connection['router'] in ipNetworkUsed[router['id']]:
                        inter.add = As['IpRange']['start']+str(2+ipNetworkUsed[router['id']][connection['router']])
                        inter.prefix = 30
                        inter.mask= "255.255.255.252"
                    #Si conx avec autre routeur pas def   
                    else:
                        adresse = lastSubnetId ###As['IpRange']['start']+str(lastSubnetId)
                        ipNetworkUsed[router['id']][connection['router']] = adresse
                        #Si routeur auquel on se connecte pas def dans tab  
                        if connection['router'] not in ipNetworkUsed:
                            ipNetworkUsed[connection['router']] = {}
                        ipNetworkUsed[connection['router']][router['id']] = adresse
                        inter.add =  As['IpRange']['start']+str(1+lastSubnetId)
                        inter.prefix = 30
                        inter.mask= "255.255.255.252"
                        lastSubnetId += 4
                #Si routeur pas def dans tab 
                else:
                    
                    adresse = lastSubnetId
                    ipNetworkUsed[router['id']] = {}
                    ipNetworkUsed[router['id']][connection['router']] = adresse
                    if connection['router'] not in ipNetworkUsed:
                        ipNetworkUsed[connection['router']] = {}
                    ipNetworkUsed[connection['router']][router['id']] = adresse
                    inter.add =As['IpRange']['start']+str(1+lastSubnetId)
                    inter.prefix = 30
                    inter.mask= "255.255.255.252"
                    lastSubnetId += 4
                if As['igp']['type'] == 'ospf':
                    inter.ospf=True
                    inter.ospfArea = connection['ospfArea']
                    inter.ospfCost = connection['ospfCost']
                elif As['igp']['type'] == 'rip':
                    inter.rip= True
                routerObj.interfaces.append(inter)
            if(As['igp']['type'] == 'ospf'):
                ospf = Igp()
                ospf.process = 1
                ospf.routerId = As['igp']['routerID']+router['id']
                ospf.passiveInterfaces = []
                routerObj.ospf = ospf
            elif(As['igp']['type'] == 'rip'):
                rip = Igp()
                rip.process = routerObj.hostname
                rip.passiveInterfaces = []
                routerObj.rip = rip
            
            bgp = Igp()
            bgp.as_number = As['number']
            bgp.routerId = As['bgp']['routerID']+router['id']
            bgp.neighbors = []
            routerObj.bgp = bgp
            routerAsList[routerObj.id] = routerObj
        ASList[As['number']] = routerAsList
    
    


    return ASList

if __name__ == '__main__':
    environment = Environment(loader=FileSystemLoader('templates/'), trim_blocks = True, lstrip_blocks = True)
    template = environment.get_template('config_template.txt')
    f = open('reseau.json','r')
    load = json.load(f)
    ASList = handle_network(load)
    
    for AS in ASList.values():
        for router in AS.values():
            print(router.hostname)
            #if router.hostname == "R1117":
            #    print(router.routeMapIns)
            path = router.hostname+".cfg"
            f2 = open(path, "w")
            f2.write(template.render(router=router))
            f2.close()
            


    f.close()

