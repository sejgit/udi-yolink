#!/usr/bin/env python3
"""
MIT License
"""

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)

from ctypes import set_errno
from os import truncate
#import udi_interface
#import sys
import time
from yolinkOutletV2 import YoLinkOutl



class udiYoOutlet(udi_interface.Node):
    id = 'yooutlet'
    '''
       drivers = [
            'GV0' = Outlet State
            'GV1' = OnDelay
            'GV2' = OffDelay
            'GV3' = Power
            'GV4' = Energy
            'GV5' = Online
            ]
    ''' 
    drivers = [
            {'driver': 'GV0', 'value': 99, 'uom': 25},
            {'driver': 'GV1', 'value': 0, 'uom': 57}, 
            {'driver': 'GV2', 'value': 0, 'uom': 57}, 
            {'driver': 'GV3', 'value': -1, 'uom': 30},
            {'driver': 'GV4', 'value': -1, 'uom': 33},
            {'driver': 'ST', 'value': 0, 'uom': 25},
            {'driver': 'GV20', 'value': 99, 'uom': 25},              

            ]


    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   

        logging.debug('udiYoOutlet INIT- {}'.format(deviceInfo['name']))
        self.n_queue = []
     
        self.yoAccess = yoAccess
        self.devInfo =  deviceInfo   
        self.yoOutlet = None
        self.node_ready = False
        self.powerSupported = True # assume 
        self.last_state = ''
        self.timer_update = 5
        self.timer_expires = 0
        self.onDelay = 0
        self.offDelay = 0

        polyglot.subscribe(polyglot.START, self.start, self.address)
        polyglot.subscribe(polyglot.STOP, self.stop)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
               

        # start processing events and create add our controller node
        polyglot.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        #self.node.setDriver('ST', 1, True, True)
        self.adr_list = []
        self.adr_list.append(address)

    def node_queue(self, data):
        self.n_queue.append(data['address'])

    def wait_for_node_done(self):
        while len(self.n_queue) == 0:
            time.sleep(0.1)
        self.n_queue.pop()



    def start(self):
        logging.info('start - YoLinkOutlet')
        self.node.setDriver('ST', 0, True, True)
        self.yoOutlet  = YoLinkOutl(self.yoAccess, self.devInfo, self.updateStatus)
        time.sleep(2)
        self.yoOutlet.initNode()
        time.sleep(2)
        self.yoOutlet.delayTimerCallback (self.updateDelayCountdown, self.timer_update)
        self.node_ready = True
    
    def stop (self):
        logging.info('Stop udiYoOutlet')
        self.node.setDriver('ST', 0, True, True)
        self.yoOutlet.shut_down()
        #if self.node:
        #    self.poly.delNode(self.node.address)

    def checkDataUpdate(self):
        if self.yoOutlet.data_updated():
            self.updateData()
        #if time.time() >= self.timer_expires - self.timer_update:
        #    self.node.setDriver('GV1', 0, True, False)
        #    self.node.setDriver('GV2', 0, True, False)

    def updateData(self):
        logging.info('udiYoOutlet updateData')
        if self.node is not None:
            
            if  self.yoOutlet.online:
                self.node.setDriver('ST',1, True, True)
                state = str(self.yoOutlet.getState()).upper()
                if state == 'ON':
                    self.node.setDriver('GV0',1 , True, True)
                    #if self.last_state != state:
                    #    self.node.reportCmd('DON')  
                elif state == 'OFF' :
                    self.node.setDriver('GV0', 0, True, True)
                    #if self.last_state != state:
                    #    self.node.reportCmd('DOF')  
                else:
                    self.node.setDriver('GV0', 99, True, True)
                self.last_state = state                
                tmp =  self.yoOutlet.getEnergy()
                if tmp != None:
                    power = round(tmp['power']/1000,3)
                    kwatt = round(tmp['watt']/1000,3)
                    self.node.setDriver('GV3', power, True, True)
                    self.node.setDriver('GV4', kwatt, True, True)
                #logging.debug('Timer info : {} '. format(time.time() - self.timer_expires))
                if time.time() >= self.timer_expires - self.timer_update and self.timer_expires != 0:
                    self.node.setDriver('GV1', 0, True, False)
                    self.node.setDriver('GV2', 0, True, False)
                if self.yoOutlet.suspended:
                    self.node.setDriver('GV20', 1, True, True)
                else:
                    self.node.setDriver('GV20', 0)


            else:
                self.node.setDriver('GV0', 99, True, True)
                self.node.setDriver('GV1', 0, True, True)
                self.node.setDriver('GV2', 0, True, True)
                self.node.setDriver('GV3', -1, True, True)
                self.node.setDriver('GV4', -1, True, True)
                self.node.setDriver('ST',0, True, True)
                self.node.setDriver('GV20', 2, True, True)
        



    def updateStatus(self, data):
        logging.info('udiYoOutlet updateStatus')
        self.yoOutlet.updateStatus(data)
        self.updateData()


    def updateDelayCountdown( self, timeRemaining):
        logging.debug('udiYoOutlet updateDelayCountDown:  delays {}'.format(timeRemaining))
        max_delay = 0
        for delayInfo in range(0, len(timeRemaining)):
            if 'ch' in timeRemaining[delayInfo]:
                if timeRemaining[delayInfo]['ch'] == 1:
                    if 'on' in timeRemaining[delayInfo]:
                        self.node.setDriver('GV1', timeRemaining[delayInfo]['on'], True, False)
                        if max_delay < timeRemaining[delayInfo]['on']:
                            max_delay = timeRemaining[delayInfo]['on']
                    if 'off' in timeRemaining[delayInfo]:
                        self.node.setDriver('GV2', timeRemaining[delayInfo]['off'], True, False)
                        if max_delay < timeRemaining[delayInfo]['off']:
                            max_delay = timeRemaining[delayInfo]['off']
        self.timer_expires = time.time()+max_delay

    
    def checkOnline(self):
        self.yoOutlet.refreshDevice()


    def set_outlet_on(self, command = None):
        logging.info('udiYoOutlet set_outlet_on')
        self.yoOutlet.setState('ON')
        self.node.setDriver('GV0',1 , True, True)
        #self.node.reportCmd('DON')

    def set_outlet_off(self, command = None):
        logging.info('udiYoOutlet set_outlet_off')
        self.yoOutlet.setState('OFF')
        self.node.setDriver('GV0',0 , True, True)
        #self.node.reportCmd('DOF')



    def outletControl(self, command):
        
        ctrl = int(command.get('value'))  
        logging.info('udiYoOutlet outletControl - {}'.format(ctrl))
        ctrl = int(command.get('value'))
        if ctrl == 1:
            self.yoOutlet.setState('ON')
            self.node.setDriver('GV0',1 , True, True)
            self.node.reportCmd('DON')
        elif ctrl == 0:
            self.yoOutlet.setState('OFF')
            self.node.setDriver('GV0',0 , True, True)
            self.node.reportCmd('DOF')
        elif ctrl == 2: #toggle
            state = str(self.yoOutlet.getState()).upper() 
            if state == 'ON':
                self.yoOutlet.setState('OFF')
                self.node.setDriver('GV0',0 , True, True)
                self.node.reportCmd('DOF')
            elif state == 'OFF':
                self.yoOutlet.setState('ON')
                self.node.setDriver('GV0',1 , True, True)
                self.node.reportCmd('DON')                
        elif ctrl == 5:
            logging.info('outletControl set Delays Executed: {} {}'.format(self.onDelay, self.offDelay))
            #self.yolink.setMultiOutDelay(self.port, self.onDelay, self.offDelay)
            self.node.setDriver('GV1', self.onDelay * 60, True, True)
            self.node.setDriver('GV2', self.offDelay * 60 , True, True)
            self.yoOutlet.setDelayList([{'on':self.onDelay, 'off':self.offDelay}]) 


            #Unknown remains unknown
        
        
    def prepOnDelay(self, command ):
        self.onDelay =int(command.get('value'))
        logging.info('udiYoOutlet prepOnDelay {}'.format(self.onDelay))
        #self.yoOutlet.setOnDelay(delay)
        #self.node.setDriver('GV1', self.onDelay*60, True, True)

    def prepOffDelay(self, command):

        self.offDelay =int(command.get('value'))
        logging.info('udiYoOutlet prefOffDelay Executed {}'.format(self.offDelay ))
        #self.yoOutlet.setOffDelay(delay)
        #self.node.setDriver('GV2', self.offDelay*60, True, True)

    def update(self, command = None):
        logging.info('Update Status Executed')
        self.yoOutlet.refreshDevice()
 


    commands = {
                'UPDATE': update,
                'DON'   : set_outlet_on,
                'DOF'   : set_outlet_off,
                'SWCTRL': outletControl, 
                'ONDELAY' : prepOnDelay,
                'OFFDELAY' : prepOffDelay 
                }




