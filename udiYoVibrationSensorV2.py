#!/usr/bin/env python3
"""
Polyglot TEST v3 node server 


MIT License
"""
from os import truncate
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)

import time
from yolinkVibrationSensorV2 import YoLinkVibrationSen



class udiYoVibrationSensor(udi_interface.Node):
    id = 'yovibrasens'
    
    '''
       drivers = [
            'GV0' = Vibration Alert
            'GV1' = Battery Level
            'ST' = Online
            ]

    ''' 
        
    drivers = [
            {'driver': 'GV0', 'value': 99, 'uom': 25}, 
            {'driver': 'GV1', 'value': 99, 'uom': 25},
            {'driver': 'GV2', 'value': 0, 'uom': 25},            
            {'driver': 'CLITEMP', 'value': 99, 'uom': 25},
            {'driver': 'ST', 'value': 0, 'uom': 25},
            #{'driver': 'ST', 'value': 0, 'uom': 25},
            ]


    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   

        logging.debug('udiYoVibrationSensor INIT- {}'.format(deviceInfo['name']))
        self.adress = address
        self.yoAccess = yoAccess
        self.devInfo =  deviceInfo
        self.yoVibrationSensor  = None
        self.node_ready = False
        self.last_state = 99
        self.cmd_state = 0
        self.n_queue = []
        #self.Parameters = Custom(polyglot, 'customparams')
        # subscribe to the events we want
        #polyglot.subscribe(polyglot.CUSTOMPARAMS, self.parameterHandler)
        #polyglot.subscribe(polyglot.POLL, self.poll)
        polyglot.subscribe(polyglot.START, self.start, self.address)
        polyglot.subscribe(polyglot.STOP, self.stop)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        

        # start processing events and create add our controller node
        polyglot.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        self.temp_unit = self.yoAccess.get_temp_unit()
        self.adr_list = []
        self.adr_list.append(address)


    def node_queue(self, data):
        self.n_queue.append(data['address'])

    def wait_for_node_done(self):
        while len(self.n_queue) == 0:
            time.sleep(0.1)
        self.n_queue.pop()



    def start(self):
        logging.info('start - udiYoVibrationSensor')
        self.yoVibrationSensor  = YoLinkVibrationSen(self.yoAccess, self.devInfo, self.updateStatus)
        time.sleep(2)
        self.yoVibrationSensor.initNode()
        self.node_ready = True
        #self.node.setDriver('ST', 1, True, True)

    
    def stop (self):
        logging.info('Stop udiYoVibrationSensor')
        self.node.setDriver('ST', 0, True, True)
        self.yoVibrationSensor.shut_down()
        #if self.node:
        #    self.poly.delNode(self.node.address)

    def checkOnline(self):
        self.yoVibrationSensor.refreshDevice()   
    
    def checkDataUpdate(self):
        if self.yoVibrationSensor.data_updated():
            self.updateData()


    def updateData(self):
        if self.node is not None:
            if self.yoVibrationSensor.online:               
                vib_state = self.getVibrationState()
                if vib_state == 1:
                    self.node.setDriver('GV0', 1, True, True)
                    if self.last_state != vib_state and self.cmd_state in [0,1]:
                        self.node.reportCmd('DON')   
                elif vib_state == 0:
                    self.node.setDriver('GV0', 0, True, True)
                    if self.last_state != vib_state and self.cmd_state in [0,2]:
                        self.node.reportCmd('DOF')  
                else:
                    self.node.setDriver('GV0', 99, True, True) 
                self.last_state = vib_state
                self.node.setDriver('GV1', self.yoVibrationSensor.getBattery(), True, True)
                self.node.setDriver('ST', 1, True, True)
                
                devTemp =  self.yoVibrationSensor.getDeviceTemperature()
                if devTemp != 'NA':
                    if self.temp_unit == 0:
                        self.node.setDriver('CLITEMP', round(devTemp,0), True, True, 4)
                    elif self.temp_unit == 1:
                        self.node.setDriver('CLITEMP', round(devTemp*9/5+32,0), True, True, 17)
                    elif self.temp_unit == 2:
                        self.node.setDriver('CLITEMP', round(devTemp+273.15,0), True, True, 26)
                else:
                    self.node.setDriver('CLITEMP', 99, True, True, 25)

            else:
                self.node.setDriver('GV0', 99, True, True)
                self.node.setDriver('GV1', 99, True, True)
                self.node.setDriver('CLITEMP', 99, True, True, 25)
                self.node.setDriver('ST', 1, True, True)




    def getVibrationState(self):
        if self.yoVibrationSensor.online:
            if  self.yoVibrationSensor.getVibrationState() == 'normal':
                return(0)
            else:
                return(1)
        else:
            return(99)

    def updateStatus(self, data):
        logging.info('updateStatus - udiYoLinkVibrationSensor')
        self.yoVibrationSensor.updateStatus(data)
        self.updateData()

    def set_cmd(self, command):
        ctrl = int(command.get('value'))   
        logging.info('udiYoVibrationSensor  set_cmd - {}'.format(ctrl))
        self.cmd_state = ctrl
        self.node.setDriver('GV2', self.cmd_state, True, True)

    def update(self, command = None):
        logging.info('udiYoVibrationSensor Update  Executed')
        self.yoVibrationSensor.refreshSensor()
       

    def noop(self, command = None):
        pass

    commands = {
                'SETCMD': set_cmd,        
                'UPDATE': update,
                'QUERY' : update, 
                'DON'   : noop,
                'DOF'   : noop
                }





