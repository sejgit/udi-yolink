#!/usr/bin/env python3
"""
Polyglot TEST v3 node server 


MIT License
"""

try:
    import udi_interface
    logging = udi_interface.LOGGER
    #logging = getlogger('udiDimmerV2')
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)

from os import truncate
#import udi_interface
#import sys
import time
from yolinkDimmerV3 import YoLinkDim

class udiYoDimmer(udi_interface.Node):
  
    id = 'yodimmer'
    drivers = [
            {'driver': 'GV0', 'value': 99, 'uom': 25},
            {'driver': 'GV1', 'value': 0, 'uom': 57}, 
            {'driver': 'GV2', 'value': 0, 'uom': 57}, 
            {'driver': 'GV3', 'value': 0, 'uom': 51},
            {'driver': 'ST', 'value': 0, 'uom': 25},
            {'driver': 'GV20', 'value': 99, 'uom': 25},            

            ]
    '''
       drivers = [
            'GV0' =  Dinner State
            'GV1' = OnDelay
            'GV2' = OffDelay
            'GV3' = Dimmer Brightness
            #'GV4' = Energy
            'ST' = Online/Connected
            'GV20' = Suspended state
            ]

    ''' 

    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   
        logging.debug('udiYoDimmer INIT- {}'.format(deviceInfo['name']))
        self.devInfo =  deviceInfo   
        self.yoAccess = yoAccess
        self.yoDimmer = None
        self.node_ready = False
        self.timer_cleared = True
        self.n_queue = [] # one queue for all
        self.last_state = ''
        self.timer_update = 5
        self.timer_expires = 0
        self.onDelay = 0
        self.offDelay = 0

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
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        self.adr_list = []
        self.adr_list.append(address)

    def node_queue(self, data):
        self.n_queue.append(data['address'])

    def wait_for_node_done(self):
        while len(self.n_queue) == 0:
            time.sleep(0.1)
        self.n_queue.pop()


    def start(self):
        logging.info('start - udiYoDimmer')
        self.node.setDriver('ST', 0, True, True)
        self.yoDimmer  = YoLinkDim(self.yoAccess, self.devInfo, self.updateStatus)
        time.sleep(2)
        self.yoDimmer.initNode()
        time.sleep(2)
        #self.node.setDriver('ST', 1, True, True)
        self.yoDimmer.delayTimerCallback (self.updateDelayCountdown, self.timer_update )
        self.node_ready = True


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
        logging.info('Stop udiyoDimmer')
        self.node.setDriver('ST', 0, True, True)
        self.yoDimmer.shut_down()
        #if self.node:
        #    self.poly.delNode(self.node.address)
            
    #def checkOnline(self):
    #    self.yoDimmer.refreshDevice()
    
    
    def checkDataUpdate(self):
        if self.yoDimmer.data_updated():
            self.updateData()


    def updateData(self):
       if self.node is not None:
            state =  self.yoDimmer.getState().upper()
            if self.yoDimmer.online:
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
                self.node.setDriver('GV3', self.yoDimmer.brightness, True, True)
                #logging.debug('Timer info : {} '. format(time.time() - self.timer_expires))
                if time.time() >= self.timer_expires - self.timer_update and self.timer_expires != 0:
                    self.node.setDriver('GV1', 0, True, False)
                    self.node.setDriver('GV2', 0, True, False) 
                if self.yoDimmer.suspended:
                    self.node.setDriver('GV20', 1, True, True)
                else:
                     self.node.setDriver('GV20', 0)
            else:
                self.node.setDriver('ST', 0, True, True)
                self.node.setDriver('GV0', 99, True, True)
                self.node.setDriver('GV1', 0, True, False)
                self.node.setDriver('GV2', 0, True, False)
                self.node.setDriver('GV20', 2, True, True)
           

    def updateStatus(self, data):
        logging.info('updateStatus - Switch')
        self.yoDimmer.updateStatus(data)
        self.updateData()
 
    def set_switch_on(self, command = None):
        logging.info('udiyoDimmer set_switch_on')  
        self.yoDimmer.setState('ON')
        self.node.setDriver('GV0',1 , True, True)
        self.node.reportCmd('DON')

    def set_switch_off(self, command = None):
        logging.info('udiYoDimmer set_switch_off')  
        self.yoDimmer.setState('OFF')
        self.node.setDriver('GV0',0 , True, True)
        self.node.reportCmd('DOF')

    def set_switch_fon(self, command = None):
        logging.info('udiyoDimmer set_switch_on')  
        self.yoDimmer.setState('ON')
        self.node.setDriver('GV0',1 , True, True)
        self.node.reportCmd('DFON')

    def set_switch_foff(self, command = None):
        logging.info('udiYoDimmer set_switch_off')  
        self.yoDimmer.setState('OFF')
        self.node.setDriver('GV0',0 , True, True)
        self.node.reportCmd('DFOF')



    def set_dimmer_level(self, command = None):
        brightness = int(command.get('value'))   
        #self.brightness = brightness
        logging.info('udiYoDimmer set_dimmer_level:{}'.format(brightness) )  
        if 0 >= brightness :
            #self.yoDimmer.setState('OFF')
            brightness = 0            
        elif 100 <=  brightness:
            brightness = 100
        self.yoDimmer.setBrightness(brightness) #????
        self.node.setDriver('GV3',brightness , True, True)

    def switchControl(self, command):
        logging.info('udiYoDimmer switchControl') 
        ctrl = command.get('value')   
        logging.debug('switchControl : {}'.format(ctrl))
        if ctrl == 1:
            self.yoDimmer.setState('ON')
            self.node.setDriver('GV0',1 , True, True)
            self.node.reportCmd('DON')
        elif ctrl == 0:
            self.yoDimmer.setState('OFF')
            self.node.setDriver('GV0',0 , True, True)
            self.node.reportCmd('DOF')
        elif ctrl == 2: #toggle
            state = str(self.yoDimmer.getState()).upper() 
            logging.debug('switchControl : {}, {}'.format(ctrl, state))
            if state == 'ON':
                self.yoDimmer.setState('OFF')
                self.node.setDriver('GV0',0 , True, True)
                self.node.reportCmd('DOF')
            elif state == 'OFF':
                self.yoDimmer.setState('ON')
                self.node.setDriver('GV0',1 , True, True)
                self.node.reportCmd('DON')
            #Unknown remains unknown
        elif ctrl == 5:
            logging.info('switchControl set Delays Executed: {} {}'.format(self.onDelay, self.offDelay))
            #self.yolink.setMultiOutDelay(self.port, self.onDelay, self.offDelay)
            self.node.setDriver('GV1', self.onDelay * 60, True, True)
            self.node.setDriver('GV2', self.offDelay * 60 , True, True)
            self.yoDimmer.setDelayList([{'on':self.onDelay, 'off':self.offDelay}]) 

    def setOnDelay(self, command ):
        logging.info('udiYoDimmer setOnDelay')
        self.onDelay =int(command.get('value'))
        self.yoDimmer.setOnDelay(self.onDelay )
        self.node.setDriver('GV1', self.onDelay *60, True, True)

    def setOffDelay(self, command):
        logging.info('udiYoDimmer setOffDelay')
        self.offDelay  =int(command.get('value'))
        self.yoDimmer.setOffDelay(self.offDelay)
        self.node.setDriver('GV2', self.offDelay*60, True, True)


    def update(self, command = None):
        logging.info('udiYoDimmer Update Status')
        self.yoDimmer.refreshDevice()
        #self.yoDimmer.refreshSchedules()     


    commands = {
                'UPDATE': update,
                'QUERY' : update,
                'DON'   : set_switch_on,
                'DOF'   : set_switch_off,
                'DFON'   : set_switch_fon,
                'DFOF'   : set_switch_foff,                
                'SWCTRL': switchControl, 
                'DIMLVL' : set_dimmer_level,
                'ONDELAY' : setOnDelay,
                'OFFDELAY' : setOffDelay 
                }




