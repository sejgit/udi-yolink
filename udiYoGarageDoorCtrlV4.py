#!/usr/bin/env python3
"""
Polyglot TEST v3 node server 


MIT License
"""
from os import truncate
import threading
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
#import sys
import time
from yolinkGarageDoorToggleV2 import YoLinkGarageDoorCtrl




class udiYoGarageDoor(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, start_done, configDoneHandler,  wait_for_node_done, node_queue, checkNameSync
    id = 'yogarage'
    
    '''
       drivers = [
            'ST' = Online
            ]

    ''' 
        
    drivers = [ 
            {'driver': 'ST', 'value': 0, 'uom': 25},
            {'driver': 'GV30', 'value': 99, 'uom': 25},
            {'driver': 'GV20', 'value': 99, 'uom': 25},
            ]


    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   

        
        self.yoAccess=yoAccess
        self.devInfo =  deviceInfo   
        self.yoDoorControl  = None
        self.node_ready = False
        self.configDone = False
        self.system_ready=False
        self._update_lock = threading.Lock()
        logging.debug('udiYoGarageDoor INIT - {}'.format(deviceInfo['name']))
        self.n_queue = []
        #polyglot.subscribe(polyglot.POLL, self.poll)
        polyglot.subscribe(polyglot.START, self.start, self.address)
        polyglot.subscribe(polyglot.STOP, self.stop)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        self.poly.subscribe(self.poly.CONFIGDONE, self.configDoneHandler)
        self.poly.subscribe(self.poly.STARTDONE, self.start_done)
        
        # start processing events and create add our controller node
        polyglot.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        self.adr_list = []
        self.adr_list.append(address)
        self.node_ready = True


    def start(self):
        logging.info('start - udiYoGarageDoor')
        while not self.node_ready or not self.configDone:
            time.sleep(0.5)
        self.my_setDriver('ST', 0)
        self.my_setDriver('GV30', 0)
        self.yoDoorControl = YoLinkGarageDoorCtrl(self.yoAccess, self.devInfo, self.updateStatus)
        time.sleep(2)
        self.my_setDriver('ST', 1)
        self.my_setDriver('GV30', 1)
        #time.sleep(3)
        self.system_ready=True

    def initNode(self):
        self.yoDoorControl.online = True
        #self.my_setDriver('ST', 1, True, True)
        
    def checkOnline(self):
        pass
        
    def checkDataUpdate(self):
        pass

    def updateLastTime(self):
        pass
        #self.my_setDriver('TIME', self.yoDoorControl.getTimeSinceUpdateMin(), 44)

    
    def stop (self):
        logging.info('Stop udiYoGarageDoor')
        self.my_setDriver('ST', 0)
        self.my_setDriver('GV30', 0)
        if getattr(self, 'yoDoorControl', None):
            self.yoDoorControl.shut_down()

    def updateStatus(self, data):
        logging.debug('updateStatus - udiYoGarageDoor')
        with self._update_lock:
            self.yoDoorControl.updateCallbackStatus(data)
            if self.yoDoorControl is not None:

                if self.yoDoorControl.suspended:
                    self.my_setDriver('GV20', 1)
                else:
                    self.my_setDriver('GV20', 0)

                if self.yoDoorControl.check_system_online():
                    self.my_setDriver('ST', 1)
                    self.my_setDriver('GV30', 1)
                else:
                    self.my_setDriver('GV20', 2)
                    #self.my_setDriver('ST', 0, True, True)

        


    def toggleDoor(self, command = None):
        logging.info('GarageDoor Toggle Door')
        self.yoDoorControl.toggleDevice()
        self.node.reportCmd('DON')
        time.sleep(1.5)
        self.node.reportCmd('DOF')

    commands = {
                    'TOGGLE': toggleDoor,
                    'DON'   : toggleDoor,
                    'DOF'   : toggleDoor,
                }




