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
    id = 'yoschedule'

    drivers = [
            #{'driver': 'GV12', 'value': 0, 'uom': 56},
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
        model = str(deviceInfo['modelName'][:6])
        dev_type = deviceInfo['type']
        self.scheduleType = 'SEC'

        self.yoAccess = yoAccess
        self.devInfo =  deviceInfo   
        self.yoSchedule= None
        self.node_ready = False
        self.schedule_selected = None


        self.poly = polyglot
        self.poly.subscribe(self.poly.START, self.start, self.address)
        self.poly.subscribe(self.poly.STOP, self.stop)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)

        self.yoSchedule = YoLinkSchedule(self.yoAccess, self.devInfo, self.updateStatus)               
        time.sleep(2)
        self.yoSchedule.refreshSchedules()
        time.sleep(1)


        if self.yoSchedule.no_data():
            logging.debug('Schedule support_seconds not found, default to False - device likely off line')
            
            self.support_seconds = False
        else:
            self.support_seconds = self.yoSchedule.get_data('supports_seconds')
            logging.debug('Schedule support_seconds {}not found, device likely off line')
        logging.debug('Schedule support_seconds: {}'.format(self.support_seconds))
        if dev_type == 'InfraredRemoter':
            if self.support_seconds:    
                self.id = 'yoirScheduleSec'    
            else:    
                self.id = 'yoirSchedule'    
            self.scheduleType = 'Key'
            self.drivers.append({'driver': 'GV12', 'value': 99, 'uom': 25}) #outport/channel
        elif dev_type in ['Switch', 'Outlet']:
            if self.support_seconds:    
                self.id = 'yoScheduleSec'    
            else:    
                self.id = 'yoSchedule'  
            self.scheduleType = 'OnOff'

        elif dev_type in ['MultiOutlet']:
            if self.support_seconds:    
                self.id = 'yoMScheduleSec'    
            else:    
                self.id = 'yoMSchedule'  
            self.scheduleType = 'MOnOff'
            self.drivers.append({'driver': 'GV12', 'value': 99, 'uom': 25}) 


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
       
        #time.sleep(2)
        #self.yoSchedule.initNode()
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
        try:
            logging.debug('prep_schedule {} '.format(query))
            params = {}
            onH = 25
            onM = 0     
            onS = 0
            offH = 25
            offM = 0   
            offS = 0
            key = -1

            #query = command.get("query")  
            if self.scheduleType == 'MOnOff':     
                port = query.get('outport.uom25')
                if isinstance(port, str):
                    params['ch'] = int(port)-1
            elif self.scheduleType == 'Key':     
                key = query.get('outport.uom25')
                if isinstance(key, str):
                    params['key'] = int(key)-1


            schedule_selected = query.get('index.uom25')
            if isinstance(schedule_selected, str):
                schedule_selected = int(schedule_selected)  
                params['index'] = str(schedule_selected )
           
            tmp = query.get('active.uom25') 
            if isinstance(tmp, str): 
                activated = (int(tmp) == 1)
                params['isValid'] = activated 
            
            onH = query.get('onH.uom19')
            onM = query.get('onM.uom44')
            if isinstance(onH, int) and isinstance(onM, int):
                on_str = str(onH)+':'+str(onM)
                if self.support_seconds:
                    onS = query.get('onS.uom57')
                    if isinstance(onS, int):
                        on_str = on_str + ':' + str(onS)
                params['on'] = on_str

            offH = query.get('offH.uom19')
            offM = query.get('offM.uom44')  
            if isinstance(offH, int) and isinstance(offM, int):
                off_str = str(offH)+':'+str(offM)
                if self.support_seconds:
                    offS = query.get('offS.uom57')
                    if isinstance(offS, int):
                        off_str = off_str + ':' + str(offS)
                params['off'] = off_str 

            binDays = query.get('bindays.uom25')                    
            if isinstance('bindays.uom25', str):
                binDays = int(binDays)
                params['week'] = binDays

            return(schedule_selected, params)
        except Exception as e:
            logging.error('Exception in prep_schedule: {}'.format(e))
            return(None, None)  

    def activate_schedule(self, query):
        logging.info('activate_schedule {}'.format(query))       
        #query = command.get("query")

        schedule_selected = query.get('index.uom25')
        if isinstance(schedule_selected, str):  
            schedule_selected = int(schedule_selected)
        tmp = query.get('active.uom25')
        if isinstance(tmp, str):
            activated = (int(tmp)  == 1)    
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
            logging.debug('Schedule exist for the selected index')
            if self.scheduleType in ['MOnOff']:
                if 'ch' in sch_info:
                    self.my_setDriver('GV12', int(sch_info['ch']))
            elif self.scheduleType in ['Key']:
                if 'key' in sch_info:
                    self.my_setDriver('GV12', int(sch_info['key'])) 

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
            elif len(timelist) == 3 and self.support_seconds:
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
            elif len(timelist) == 3 and self.support_seconds:
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
            sch_info = self.yoSchedule.getScheduleInfo(self.schedule_selected)
            self.update_schedule_data(sch_info, self.schedule_selected)
 

    def update(self, command = None):
        logging.info('Update Status Executed')
        self.yoSchedule.refreshDevice()


    def lookup_schedule(self, command):
        logging.info('udiYoOutlet lookup_schedule {}'.format(command))

        self.schedule_selected = command.get('value')
        if isinstance(self.schedule_selected, str):
            self.schedule_selected = int(self.schedule_selected)
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