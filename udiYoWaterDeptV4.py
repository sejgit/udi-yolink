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
#import sys
import time
from yolinkWaterDeptV3 import YoLinkWaterDeptSensor



class udiYoWaterDept(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, start_done, configDoneHandler,  retrieve_cmd_state, bool2ISY, node_queue, wait_for_node_done, checkNameSync

    id = 'yowaterdept'
    
    '''
       drivers = [
            'GV0' = Level ?
            'GV1' = Low Level 
            'GV2' = High Level 
            'GV3' = Low Water Alarm 25
            'GV4' = High Water Alarm  25
            'GV5' = Detect Error Alarm 25            
            'BATLVL' = BatteryLevel 25
            'TIME' = Epoc time of data
            'ST' = Online
            ]

    ''' 
        
    drivers = [

            {'driver': 'GV0', 'value': 0, 'uom': 56},
            {'driver': 'GV1', 'value': 0, 'uom': 56}, 
            {'driver': 'GV2', 'value': 0, 'uom': 56}, 
            {'driver': 'GV3', 'value': 0, 'uom': 25},
            {'driver': 'GV4', 'value': 0, 'uom': 25},
            {'driver': 'GV5', 'value': 0, 'uom': 25},
            {'driver': 'BATLVL', 'value': 99, 'uom': 25},
            {'driver': 'ST', 'value': 0, 'uom': 56},
            {'driver': 'GV30', 'value': 99, 'uom': 25},            
            {'driver': 'GV20', 'value': 0, 'uom': 25},            
            {'driver': 'TIME', 'value': int(time.time()), 'uom': 151},

            ]


    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   
        #super(YoLinkSW, self).__init__( csName, csid, csseckey, devInfo,  self.updateStatus, )
        #  
        logging.debug('udiYoWaterDept INIT- {}'.format(deviceInfo['name']))
        self.name = name
        
        self.poly = polyglot
        self.n_queue = []  
        self.yoAccess = yoAccess
        self.devInfo =  deviceInfo
        self.yoWaterDept  = None
        self.node_ready = False
        self.configDone = False
        self.system_ready=False
        #self.temp_unit = self.yoAccess.get_temp_unit()
        #self.cmd_state = self.retrieve_cmd_state()
        #self.address = address
        #self.poly = polyglot

        #self.Parameters = Custom(polyglot, 'customparams')
        # subscribe to the events we want
        #polyglot.subscribe(polyglot.CUSTOMPARAMS, self.parameterHandler)
        #polyglot.subscribe(polyglot.POLL, self.poll)
        self.poly.subscribe(self.poly.START, self.start, self.address)
        self.poly.subscribe(self.poly.STOP, self.stop)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        self.poly.subscribe(self.poly.CONFIGDONE, self.configDoneHandler)
        self.poly.subscribe(self.poly.STARTDONE, self.start_done)
                     
        # start processing events and create add our controller node
        self.poly.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()

        self.node = self.poly.getNode(address)
        self.adr_list = []
        self.adr_list.append(address)
        self.node_ready = True


  

    def start(self):
        logging.info('Start udiYoWaterDept')
        while not self.node_ready or not self.configDone:
            time.sleep(0.5)
        self.my_setDriver('GV30', 0, True, True)
        self.yoWaterDept  = YoLinkWaterDeptSensor(self.yoAccess, self.devInfo, self.updateStatus)
        time.sleep(2)
        self.yoWaterDept.initNode()
        time.sleep(1)
        tries = 1
        while not self.yoWaterDept.check_system_online() and (tries <= 5 or self.yoWaterDept.throttled()):
            logging.info(f'Waiting for device {self.name} to come online...')
            time.sleep(2)
            tries += 1
        time.sleep(2)
        self.temp_unit = self.yoAccess.get_temp_unit()
        #self.my_setDriver('GV30', 1, True, True)
        self.system_ready=True

        
    def initNode(self):
        self.yoWaterDept.refreshSensor()

    
    def stop (self):
        logging.info('Stop udiYoWaterDept')
        self.my_setDriver('GV30', 0, True, True)
        if getattr(self, 'yoWaterDept', None):
            self.yoWaterDept.shut_down()
        #if self.node:
        #    self.poly.delNode(self.node.address)

    def checkOnline(self):
        self.yoWaterDept.refreshDevice()

    def checkDataUpdate(self):
        if self.yoWaterDept.data_updated():
            self.updateData()


    def updateData(self):
        #alarms = self.yoWaterDept.getAlarms()
        #limits = self.yoWaterDept.getLimits()
        try:
            if self.node is not None:
                while not self.node_ready or not self.system_ready or not self.configDone:
                    time.sleep(0.5)
            message_type, message_action = self.yoWaterDept.get_message_type() # if event some data may not be updated 
            unix_time = self.yoWaterDept.get_report_time('reportAt')
            self.my_setDriver('TIME', unix_time, 151)


            if self.yoWaterDept.check_system_online():
                water_dept = self.yoWaterDept.get_data('waterDepth', 'state')
                logging.debug(f"yoWaterDept : {water_dept}")
            
                self.my_setDriver('GV0', water_dept, type=message_type)
                self.my_setDriver('ST', water_dept, type=message_type)
                settings_low  = self.yoWaterDept.get_data('low', 'alarmSettings')
                settings_high  = self.yoWaterDept.get_data('high', 'alarmSettings')
                self.my_setDriver('GV1', settings_low, 56)
                self.my_setDriver('GV2', settings_high, 56)
                alarms =  self.yoWaterDept.getAlarms()
                alarm_low = self.yoWaterDept.get_data('lowAlarm', 'alarm')
                alarm_high = self.yoWaterDept.get_data('highAlarm', 'alarm')
                alarm_error = self.yoWaterDept.get_data('detectorError', 'alarm')
                self.my_setDriver('GV3', self.bool2ISY(alarm_low), type=message_type)
                self.my_setDriver('GV4', self.bool2ISY(alarm_high), type=message_type)
                self.my_setDriver('GV5', self.bool2ISY(alarm_error), type=message_type)

                self.my_setDriver('BATLVL', self.yoWaterDept.get_data('battery', 'state'), type=message_type)
                #logging.debug('Last  tamp {}'.format(int(self.yoWaterDept.lastUpdate()/60)))
                #logging.debug('date tamp {}'.format(int(self.yoWaterDept.getDataTimestamp()/60)))
                #self.my_setDriver('TIME', int(self.yoWaterDept.getDataTimestamp()/60), 44)
                self.my_setDriver('GV30', 1)
                if self.yoWaterDept.suspended:
                    self.my_setDriver('GV20', 1)
                else:
                    self.my_setDriver('GV20', 0)                    
            else:
                self.my_setDriver('GV30', 0)
                self.my_setDriver('GV20', 0)  
        except Exception as e:
                    logging.error(f'Exception updateData {e}')
                    self.my_setDriver('TIME', int(self.yoWaterDept.getDataTimestamp()/60))       
            


    def updateStatus(self, data):
        logging.debug('udiYoWaterDept - updateStatus')
        if self.yoWaterDept is not None:        
            self.yoWaterDept.updateStatus(data)
            self.updateData()

    def set_attributes(self, command):
        logging.info('udiYoWaterDept  set_attributes - {}'.format(command))
        attribs = {}
        query = command.get("query")
        highAlarm = int(query.get("waterHighAlarm.uom56"))
        lowAlarm= int(query.get("waterLowAlarm.uom56"))
        attribs['high'] = highAlarm
        attribs['low'] = lowAlarm
        self.yoWaterDept.setAttributes(attribs)
        self.my_setDriver('GV1', 98, 25)
        self.my_setDriver('GV2', 98, 25)


    def update(self, command = None):
        logging.info('WaterDept Update')
        self.yoWaterDept.refreshDevice()
       


    commands = {
                'SETATTR': set_attributes,             
                'UPDATE': update,
                }






