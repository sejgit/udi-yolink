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

from os import truncate
#import udi_interface
#import sys
import time
from yolinkSirenV3 import YoLinkSiren


class udiYoSiren(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, node_queue, wait_for_node_done

    id = 'yosiren'
    '''
       drivers = [
            'GV0' = Siren State
            'GV1' = Alarm Duration
            'GV2' = BatteryLevel
            'ST' = Online
            ]
    '''  #Needs update 
    drivers = [
            {'driver': 'GV0', 'value': 99, 'uom': 25},
            {'driver': 'GV1', 'value': 0, 'uom': 58}, # seconds
            {'driver': 'GV2', 'value': 99, 'uom': 25},
            {'driver': 'GV3', 'value': 99, 'uom': 25},
            {'driver': 'ST', 'value': 0, 'uom': 25},
            {'driver': 'GV30', 'value': 99, 'uom': 25},
            {'driver': 'GV20', 'value': 99, 'uom': 25},
             {'driver': 'TIME', 'value' :int(time.time()), 'uom': 151},
            ]



    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   
        logging.debug('udiYoSiren INIT- {}'.format(deviceInfo['name']))
        self.n_queue = []
        self.yoAccess = yoAccess
        self.devInfo =  deviceInfo
        self.yoSiren = None
        self.node_ready = False
        self.last_state = ''
        self.timer_cleared = True
        self.timer_update = 5
        self.timer_expires = 0
        self.sirenState = 99 # needed as class c device - keep value until online again 
        model = str(deviceInfo['modelName'][:6])        
        self.soundLevelSupport = model in ['YS7103']      
        #
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


    def start(self):
        logging.info('Start - udiYoSiren')
        self.my_setDriver('GV30', 0, True, True)

        self.yoSiren = YoLinkSiren(self.yoAccess, self.devInfo, self.updateStatus)
        
        time.sleep(2)
        self.yoSiren.initNode()
        time.sleep(2)
        self.node_ready = True

    def stop (self):
        logging.info('Stop udiYoSiren')
        self.my_setDriver('GV30', 0, True, True)
        self.yoSiren.shut_down()
        #if self.node:
        #    self.poly.delNode(self.node.address)
            
    def checkOnline(self):
        #get get info even if battery operated 
        self.yoSiren.refreshDevice()    


 

    def checkDataUpdate(self):
        if self.yoSiren.data_updated():
            self.updateData()
        #if time.time() >= self.timer_expires - self.timer_update:
        #    self.node.setDriver('GV1', 0, True, False)
        #    self.node.setDriver('GV2', 0, True, False)


    def updateData(self):
        if self.node is not None:
            while not self.node_ready:
                time.sleep(0.5)
            message_type = self.yoSiren.get_message_type() # if event some data may not be updated 
            unix_time = self.yoSiren.get_report_time('reportAt')
            self.my_setDriver('TIME', unix_time, 151)
            state_list = ['normal', 'alert', 'off']
            if self.yoSiren.check_system_online():
                state =  self.yoSiren.get_data('state')
                logging.debug('Siren state {}'.format(state))
                if state in state_list:
  
                    self.my_setDriver('GV0', state_list.index(state), type=message_type)
                    self.my_setDriver('ST', state_list.index(state), type=message_type)
                else:
                    self.my_setDriver('GV0', 99)
                    self.my_setDriver('ST', 99)
                supply = self.udiYoSiren.get_data('powerSupply')
                if supply in ['battery']:
                    logging.debug(f'udiYoSiren - getBattery: {supply} ')    
                    self.node.my_setDriver('GV2', self.yoSiren.get_data('battery'), type=message_type)
                elif supply in ['ext_supply', 'usb']:
                    logging.debug('udiYoSiren - external Supply')    
                    self.my_setDriver('GV2', 98, type=message_type)
                else:
                    self.my_setDriver('GV2', 99, type=message_type)
                duration = self.yoSiren.get_data('alarmDuration')
                logging.debug('AlarmDuration : {}'.format(duration))
                self.my_setDriver('GV1', duration, type=message_type)
                if self.soundLevelSupport:
                    sound_level = self.yoSiren.get_data('soundLevel')
                    if sound_level in [1,100]:
                        sound_level = 1
                    elif sound_level in [2,104]:
                        sound_level = 2
                    elif sound_level in [3,110]:
                        sound_level = 3
                    elif sound_level in [0]:
                        sound_level = 0
                    else:
                        sound_level = 99
                else:   
                    sound_level = 98
                logging.debug('Sound Level : {}'.format(sound_level))                    
                self.my_setDriver('GV3', sound_level,  type=message_type)

                self.my_setDriver('GV30', 1)


                #logging.debug('Timer info : {} '. format(time.time() - self.timer_expires))
                if self.yoSiren.suspended:
                    self.my_setDriver('GV20', 1, True, True)
                else:
                    self.my_setDriver('GV20', 0)
            else:
                
                self.node.my_setDriver('GV30', 0)
                self.node.my_setDriver('GV20', 2)
                

    def updateStatus(self, data):
        logging.info('updateStatus - udiYoSiren')
        self.yoSiren.updateStatus(data)
        self.updateData()
    

    def sirenControl(self, command):
        logging.info('Siren Control')
        state = int(command.get('value'))
        if state == 1:
            self.yoSiren.setState('on')
            self.sirenState = 1
            self.node.setDriver('GV0',self.sirenState , True, True)
            self.node.setDriver('ST',self.sirenState , True, True)
        else:
            self.yoSiren.setState('off')
            self.sirenState  = 0
            self.node.setDriver('GV0', self.sirenState , True, True)
            self.node.setDriver('ST', self.sirenState , True, True)



    def update(self, command = None):
        logging.info('Update Status Executed')
        self.yoSiren.refreshDevice()



    commands = {
                'UPDATE': update,
                'SIRENCTRL': sirenControl, 
                }




