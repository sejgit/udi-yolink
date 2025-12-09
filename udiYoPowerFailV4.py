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
from yolinkPowerFailV3 import YoLinkPowerFailSensor



class udiYoPowerFailSenor(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, save_cmd_state, retrieve_cmd_state, bool2ISY, prep_schedule, activate_schedule, update_schedule_data, node_queue, wait_for_node_done, mask2key

    id = 'yopwralarm'
    
    '''
       drivers = [
            'GV0' = Power Failure Alert
            'GV1' = Battery Level
            'GV2' = AlertState
            'GV3' = Powered
            'GV4' = Muted
                        
            'ST' = Online
            ]

    ''' 
        
    drivers = [
            {'driver': 'GV0', 'value': 99, 'uom': 25}, 
            {'driver': 'GV1', 'value': 99, 'uom': 25}, 
            {'driver': 'GV2', 'value': 99, 'uom': 25}, 
            {'driver': 'GV3', 'value': 99, 'uom': 25}, 
            {'driver': 'GV4', 'value': 99, 'uom': 25}, 
            {'driver': 'GV7', 'value': 0, 'uom': 25},      
            {'driver': 'ST', 'value': 0, 'uom': 25},
            {'driver': 'GV30', 'value': 0, 'uom': 25},
            {'driver': 'GV20', 'value': 99, 'uom': 25}, 
             {'driver': 'TIME', 'value' :int(time.time()), 'uom': 151},

            ]


    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   
        #from  udiLib import node_queue, wait_for_node_done, getValidName, getValidAddress, send_temp_to_isy, isy_value, bool2ISY
        logging.debug('udiYoPowerFailSenor INIT- {}'.format(deviceInfo['name']))
        self.adress = address
        self.yoAccess = yoAccess
        self.devInfo =  deviceInfo
        self.yoVibrationSensor  = None
        self.node_ready = False
        self.last_state = 99
        self.cmd_state = self.retrieve_cmd_state()
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
        #self.my_setDriver('GV30', 0)
        self.adr_list = []
        self.adr_list.append(address)

    def start(self):
        logging.info('start - udiYoPowerFailSenor')
        self.my_setDriver('GV30', 0)
        self.yoPowerFail  = YoLinkPowerFailSensor(self.yoAccess, self.devInfo, self.updateStatus)
        time.sleep(2)
        self.yoPowerFail.initNode()
        self.node_ready = True
        #self.my_setDriver('GV30', 1)

    
    def stop (self):
        logging.info('Stop udiYoPowerFailSenor')
        self.my_setDriver('GV30', 0)
        self.yoPowerFail.shut_down()
        #if self.node:
        #    self.poly.delNode(self.node.address)

    def checkOnline(self):
        self.yoPowerFail.refreshDevice()   
    
    def checkDataUpdate(self):
        if self.yoPowerFail.data_updated():
            self.updateData()



    def updateData(self):
        alert_state = ['normal', 'alert', 'off']
        if self.node is not None:
            message_type = self.yoPowerFail.get_last_message_type() # if event some data may not be updated 
            unix_time = self.yoPowerFail.get_report_time('reportAt')
            self.my_setDriver('TIME', unix_time, 151)
     
            if self.yoPowerFail.online:               
                #state = self.yoPowerFail.getAlertState()
                state = self.yoPowerFail.get_data('state', 'state')
                logging.debug('state GV0 : {}'.format(state))
                if state in alert_state:    
                    state_val = alert_state.index(state) 
                    self.my_setDriver('GV0', state_val, type=message_type)
                    self.my_setDriver('ST', state_val, type=message_type)
                else:
                    self.my_setDriver('GV0', 99, type=message_type)
                    self.my_setDriver('ST', 99, type=message_type)
                if state != self.last_state:
                    if state ==1 and self.cmd_state in [0,1]:
                        self.node.reportCmd('DON')
                    elif state == 0 and self.cmd_state in [0,2]:
                        self.node.reportCmd('DOF')                    
                self.my_setDriver('GV1', self.yoPowerFail.get_data('battery', 'state'))
                alert = self.yoPowerFail.get_data('alertType', 'state')
                logging.debug('AlertState GV2 : {}'.format(alert))
                self.my_setDriver('GV2', alert, type=message_type)
                powered = self.yoPowerFail.get_data('powerSupply', 'state')
                logging.debug('Powered  GV3 : {}'.format(powered))
                self.my_setDriver('GV3', self.bool2ISY(powered), type=message_type)
                muted = self.yoPowerFail.get_data('mute', 'state')
                logging.debug('Muted GV4 : {}'.format(muted))
                self.my_setDriver('GV4', self.bool2ISY(muted), type=message_type)
                self.my_setDriver('GV30', 1)
                if self.yoPowerFail.suspended:
                    self.my_setDriver('GV20', 1)
                else:
                    self.my_setDriver('GV20', 0)
            else:

                self.my_setDriver('GV30', 1)
                self.my_setDriver('GV20', 2)



    def getPowerSupplyState(self):
        logging.debug('getPowerSupplyState')




    def updateStatus(self, data):
        logging.info('updateStatus - udiYoPowerFailSenor')
        self.yoPowerFail.updateStatus(data)
        self.updateData()

    def set_cmd(self, command):
        ctrl = int(command.get('value'))   
        logging.info('udiYoPowerFailSenor  set_cmd - {}'.format(ctrl))
        self.cmd_state = ctrl
        self.my_setDriver('GV7', self.cmd_state)
        self.save_cmd_state(self.cmd_state)

        
    def update(self, command = None):
        logging.info('udiYoPowerFailSenor Update  Executed')
        self.yoPowerFail.refreshDevice()
       

    def noop(self, command = None):
        pass

    commands = {
                'SETCMD': set_cmd,
                'UPDATE': update,

                #'DON'   : noop,
                #'DOF'   : noop
                }





