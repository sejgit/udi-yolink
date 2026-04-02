#!/usr/bin/env python3
"""
Polyglot TEST v3 node server 


MIT License
"""
import time
from yolinkDoorSensorV3 import YoLinkDoorSensor

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)


class udiYoDoorSensor(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, save_cmd_state, retrieve_cmd_state, node_queue, wait_for_node_done, checkNameSync

    id = 'yodoorsens'
    
    '''
       drivers = [
            'GV0' = DoorState
            'GV1' = Batery
            'ST' = Online
            ]

    ''' 
        
    drivers = [ {'driver': 'GV0', 'value': 99, 'uom': 25}, 
            {'driver': 'GV1', 'value': 99, 'uom': 25}, 
            {'driver': 'GV2', 'value': 0, 'uom': 25},     
            {'driver': 'GV3', 'value': int(time.time()), 'uom': 151},
            {'driver': 'ST', 'value': 0, 'uom': 25},
            {'driver': 'GV30', 'value': 99, 'uom': 25},
            {'driver': 'GV20', 'value': 99, 'uom': 25}, 
            {'driver': 'TIME', 'value': int(time.time()), 'uom': 151}, ]


    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   
        #super(YoLinkSW, self).__init__( csName, csid, csseckey, devInfo,  self.updateStatus, )
        #  
        self.devInfo =  deviceInfo   
        self.yoAccess = yoAccess
        self.name = name
        self.yoDoorSensor = None
        self.node_ready = False
        self.system_ready=False
        self.last_state = 99
        self.cmd_state =  self.retrieve_cmd_state()
        logging.debug('udiYoDoorSensor INIT - {}'.format(deviceInfo['name']))
        self.n_queue = []
        


        #polyglot.subscribe(polyglot.POLL, self.poll)
        polyglot.subscribe(polyglot.START, self.start, self.address)
        polyglot.subscribe(polyglot.STOP, self.stop)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        

        polyglot.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        self.adr_list = []
        self.adr_list.append(address)        
        self.node_ready = True





    def start(self):
        logging.info('start - udiYoDoorSensor')
        while not self.node_ready:
            time.sleep(0.5)
        #self.my_setDriver('ST', 0)
        self.my_setDriver('GV30', 0)
        self.yoDoorSensor  = YoLinkDoorSensor(self.yoAccess, self.devInfo, self.updateStatus)   
        time.sleep(2)
        self.yoDoorSensor.initNode()
        time.sleep(1)
        tries = 1
        while not self.yoDoorSensor.check_system_online() and (tries <= 5 or self.yoDoorSensor.throttled()):
            logging.info(f'Waiting for device {self.name} to come online...')
            time.sleep(2)
            tries += 1

        #self.my_setDriver('ST', 1)
        #if not self.yoDoorSensor.online:
        #    logging.warning('Device {} not on-line at start'.format(self.devInfo['name']))

        #else:
        #    self.my_setDriver('ST', 1)
        self.system_ready=True

    def stop (self):
        logging.info('Stop - udiYoDoorSensor')
        #self.my_setDriver('ST', 0)
        self.my_setDriver('GV30', 0)
        if getattr(self, 'yoDoorSensor', None):
            self.yoDoorSensor.shut_down()
        #if self.node:
        #    self.poly.delNode(self.node.address)

    def doorState(self):
        state = self.yoDoorSensor.get_data('state','state')

        if isinstance(state, str) and state.lower() == 'closed':
            return(0)
        elif isinstance(state, str) and state.lower() == 'open':
            return(1)
        else:
            return(99)
    
    def checkOnline(self):
        # only gets the casched status (battery operated device)
        self.yoDoorSensor.refreshDevice()
       
    def checkDataUpdate(self):
        if self.yoDoorSensor.data_updated():
            self.updateData()



    def updateData(self):
        if self.node is not None:
            while not self.node_ready or not self.system_ready:
                time.sleep(0.5)
            message_type, message_action = self.yoDoorSensor.get_message_type() # if event some data may not be updated 
            unix_time = self.yoDoorSensor.get_report_time('reportAt')
            self.my_setDriver('TIME', unix_time, 151)

            if self.yoDoorSensor.check_system_online():
                doorstate = self.doorState()
                if doorstate == 1:
                    self.my_setDriver('GV0', 1 )
                    self.my_setDriver('ST', 1 )
                    if doorstate != self.last_state and self.cmd_state in [0,1]:
                        self.node.reportCmd('DON')
                elif doorstate == 0:
                    self.my_setDriver('GV0', 0 )
                    self.my_setDriver('ST', 0 )
                    if doorstate != self.last_state and self.cmd_state in [0,2]:
                        self.node.reportCmd('DOF')
                else:
                    self.my_setDriver('GV0', 99 )
                    self.my_setDriver('ST', 99 )
                self.last_state = doorstate
                self.my_setDriver('GV1', self.yoDoorSensor.getBattery())
                self.my_setDriver('GV2', self.cmd_state)
                #self.my_setDriver('ST', 1)
                state_change = self.yoDoorSensor.get_data('stateChangedAt', 'state')
                logging.debug('state_change : {}'.format(state_change))
                if state_change is not None:
                    self.my_setDriver('GV3', int(state_change/1000), type=message_type)
                else:
                    self.my_setDriver('GV3', 99, 25, type=message_type)


                self.my_setDriver('GV30', 1)
                if self.yoDoorSensor.suspended:
                    self.my_setDriver('GV20', 1)
                else:
                    self.my_setDriver('GV20', 0)

            else:
                #self.my_setDriver('GV0', 99)
                #self.my_setDriver('GV1', 99)
                #self.my_setDriver('GV2', self.cmd_state)
                #self.my_setDriver('ST', 0)
                self.my_setDriver('GV30', 0) 
                self.my_setDriver('GV20', 2)



    def updateStatus(self, data):
        logging.debug('updateStatus - {}'.format(self.name))
        if self.node is not None:
            while not self.node_ready or not self.system_ready:
                time.sleep(0.5)
        self.yoDoorSensor.updateStatus(data)
        #logging.debug(data)
        self.updateData()


    def set_cmd(self, command):
        ctrl = int(command.get('value'))   
        logging.info('udiYoDoorSensor  set_cmd - {}'.format(ctrl))
        self.cmd_state = ctrl
        self.my_setDriver('GV2', self.cmd_state)
        self.save_cmd_state(self.cmd_state)

    def update(self, command = None):
        logging.info('{} - Update Status Executed'.format(self.name))
        self.yoDoorSensor.refreshDevice()
       
    def noop(self, command = None):
        pass

    commands = {
                'SETCMD': set_cmd,
                'UPDATE': update,
                }






