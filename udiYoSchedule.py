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

from yolink_mqtt_classV4 import YoLinkMQTTDevice




class udiYoSchedule(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, prep_schedule, convert_timestr_to_epoch, activate_schedule, update_schedule_data, node_queue, wait_for_node_done, bool2ISY, mask2key
    id = 'yoscheduleSec'

    drivers = [
            {'driver': 'GV13', 'value': 0, 'uom': 25}, #Schedule index/no
            {'driver': 'GV14', 'value': 99, 'uom': 25}, # Active
            {'driver': 'GV15', 'value': 99, 'uom': 25}, #start Hour
            {'driver': 'GV16', 'value': 99, 'uom': 25}, #start Min
            {'driver': 'GV21', 'value': 99, 'uom': 25}, #start Sec            
            {'driver': 'GV17', 'value': 99, 'uom': 25}, #stop Hour                                              
            {'driver': 'GV18', 'value': 99, 'uom': 25}, #stop Min                                        
            {'driver': 'GV22', 'value': 99, 'uom': 25}, #stop Sec            
            ]


    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   

        logging.debug('udiYoOutletPwr INIT- {}'.format(deviceInfo['name']))
        self.n_queue = []
     
        self.yoAccess = yoAccess
        self.devInfo =  deviceInfo   
        self.yoSchedule= None
        self.node_ready = False
        self.schedule_selected = None
  
        polyglot.subscribe(polyglot.START, self.start, self.address)
        polyglot.subscribe(polyglot.STOP, self.stop)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
               

        # start processing events and create add our controller node
        polyglot.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        #self.my_setDriver('GV30', 1)
        self.adr_list = []
        self.adr_list.append(address)


    def start(self):
        logging.info('start - Schedule subnode')
        self.my_setDriver('GV30', 0)
        self.yoSchedule = YoLinkSchedule(self.yoAccess, self.devInfo, self.updateStatus)
        time.sleep(2)
        self.yoSchedule.initNode()
        time.sleep(2)
        self.yoSchedule.refreshSchedules()
        self.node_ready = True
        
    
    def stop (self):
        logging.info('Stop udiYoOutlet')
        self.my_setDriver('GV30', 0)
        self.yoSchedule.shut_down()
        #if self.node:
        #    self.poly.delNode(self.node.address)

    def checkDataUpdate(self):
        #if self.yoSchedule.data_updated():
        self.updateData()
        #if time.time() >= self.timer_expires - self.timer_update:
        #    self.my_setDriver('GV1', 0, True, False)
        #    self.my_setDriver('GV2', 0, True, False)     



    def updateData(self):
        logging.info('udiyoScheduleupdateData -  {}'.format(self.schedule_selected))
        if self.node is not None:
            message_type = self.yoSchedule.get_last_message_type()
            unix_time = self.yoSchedule.get_report_time('time')
            logging.debug(f'unix time {unix_time}')
            self.my_setDriver('TIME', unix_time, 151)
            if self.yoSchedule.online: 
                logging.debug('Outlet is online')
                #if  self.yoSchedule.online:
                self.my_setDriver('GV30',1)
                #state = str(self.yoSchedule.getState()).upper()
                state = str(self.yoSchedule.get_data('state'))
                logging.debug('Outlet Online State : {} '. format(state))
                logging.debug('Outlet State : {} '. format(state))
                if state in ['on', 'open']:
                    self.my_setDriver('GV0',1, type=message_type)
                    self.my_setDriver('ST',1, type=message_type)
                    state =  'open'
                    #if self.last_state != state:
                    #    self.node.reportCmd('DON')  
                elif state in [ 'off', 'closed']:
                    self.my_setDriver('GV0', 0, type=message_type)
                    self.my_setDriver('ST', 0, type=message_type)
                    state = 'closed'
                    #if self.last_state != state:
                    #    self.node.reportCmd('DOF')  
                #else:
                #    self.my_setDriver('GV0', 99)
                self.last_state = state           
                      

                #tmp =  self.yoSchedule.getEnergy()
                #logging.debug('Power/Energy info : {} '. format(tmp))
                
                if self.powerSupported: 
                    powerW = self.yoSchedule.get_data('power')
                    if isinstance(powerW, (int, float)):
                        powerW = round(powerW/10,3) # reports 1/10W
                        self.my_setDriver('GV3', powerW, 73, type=message_type)

                    energyWh = self.yoSchedule.get_data('watt')  
                    if isinstance(energyWh, (int, float)):            
                        energyWh = round(energyWh/10,3) # reports 1/10Wh                    
                    self.my_setDriver('GV4', energyWh, 119, type=message_type)

                    self.my_setDriver('GV5', self.bool2ISY(self.yoSchedule.get_data('overload', 'alertType')), type=message_type)
                    self.my_setDriver('GV6', self.bool2ISY(self.yoSchedule.get_data('highLoad', 'alertType')), type=message_type)   
                    self.my_setDriver('GV7', self.bool2ISY(self.yoSchedule.get_data('lowLoad', 'alertType')), type=message_type)
                    self.my_setDriver('GV8', self.bool2ISY(self.yoSchedule.get_data('highTemperature', 'alertType')), type=message_type)
                    
                #logging.debug('Timer info : {} '. format(time.time() - self.timer_expires))
                if time.time() >= self.timer_expires - self.timer_update and self.timer_expires != 0:
                    self.my_setDriver('GV1', 0)
                    self.my_setDriver('GV2', 0)
                if self.yoSchedule.suspended:
                    self.my_setDriver('GV20', 1)
                else:
                    self.my_setDriver('GV20', 0)
            else:

                self.my_setDriver('GV30',0)
                self.my_setDriver('GV20', 2)
  

        sch_info = self.yoSchedule.getScheduleInfo(self.schedule_selected)
        self.update_schedule_data(sch_info, self.schedule_selected)
 

    def update(self, command = None):
        logging.info('Update Status Executed')
        self.yoSchedule.refreshDevice()


    def lookup_schedule(self, command):
        logging.info('udiYoOutlet lookup_schedule {}'.format(command))
        self.schedule_selected = int(command.get('value'))
        self.yoSchedule.refreshSchedules()

    def define_schedule(self, command):
        logging.info('udiYoSwitch define_schedule {}'.format(command))
        query = command.get("query")
        self.schedule_selected, params = self.prep_schedule(query)
        self.yoSchedule.setSchedule(self.schedule_selected, params)


    def control_schedule(self, command):
        logging.info('udiYoSwitch control_schedule {}'.format(command))       
        query = command.get("query")
        self.activated, self.schedule_selected = self.activate_schedule(query)
        self.yoSchedule.activateSchedule(self.schedule_selected, self.activated)
        









    commands = {
                'UPDATE'        : update,
                'LOOKUPSCH'    : lookup_schedule,
                'DEFINESCH'    : define_schedule,
                'CTRLSCH'      : control_schedule,
                }




class YoLinkSchedule(YoLinkMQTTDevice):
    def __init__(yolink, yoAccess,  deviceInfo, callback):
        super().__init__(yoAccess,  deviceInfo, callback)

