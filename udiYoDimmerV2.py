#!/usr/bin/env python3
"""
Polyglot TEST v3 node server 


MIT License
"""

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)

from os import truncate
#import udi_interface
#import sys
import time
from yolinkDimmerV2 import YoLinkDim

class udiYoSwitch(udi_interface.Node):
  
    id = 'yodimmer'
    drivers = [
            {'driver': 'GV0', 'value': 99, 'uom': 25},
            {'driver': 'GV1', 'value': 0, 'uom': 57}, 
            {'driver': 'GV2', 'value': 0, 'uom': 57}, 
            {'driver': 'GV3', 'value': 0, 'uom': 30},
            #{'driver': 'GV4', 'value': 0, 'uom': 33},
            {'driver': 'ST', 'value': 0, 'uom': 25},

            ]
    '''
       drivers = [
            'GV0' =  Dinner State
            'GV1' = OnDelay
            'GV2' = OffDelay
            'GV3' = Dimmer Brightness
            #'GV4' = Energy
            'ST' = Online/Connected
            ]

    ''' 

    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   
        logging.debug('udiYoSwitch INIT- {}'.format(deviceInfo['name']))
        self.devInfo =  deviceInfo   
        self.yoAccess = yoAccess
        self.yoSwitch = None
        self.timer_cleared = True
        self.n_queue = [] 
        self.last_state = ''
        self.timer_update = 5
        self.timer_expires = 0
        self.brightness = 50
        #self.Parameters = Custom(polyglot, 'customparams')
        # subscribe to the events we want
        #polyglot.subscribe(polyglot.CUSTOMPARAMS, self.parameterHandler)
        #polyglot.subscribe(polyglot.POLL, self.poll)
        polyglot.subscribe(polyglot.START, self.start, self.address)
        polyglot.subscribe(polyglot.STOP, self.stop)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
               

        # start processing events and create add our controller node
        polyglot.ready()
        self.poly.addNode(self)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
    
    def node_queue(self, data):
        self.n_queue.append(data['address'])

    def wait_for_node_done(self):
        while len(self.n_queue) == 0:
            time.sleep(0.1)
        self.n_queue.pop()


    def start(self):
        logging.info('start - udiYoSwitch')
        self.yoSwitch  = YoLinkDim(self.yoAccess, self.devInfo, self.updateStatus)
        time.sleep(2)
        self.yoSwitch.initNode()
        time.sleep(2)
        #self.node.setDriver('ST', 1, True, True)
        self.yoSwitch.delayTimerCallback (self.updateDelayCountdown, self.timer_update )



    def updateDelayCountdown (self, timeRemaining ) :
        logging.debug('updateDelayCountdown {}'.format(timeRemaining))
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
      

    def stop (self):
        logging.info('Stop udiYoSwitch')
        self.node.setDriver('ST', 0, True, True)
        self.yoSwitch.shut_down()
        #if self.node:
        #    self.poly.delNode(self.node.address)
            
    def checkOnline(self):
        self.yoSwitch.refreshDevice() 
    
    
    def checkDataUpdate(self):
        if self.yoSwitch.data_updated():
            self.updateData()


    def updateData(self):
       if self.node is not None:
            state =  self.yoSwitch.getState().upper()
            if self.yoSwitch.online:
                self.node.setDriver('ST', 1, True, True)
                if state == 'ON':
                    self.node.setDriver('GV0', 1, True, True)
                    #if self.last_state != state:
                    #    self.node.reportCmd('DON')  
                elif  state == 'OFF':
                    self.node.setDriver('GV0', 0, True, True)
                    #if self.last_state != state:
                    #    self.node.reportCmd('DOF')  
                else:
                    self.node.setDriver('GV0', 99, True, True)
                self.last_state = state
                
                #logging.debug('Timer info : {} '. format(time.time() - self.timer_expires))
                if time.time() >= self.timer_expires - self.timer_update and self.timer_expires != 0:
                    self.node.setDriver('GV1', 0, True, False)
                    self.node.setDriver('GV2', 0, True, False)                
            else:
                self.node.setDriver('ST', 0, True, True)
                self.node.setDriver('GV0', 99, True, True)
                self.node.setDriver('GV1', 0, True, False)
                self.node.setDriver('GV2', 0, True, False)    
           



    def updateStatus(self, data):
        logging.info('updateStatus - Switch')
        self.yoSwitch.updateStatus(data)
        self.updateData()
 
    def set_switch_on(self, command = None):
        logging.info('udiYoSwitch set_switch_on')  
        self.yoSwitch.setState('ON')
        self.node.setDriver('GV0',1 , True, True)
        #self.node.reportCmd('DON')

    def set_switch_off(self, command = None):
        logging.info('udiYoSwitch set_switch_off')  
        self.yoSwitch.setState('OFF')
        self.node.setDriver('GV0',0 , True, True)
        #self.node.reportCmd('DOF')

    def set_dimmer_level(self, command = None):
        brightness = int(command.get('value'))   
        #self.brightness = brightness
        logging.info('udiYoSwitch set_dimmer_level:{}'.format(brightness) )  
        if 0 >= brightness :
            #self.yoSwitch.setState('OFF')
            brightness = 0            
        elif 100>=  brightness:
            brightness = 100
        self.setBrightness(brightness) #????
        #self.yoSwitch.setState('ON')
        self.node.setDriver('GV3',brightness , True, True)

    def switchControl(self, command):
        logging.info('udiYoSwitch switchControl') 
        ctrl = int(command.get('value'))     
        if ctrl == 1:
            self.yoSwitch.setState('ON')
            self.node.setDriver('GV0',1 , True, True)
            self.node.reportCmd('DON')
        elif ctrl == 0:
            self.yoSwitch.setState('OFF')
            self.node.setDriver('GV0',0 , True, True)
            self.node.reportCmd('DOF')
        else: #toggle
            state = str(self.yoOutlet.getState()).upper() 
            if state == 'ON':
                self.yoSwitch.setState('OFF')
                self.node.setDriver('GV0',0 , True, True)
                self.node.reportCmd('DOF')
            elif state == 'OFF':
                self.yoSwitch.setState('ON')
                self.node.setDriver('GV0',1 , True, True)
                self.node.reportCmd('DON')
            #Unknown remains unknown
    

    def setOnDelay(self, command ):
        logging.info('udiYoSwitch setOnDelay')
        delay =int(command.get('value'))
        self.yoSwitch.setOnDelay(delay)
        self.node.setDriver('GV1', delay*60, True, True)

    def setOffDelay(self, command):
        logging.info('udiYoSwitch setOffDelay')
        delay =int(command.get('value'))
        self.yoSwitch.setOffDelay(delay)
        self.node.setDriver('GV2', delay*60, True, True)


    def update(self, command = None):
        logging.info('udiYoSwitch Update Status')
        self.yoSwitch.refreshDevice()
        #self.yoSwitch.refreshSchedules()     


    commands = {
                'UPDATE': update,
                'QUERY' : update,
                'DON'   : set_switch_on,
                'DOF'   : set_switch_off,
                'SWCTRL': switchControl, 
                'DIMLVL' : set_dimmer_level,
                'ONDELAY' : setOnDelay,
                'OFFDELAY' : setOffDelay 
                }




