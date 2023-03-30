import json
import os

from models import Router, Interface, Igp, Neighbor,Vrf

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
            routerObj.loopback = intLoopback
            routerObj.interfaces = []
            for connection in router['connections']:
                if connection:
                    inter = Interface()
                    inter.name = "GigabitEthernet"+connection['interface']+"/0"
                    if connection['mpls']=="True":
                        inter.mpls=True
                        #routerObj.mpls=True
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
                    routerObj.interfaces.append(inter)
            if(As['igp']['type'] == 'ospf'):
                ospf = Igp()
                ospf.process = 1
                ospf.routerId = As['igp']['routerID']+router['id']
                ospf.passiveInterfaces = []
                routerObj.ospf = ospf

            #Partie BGP
            bgp = Igp()
            #Si bgp sur routeur
            if router['bgp']=="True":
                bgp.bool=True
                bgp.as_number = As['number']
                bgp.routerId = As['bgp']['routerID']+router['id']
                bgp.neighbors = []
                routerObj.bgp = bgp
                #def les neighbor
                for routeur in As['routers']:
                    if routeur['id'] != router['id'] and routeur["bgp"]=="True":
                        neighbor = Neighbor()
                        neighbor.remote_as = As['number']
                        neighbor.ipAdd = As['IpLoopbackRange']['start']+routeur['id']
                        neighbor.sendCommunity = True
                        bgp.neighbors.append(neighbor)
                
            else:
                bgp.bool=False
            routerObj.bgp = bgp
            routerObj.vrfs={}
            routerAsList[routerObj.id] = routerObj
        ASList[As['number']] = routerAsList
    #Lien inter AS
    IpRangeLink=0
    as_link_ = network['ASLink']
    for link in as_link_['links']:
        IpRangeLink += 1
        #Def des interface 
        int1 = Interface()
        int2 = Interface()
        int1.name = "GigabitEthernet"+link['firstInterface']['id']+"/0"
        int2.name = "GigabitEthernet"+link['secondInterface']['id']+"/0"
        if as_link_['IpRange']['auto']=="True":
            add1 = network['ASLink']['IpRange']['start'] + IpRangeLink + "." + link['firstAS'] + "."+link['firstRouter']
            int1.add = add1
            add2 = network['ASLink']['IpRange']['start'] + str(hex(IpRangeLink)[2:]) + "." + link['secondAS'] +"."+ link['secondRouter']
            int2.add = add2
            int1.mask = network['ASLink']['IpRange']['prefix']
            int2.mask = network['ASLink']['IpRange']['prefix']
        else:
            int1.add = link["firstInterface"]["add"]
            int2.add = link["secondInterface"]["add"]
            int1.mask = link["firstInterface"]["mask"]
            int2.mask = link["secondInterface"]["mask"]
        ASList[link['firstAS']][link['firstRouter']].interfaces.append(int1)
        ASList[link['secondAS']][link['secondRouter']].interfaces.append(int2)
        #Rajout des int en passive int
        if hasattr(ASList[link['firstAS']][link['firstRouter']], "ospf"):
            int1.ospf = True
            int1.ospfArea = link['firstInterface']['ospfArea']

            ASList[link['firstAS']][link['firstRouter']].ospf.passiveInterfaces.append(int1.name)
        if hasattr(ASList[link['secondAS']][link['secondRouter']], "ospf"):
            int2.ospf = True
            int2.ospfArea = link['secondInterface']['ospfArea']

            ASList[link['secondAS']][link['secondRouter']].ospf.passiveInterfaces.append(int2.name)
        if link['vrfName']!="":
            vrf= Vrf()
            if link['vrfName'] in ASList[link['firstAS']][link['firstRouter']].vrfs :
                ASList[link['firstAS']][link['firstRouter']].vrfs[link['vrfName']].add.append(int2.add)
                
            else:
                vrf.as_target=link['secondAS']
                vrf.add=[int2.add]
                ASList[link['firstAS']][link['firstRouter']].vrfs[link['vrfName']]=vrf
            ASList[link['secondAS']][link['secondRouter']].vrfClient=True
            if hasattr(ASList[link['secondAS']][link['secondRouter']], "vrfClientAdd"):
                ASList[link['secondAS']][link['secondRouter']].vrfClientAdd.append([int1.add,link['firstAS']])
            else:
                ASList[link['secondAS']][link['secondRouter']].vrfClientAdd=[[int1.add,link['firstAS']]]
        else:
            neighb1 = Neighbor()
            neighb1.remote_as = link['firstAS']
            neighb1.ipAdd = int1.add
            neighb1.noLoopback = True
            neighb2 = Neighbor()
            neighb2.remote_as = link['secondAS']
            neighb2.ipAdd = int2.add
            neighb2.noLoopback = True
            ASList[link['firstAS']][link['firstRouter']].bgp.neighbors.append(neighb2)
            ASList[link['secondAS']][link['secondRouter']].bgp.neighbors.append(neighb1)
    


    return ASList

if __name__ == '__main__':
    environment = Environment(loader=FileSystemLoader('templates/'), trim_blocks = True, lstrip_blocks = True)
    template = environment.get_template('config_template.txt')
    f = open('reseau.json','r')
    load = json.load(f)
    ASList = handle_network(load)
    
    for AS in ASList.values():
        for router in AS.values():
            print(router.vrfs)
            #path = router.hostname+".cfg"
            path = "../Reseau_NAS/project-files/dynamips"
            cfg_file = 'i' + str(load['routerMap'][router.hostname]) + "_startup-config.cfg"
            real_path=""
            for root, dirs, files in os.walk(path):
                if cfg_file in files:
                    real_path = os.path.join(root, cfg_file)
            f2 = open(real_path, "w")
            f2.write(template.render(router=router))
            f2.close()
            print(router.hostname)

    f.close()

