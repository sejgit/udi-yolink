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
from yolinkLockV3 import YoLinkLock



class udiYoLockV2(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, save_cmd_state, retrieve_cmd_state, bool2ISY, prep_schedule, activate_schedule, update_schedule_data, node_queue, wait_for_node_done, mask2key

    id = 'yolockv2'
    '''
       drivers = [
            'GV0' = LockState
            'GV1' = Battery
            'GV2' = DoorBell
            'ST' = Online
            ]
    ''' 
    drivers = [
            {'driver': 'GV0', 'value': 99, 'uom': 25},
            {'driver': 'GV1', 'value': 0, 'uom': 25}, 
            {'driver': 'GV2', 'value': 0, 'uom': 25}, 
            {'driver': 'GV3', 'value': 98, 'uom': 25},
            {'driver': 'GV4', 'value': 0, 'uom': 25}, 
            {'driver': 'GV5', 'value': 98, 'uom': 25},            
            {'driver': 'ST', 'value': 0, 'uom': 25},
            {'driver': 'GV30', 'value': 99, 'uom': 25},
            {'driver': 'GV20', 'value': 99, 'uom': 25},
             {'driver': 'TIME', 'value' :int(time.time()), 'uom': 151},            
            ]


    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   

        logging.debug('udiYoLock INIT- {}'.format(deviceInfo['name']))
        self.n_queue = []   
        
        self.yoAccess = yoAccess
        self.devInfo =  deviceInfo
        self.yoLock = None
        self.node_ready = False
        self.system_ready=False
        self.last_state = ''
        self.powerSupported = True # assume
        if deviceInfo.get('type') in ['LockV2']:
            self.isLockV2 = True
        
        self.poly = polyglot


        self.poly.subscribe(self.poly.START, self.start, self.address)
        self.poly.subscribe(self.poly.STOP, self.stop)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
             

        # start processing events and create add our controller node
        self.poly.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        self.adr_list = []
        self.adr_list.append(address)
        self.node_ready = True



    def start(self):
        logging.info('start - YoLinkLock')
        while not self.node_ready:
            time.sleep(0.5)
        self.yoLock  = YoLinkLock(self.yoAccess, self.devInfo, self.updateStatus)
        time.sleep(2)
        self.yoLock.initNode()
        tries = 1
        while not self.yoLock.check_system_online() and tries <= 5:
            logging.info('Waiting for device to come online...')
            time.sleep(2)
            tries += 1
        self.my_setDriver('GV30', 1)
        self.system_ready=True

    def stop (self):
        logging.info('Stop udiYoLock')
        self.my_setDriver('GV30', 0)
        self.yoLock.shut_down()


    def checkDataUpdate(self):
        if self.yoLock.data_updated():
            self.updateData()

    def get_alerts(self):
        type = None
        info = {}
        alert_info = self.get_data('alert')
        if isinstance(alert_info, dict):
            type = alert_info.get('type')
            info = alert_info
            del info['type']
        return type, info

    def source2ISY(self, source) -> int:
        if source in ['Password']:
            return 0
        elif source in ['Manual']:
            return
        elif source in ['Key']:
            return 2
        elif source in['AutoLock', 'Automatic']:
            return 3
        elif source in ['Fingerprint']:
            return 4
        else:
            return 99            

    def updateData(self):
        if self.node is not None:
            while not self.node_ready or not self.system_ready:
                time.sleep(0.5)
            message_type, message_action = self.yoLock.get_message_type() # if event some data may not be updated 
            unix_time = self.yoLock.get_report_time('reportAt')
            self.my_setDriver('TIME', unix_time, 151)

            if  self.yoLock.check_system_online():
                state = str(self.yoLock.get_data('lock','state'))
                logging.debug('LockV2 state: {}'.format(state))
                if state in ['lock','locked'] :
                    self.my_setDriver('GV0', 1, type=message_type)
                    self.my_setDriver('ST', 1, type=message_type)

                    if self.last_state != state:
                        self.node.reportCmd('DON')
                elif state in ['unlock', 'unlocked']: 
                    self.my_setDriver('GV0', 0, type=message_type)
                    self.my_setDriver('ST', 0, type=message_type    )
                    if self.last_state != state:
                        self.node.reportCmd('DOF')
                else:
                    self.my_setDriver('GV0', 99)
                    self.my_setDriver('ST', 99)

                self.last_state = state
                battery = self.yoLock.get_data('battery')
                self.my_setDriver('GV1', battery, type=message_type)
                #bell = self.yoLock.getDoorBellRing()
                door_state = self.yoLock.get_data('door', 'state')
                if door_state in ['closed']:
                    self.my_setDriver('GV3', 0)
                elif  door_state in ['open']:
                    self.my_setDriver('GV3', 1)
                else:
                    self.my_setDriver('GV3', 99, type=message_type)
                self.my_setDriver('GV30', 1)                
  

                alert_type, info = self.get_alerts()   
                lock_list = ['Lock','Unlock','LockFailed','UnLockFailed']             
                if alert_type is None:
                    logging.debug('No alert')
                elif alert_type in ['doorbell', 'bell', 'DoorBell']:
                    logging.debug('Doorbell rung')
                    self.my_setDriver('GV2', 1, type=message_type)
                elif alert_type in lock_list:
                    logging.debug('Lock/Unlock event')          
                    self.my_setDriver('GV4', lock_list.index(alert_type), type=message_type)
                    source = info.get('source')
                    self.my_setDriver('GV5', self.source2ISY(source), type=message_type)                
                else:
                    logging.debug('Unknown alert type: {}'.format(alert_type))
                #self.my_setDriver('GV2', self.bool2ISY(self.yoLock.getDoorBellRing()), type=message_type)

                #doorstate = self.yoLock.getDoorState()

                if self.yoLock.suspended:
                    self.my_setDriver('GV20', 1)
                else:
                    self.my_setDriver('GV20', 0)
            else:
                self.my_setDriver('GV30', 0)
                self.my_setDriver('GV20', 2)
            



    def updateStatus(self, data):
        logging.info('udiYoLock updateStatus')
        self.yoLock.updateStatus(data)
        self.updateData()



    
    def checkOnline(self):
        self.yoLock.refreshDevice()


    def set_lock(self, command = None):
        logging.info('udiYoLock set_lock')
        self.yoLock.setState('LOCK')
        self.my_setDriver('GV0',1 )
        self.my_setDriver('ST',1 )
        self.node.reportCmd('DON')

    def set_unlock(self, command = None):
        logging.info('udiYoLock set_unlock')
        self.yoLock.setState('UNLOCK')
        self.my_setDriver('GV0',0 )
        self.my_setDriver('ST',0 )
        self.node.reportCmd('DOF')

    def lockControl(self, command):
        ctrl = int(command.get('value'))
        logging.info('udiYoLock lockControl - {}'.format(ctrl))
        if ctrl == 1:
            self.yoLock.setState('LOCK')
            self.my_setDriver('GV0',1 )
            self.my_setDriver('ST',1 )
            self.node.reportCmd('DON')
        elif ctrl == 0:
            self.yoLock.setState('UNLOCK')
            self.my_setDriver('GV0',0 )
            self.my_setDriver('ST',0 )
            self.node.reportCmd('DOF')


        
    def update(self, command = None):
        logging.info('Update Status Executed')
        self.yoLock.refreshDevice()
        
 


    commands = {
                'UPDATE' : update,
                'LOCK'   : set_lock,
                'UNLOCK' : set_unlock,
                'LOCKCTRL' : lockControl, 

                }


class udiYoLock(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, save_cmd_state, retrieve_cmd_state, bool2ISY, prep_schedule, activate_schedule, update_schedule_data, node_queue, wait_for_node_done, mask2key

    id = 'yolock'
    '''
       drivers = [
            'GV0' = LockState
            'GV1' = Battery
            'GV2' = DoorBell
            'ST' = Online
            ]
    ''' 
    drivers = [
            {'driver': 'GV0', 'value': 99, 'uom': 25},
            {'driver': 'GV1', 'value': 0, 'uom': 25}, 
            #{'driver': 'GV2', 'value': 0, 'uom': 25}, 
            {'driver': 'GV3', 'value': 98, 'uom': 25},
            #{'driver': 'GV4', 'value': 0, 'uom': 25}, 
            #{'driver': 'GV5', 'value': 98, 'uom': 25},            
            {'driver': 'ST', 'value': 0, 'uom': 25},
            {'driver': 'GV30', 'value': 99, 'uom': 25},
            {'driver': 'GV20', 'value': 99, 'uom': 25},
             {'driver': 'TIME', 'value' :int(time.time()), 'uom': 151},            
            ]


    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   

        logging.debug('udiYoLock INIT- {}'.format(deviceInfo['name']))
        self.n_queue = []   
        
        self.yoAccess = yoAccess
        self.devInfo =  deviceInfo
        self.yoLock = None
        self.node_ready = False
        self.system_ready=False
        self.last_state = ''
        self.powerSupported = True # assume
        if deviceInfo.get('type') in ['LockV2']:
            self.isLockV2 = True
        
        self.poly = polyglot


        self.poly.subscribe(self.poly.START, self.start, self.address)
        self.poly.subscribe(self.poly.STOP, self.stop)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
             

        # start processing events and create add our controller node
        self.poly.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        self.adr_list = []
        self.adr_list.append(address)
        self.node_ready = True



    def start(self):
        logging.info('start - YoLinkLock')
        while not self.node_ready:
            time.sleep(0.5)
        self.yoLock  = YoLinkLock(self.yoAccess, self.devInfo, self.updateStatus)
        time.sleep(2)
        self.yoLock.initNode()
        tries = 1
        while not self.yoLock.check_system_online() and tries <= 5:
            logging.info('Waiting for device to come online...')
            time.sleep(2)
            tries += 1
        self.my_setDriver('GV30', 1)
        self.system_ready=True

    def stop (self):
        logging.info('Stop udiYoLock')
        self.my_setDriver('GV30', 0)
        self.yoLock.shut_down()


    def checkDataUpdate(self):
        if self.yoLock.data_updated():
            self.updateData()

 

    def updateData(self):
        if self.node is not None:
            while not self.node_ready or not self.system_ready:
                time.sleep(0.5)
            message_type, message_action = self.yoLock.get_message_type() # if event some data may not be updated 
            unix_time = self.yoLock.get_report_time('reportAt')
            self.my_setDriver('TIME', unix_time, 151)

            if  self.yoLock.check_system_online():
                state = str(self.yoLock.get_data('state','state'))
                logging.debug('Lock state: {}'.format(state))
                if state in ['lock','locked'] :
                    self.my_setDriver('GV0', 1, type=message_type)
                    self.my_setDriver('ST', 1, type=message_type)

                    if self.last_state != state:
                        self.node.reportCmd('DON')
                elif state in ['unlock', 'unlocked']: 
                    self.my_setDriver('GV0', 0, type=message_type)
                    self.my_setDriver('ST', 0, type=message_type    )
                    if self.last_state != state:
                        self.node.reportCmd('DOF')
                else:
                    self.my_setDriver('GV0', 99)
                    self.my_setDriver('ST', 99)

                self.last_state = state
                battery = self.yoLock.get_data('battery', 'state')
                self.my_setDriver('GV1', battery, type=message_type)
                #bell = self.yoLock.getDoorBellRing()
                door_state = self.yoLock.get_data('door', 'state')
                if door_state in ['closed']:
                    self.my_setDriver('GV3', 0)
                elif  door_state in ['open']:
                    self.my_setDriver('GV3', 1)
                else:
                    self.my_setDriver('GV3', 99, type=message_type)
                self.my_setDriver('GV30', 1)                
  


                if self.yoLock.suspended:
                    self.my_setDriver('GV20', 1)
                else:
                    self.my_setDriver('GV20', 0)
            else:
                self.my_setDriver('GV30', 0)
                self.my_setDriver('GV20', 2)
            



    def updateStatus(self, data):
        logging.info('udiYoLock updateStatus')
        self.yoLock.updateStatus(data)
        self.updateData()



    
    def checkOnline(self):
        self.yoLock.refreshDevice()


    def set_lock(self, command = None):
        logging.info('udiYoLock set_lock')
        self.yoLock.setState('LOCK')
        self.my_setDriver('GV0',1 )
        self.my_setDriver('ST',1 )

        self.node.reportCmd('DON')

    def set_unlock(self, command = None):
        logging.info('udiYoLock set_outlet_off')
        self.yoLock.setState('UNLOCK')
        self.my_setDriver('GV0',0 )
        self.my_setDriver('ST',0 )
        self.node.reportCmd('DOF')



    def lockControl(self, command):
        ctrl = int(command.get('value'))   
        logging.info('udiYoLock switchControl - {}'.format(ctrl))
        ctrl = int(command.get('value'))     
        if ctrl == 1:
            self.yoLock.setState('LOCK')
            self.my_setDriver('GV0',1 )
            self.my_setDriver('ST',1 )    
            self.node.reportCmd('DON')
        elif ctrl == 0:
            self.yoLock.setState('UNLOCK')
            self.my_setDriver('GV0',0 ) 
            self.my_setDriver('ST',0 )
            self.node.reportCmd('DOF')
      
        
        
        
    def update(self, command = None):
        logging.info('Update Status Executed')
        self.yoLock.refreshDevice()
        
 


    commands = {
                'UPDATE' : update,
                'LOCK'   : set_lock,
                'UNLOCK' : set_unlock,
                'LOCKCTRL' : lockControl,

                }



