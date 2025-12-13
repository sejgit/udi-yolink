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
            {'driver': 'GV19', 'value': 0, 'uom': 25}, #days         
            ]


    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   

        logging.debug('udiYoSchedule INIT- {}'.format(deviceInfo['name']))
        self.n_queue = []
     
        self.yoAccess = yoAccess
        self.devInfo =  deviceInfo   
        self.yoSchedule= None
        self.node_ready = False
        self.schedule_selected = None
  
        self.poly = polyglot
        self.poly.subscribe(self.poly.START, self.start, self.address)
        self.poly.subscribe(self.poly.STOP, self.stop)
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
        #time.sleep(2)
        #self.yoSchedule.initNode()
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

    def updateStatus(self, deviceInfo):
        logging.info('Schedule updateStatus called')
        self.updateData()   

    def prep_schedule(self, query):
        logging.debug('prep_schedule {} '.format(query))
        params = {}
        onH = 25
        onM = 0     
        onS = 0
        offH = 25
        offM = 0   
        offS = 0
        include_sec = False
        #query = command.get("query")
        if 'port.uom25' in query:
            port = int(query.get('port.uom25'))-1
            params['ch'] = port
        schedule_selected = int(query.get('index.uom25'))
        tmp = int(query.get('active.uom25'))
        activated = (tmp == 1)
        if 'onH.uom19' in query:
            onH = int(query.get('onH.uom19'))
        if 'onM.uom44' in query:    
            onM = int(query.get('onM.uom44'))
        if 'offH.uom19' in query:
            offH = int(query.get('offH.uom19'))
        if 'offM.uom44' in query:    
            offM = int(query.get('offM.uom44'))  
        if 'onS.' in query:
            include_sec = True
            if 'onS.uom57' in query:            
                onS = int(query.get('onS.uom57'))
            else:
                onS = 0
        if 'offS.' in query:            
            include_sec = True  
            if 'offS.uom57' in query:            
                offS = int(query.get('onS.uom57'))
            else:
                offS = 0
            
        binDays = int(query.get('bindays.uom25'))

        
        params['index'] = str(schedule_selected )
        params['isValid'] = activated 
        params['on'] = str(onH)+':'+str(onM)
        params['off'] = str(offH)+':'+str(offM)
        if include_sec:
            params['on'] = params['on'] + ':' + str(onS)
            params['off'] =  params['off'] + ':' + str(offS)

        params['week'] = binDays
        #self.yolink.setSchedule(self.schedule_selected, params)
        return(schedule_selected, params)

    def activate_schedule(self, query):
        logging.info('activate_schedule {}'.format(query))       
        #query = command.get("query")
        schedule_selected = int(query.get('index.uom25'))
        tmp = int(query.get('active.uom25'))
        activated = (tmp == 1)
        #self.yolink.activateSchedule(schedule_selected, activated)
        return(activated, schedule_selected)

    def check_name_in_drivers(self,  name):
        logging.debug('check_name_in_drivers: {}'.format(name))
        found = False
        for drv in enumerate(self.node.drivers):
            logging.debug('check_name_in_drivers: {}'.format(drv))
            if drv['driver'] == name:
                found = True
        return(found)


    def update_schedule_data(self, sch_info, selected_schedule):
        logging.info('update_schedule_data {}'.format(sch_info)) 

        def check_name_in_drivers( name):
            found = False
            for indx, drv in enumerate(self.node.drivers):
                if drv['driver'] == name:
                    found = True
                    return(found)
            return(found)
        if sch_info:
            if 'ch' in sch_info:
                self.my_setDriver('GV12', int(sch_info['ch']))

            self.my_setDriver('GV13', selected_schedule)
            if sch_info['isValid']:
                self.my_setDriver('GV14', 1)
            else:
                self.my_setDriver('GV14', 0)
            timestr = sch_info['on']
            timelist =  timestr.split(':')
            if len(timelist) == 2:
                hour = int(timelist[0])
                minute = int(timelist[1])
                if hour == 25:
                    self.my_setDriver('GV15', 98, 25)
                    self.my_setDriver('GV16', 98, 25)
                else:
                    self.my_setDriver('GV15', int(hour),19)
                    self.my_setDriver('GV16', int(minute), 44)
            elif len(timelist) == 3:
                hour = int(timelist[0])
                minute = int(timelist[1])
                second = int(timelist[2])
                if hour == 25:
                    self.my_setDriver('GV15', 98, 25)
                    self.my_setDriver('GV16', 98, 25)
                    self.my_setDriver('GV21', 98, 25)
                else:
                    self.my_setDriver('GV15', hour, 19)
                    self.my_setDriver('GV16', minute, 44)
                    self.my_setDriver('GV21', second, 57)

            timestr = sch_info['off']
            logging.debug('timestr : {}'.format(timestr))
            timelist =  timestr.split(':')
            if len(timelist) == 2:
                hour = int(timelist[0])
                minute = int(timelist[1])
                if hour == 25:
                    self.my_setDriver('GV17', 98, 25)
                    self.my_setDriver('GV18', 98, 25)
                else:
                    self.my_setDriver('GV17', int(hour), 19)
                    self.my_setDriver('GV18', int(minute), 44)
            elif len(timelist) == 3:
                hour = int(timelist[0])
                minute = int(timelist[1])
                second = int(timelist[2])     
                if hour == 25:
                    self.my_setDriver('GV17', 98, 25)
                    self.my_setDriver('GV18', 98, 25)
                    self.my_setDriver('GV22', 98, 25)
                else:
                    self.my_setDriver('GV17', hour, 19)
                    self.my_setDriver('GV18', minute, 44)
                    self.my_setDriver('GV22', second, 57)
            self.my_setDriver('GV19',  int(sch_info['week']))

        else:
            logging.debug('No schdule exist for the selected index')
            if check_name_in_drivers('GV12'):
                self.my_setDriver('GV12', 99, 25)
            self.my_setDriver('GV13', selected_schedule) 
            self.my_setDriver('GV14', 99)
            self.my_setDriver('GV15', 99, 25)
            self.my_setDriver('GV16', 99, 25)
            self.my_setDriver('GV17', 99, 25)
            self.my_setDriver('GV18', 99, 25)
            self.my_setDriver('GV19', 0)
            if check_name_in_drivers('GV10'):
                self.my_setDriver('GV10', 99, 25)
                self.my_setDriver('GV11', 99, 25)




    def updateData(self):
        logging.info('udiyoScheduleupdateData -  {}'.format(self.schedule_selected))
        if self.node is not None:
            logging.debug('Schedule updateData called')
            '''
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
                '''
  

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

        yolink.methodList = [ 'getSchedules', 'setSchedules' ]
        yolink.eventList = ['StatusChange', 'Report', 'getState']
        yolink.stateList = ['open', 'closed', 'on', 'off']
        yolink.ManipulatorName = 'OutletEvent'
        yolink.eventTime = 'Time'
        yolink.type = deviceInfo['type']