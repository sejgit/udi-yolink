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

from yolinkSoilSensorV2 import YoLinkSoilSensor



class udiYoSoilSensor(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, save_cmd_state, retrieve_cmd_state, node_queue, wait_for_node_done, checkNameSync

    id = 'yosoilsensor'
    
    '''
       drivers = [
            'GV0' = TempC
            'GV1' = Low Temp Alarm
            'GV2' = high Temp Alarm 
            'GV3' = Humidity
            'GV4' = Low Humidity Alarm
            'GV5' = High Humidity Alarm
            'GV6' = BatteryLevel
            'GV7' = BatteryAlarm
            'GV8' = ALARM
            'GV9' = command setting 
            'ST' = Online
            ]

    ''' 
        
    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 70},
            {'driver': 'CLITEMP', 'value': 0, 'uom': 4},
            {'driver': 'CLIHUM', 'value': 0, 'uom': 51},
            {'driver': 'GV1', 'value': 2, 'uom': 25}, 
            {'driver': 'GV2', 'value': 2, 'uom': 25},           
            {'driver': 'GV3', 'value': 2, 'uom': 25}, 
            {'driver': 'GV4', 'value': 2, 'uom': 25},
            {'driver': 'GV5', 'value': 2, 'uom': 25},
            {'driver': 'GV6', 'value': 2, 'uom': 25},             
            {'driver': 'GV7', 'value': 2, 'uom': 25},
            {'driver': 'GV8', 'value': 2, 'uom': 25},            
            {'driver': 'BATLVL', 'value': 99, 'uom': 25},

            {'driver': 'GV9', 'value': 99, 'uom': 25},
            {'driver': 'GV10', 'value': 0, 'uom': 4},
            {'driver': 'GV11', 'value': 0, 'uom': 4},
            {'driver': 'GV12', 'value': 0, 'uom': 51},
            {'driver': 'GV13', 'value': 0, 'uom': 51},
            {'driver': 'GV14', 'value': 0, 'uom': 70},
            {'driver': 'GV15', 'value': 0, 'uom': 70},
            {'driver': 'GV30', 'value': 99, 'uom': 25},            
            {'driver': 'GV20', 'value': 99, 'uom': 25},            
             {'driver': 'TIME', 'value' :int(time.time()), 'uom': 151},    
            ]


    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   
        #super(YoLinkSW, self).__init__( csName, csid, csseckey, devInfo,  self.updateStatus, )
        #  
        logging.debug('udiYoSoilSensor INIT- {}'.format(deviceInfo['name']))
        self.name = name
        self.n_queue = []  
        self.yoAccess = yoAccess
        self.devInfo =  deviceInfo
        self.yoSoilSensor  = None
        self.node_ready = False
        self.system_ready=False
        self.temp_unit = self.yoAccess.get_temp_unit()   
        if self.temp_unit == 1:
            self.id = 'yosoilsensorF'


        self.cmd_state = self.retrieve_cmd_state()
        self.meas_support = []
        model = str(self.devInfo['modelName'][:6])
        self.alarm_state = False
        self.sensordata_24_hours = {}
        #self.address = address
        #self.poly = polyglot

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
        self.node_ready = True


  

    def start(self):
        logging.info('Start udiYoSoilSensor')
        while not self.node_ready:
            time.sleep(0.5)
        self.my_setDriver('GV30', 0)
        self.yoSoilSensor  = YoLinkSoilSensor(self.yoAccess, self.devInfo, self.updateStatus)
        time.sleep(1)
        self.yoSoilSensor.initNode()
        time.sleep(1)
        time.sleep(1)
        tries = 1
        while not self.yoSoilSensor.check_system_online() and (tries <= 5 or self.yoSoilSensor.throttled()):
            logging.info(f'Waiting for device {self.name} to come online...')
            time.sleep(2)
            tries += 1
        self.temp_unit = self.yoAccess.get_temp_unit()
        #self.my_setDriver('GV30', 1)
        self.system_ready=True

    def initNode(self):
        self.yoSoilSensor.refreshSensor()

    
    def stop (self):
        logging.info('Stop udiYoSoilSensor')
        self.my_setDriver('GV30', 0)
        if getattr(self, 'yoSoilSensor', None):
            self.yoSoilSensor.shut_down()
        #if self.node:
        #    self.poly.delNode(self.node.address)

    def checkOnline(self):
        self.yoSoilSensor.refreshDevice()

    def checkDataUpdate(self):
        if self.yoSoilSensor.data_updated():
            self.updateData()


    def get_alarms_state (self):
        alarm_on = False
        alarms = self.yoSoilSensor.getAlarms()
        logging.debug(f'Alarms: {alarms}')
        if alarms:
            for a_type in alarms:
                if alarms[a_type]:
                    alarm_on = True
        return(alarm_on)


    def updateData(self):
        #alarms = self.yoSoilSensor.getAlarms()
        #limits = self.yoSoilSensor.getLimits()
        logging.info('yoSoilSensor -  updateData')
        alarm_det = False 
        if self.node is not None:
            while not self.node_ready or not self.system_ready:
                time.sleep(0.5)                
            message_type, message_action = self.yoSoilSensor.get_message_type() # if event some data may not be updated 
            unix_time = self.yoSoilSensor.get_report_time('reportAt')
            self.my_setDriver('TIME', unix_time, 151)
            if self.yoSoilSensor.check_system_online():
                conductivity = self.yoSoilSensor.get_data('conductivity', 'state')
                lowCondAlarm = self.yoSoilSensor.get_data('lowConductivity', 'alarm')
                highCondAlarm = self.yoSoilSensor.get_data('highConductivity', 'alarm')
                alarm_det = alarm_det or lowCondAlarm or highCondAlarm
                if isinstance(conductivity, (int, float)):
                    self.my_setDriver('ST', round(conductivity/1000,1),  70, type=message_type)
                else:
                    self.my_setDriver('ST', 99,  25)
                self.my_setDriver('GV1', self.yoSoilSensor.bool2Nbr(lowCondAlarm), type=message_type)
                self.my_setDriver('GV2', self.yoSoilSensor.bool2Nbr(highCondAlarm), type=message_type) 
                min_conduct = self.yoSoilSensor.get_data('min', 'conductivityLimit')
                max_conduct = self.yoSoilSensor.get_data('max', 'conductivityLimit')
                if isinstance(min_conduct, (int, float)):
                    self.my_setDriver('GV14', round(min_conduct/1000,1),  70, type=message_type)
                else:
                    self.my_setDriver('GV14', 99,  25)
                if isinstance(max_conduct, (int, float)):
                    self.my_setDriver('GV15', round(max_conduct/1000,1),  70, type=message_type)    
                else:
                    self.my_setDriver('GV15', 99,  25)
                tempC = self.yoSoilSensor.get_data('temperature', 'state')
                tempLimMin = self.yoSoilSensor.get_data('min', 'tempLimit')
                tempLimMax = self.yoSoilSensor.get_data('max', 'tempLimit')    
                lowTempAlarm = self.yoSoilSensor.get_data('lowTemp', 'alarm')
                highTempAlarm = self.yoSoilSensor.get_data('highTemp', 'alarm')     
                if isinstance(tempC, (int, float)):
                    if self.temp_unit == 0:
                        self.my_setDriver('CLITEMP', round(tempC,1),  4, type=message_type)

                        #if 'tempLimit' in limits:
                        self.my_setDriver('GV10', tempLimMin,  4, type=message_type)
                        self.my_setDriver('GV11', tempLimMax,  4, type=message_type)
                
                    elif self.temp_unit == 1:
                        self.my_setDriver('CLITEMP', round(tempC*9/5+32,1),  17, type=message_type)
                        self.my_setDriver('ST', round(tempC*9/5+32,1),  17, type=message_type)
                        if isinstance(tempLimMin, (int, float)):
                            self.my_setDriver('GV10', round(tempLimMin*9/5+32,1),  17, type=message_type)
                        if isinstance(tempLimMax, (int, float)):
                            self.my_setDriver('GV11', round(tempLimMax*9/5+32,1),  17, type=message_type) 
          
                else:
                    self.my_setDriver('CLITEMP', 99,  25)
                    self.my_setDriver('ST', 99,  25)
                    self.my_setDriver('GV10', 99, 25)
                    self.my_setDriver('GV11', 99, 25)            
                self.my_setDriver('GV3', self.yoSoilSensor.bool2Nbr(lowTempAlarm), type=message_type)
                self.my_setDriver('GV4', self.yoSoilSensor.bool2Nbr(highTempAlarm), type=message_type)

                hum = self.yoSoilSensor.get_data('humidity', 'state')
                humLimMin = self.yoSoilSensor.get_data('min', 'humidityLimit')
                humLimMax = self.yoSoilSensor.get_data('max', 'humidityLimit') 
                lowHumAlarm = self.yoSoilSensor.get_data('lowHumidity', 'alarm')
                highHumAlarm = self.yoSoilSensor.get_data('highHumidity', 'alarm')  
                alarm_det = alarm_det or lowHumAlarm or highHumAlarm

                if isinstance(hum,(int,float)):
                    self.my_setDriver('CLIHUM', hum, 51, type=message_type )
    
                    self.my_setDriver('GV12', humLimMin, 51, type=message_type)
                    self.my_setDriver('GV13', humLimMax, 51, type=message_type)

                else:   
                    self.my_setDriver('CLIHUM', 99, 25)
                    self.my_setDriver('GV12', 99, 25)
                    self.my_setDriver('GV13', 99, 25)      

                self.my_setDriver('GV5', self.yoSoilSensor.bool2Nbr(lowHumAlarm), type=message_type)
                self.my_setDriver('GV6', self.yoSoilSensor.bool2Nbr(highHumAlarm), type=message_type)




                periodAlarm = self.yoSoilSensor.get_data('period', 'alarm')
                alarm_det = alarm_det or periodAlarm
                self.my_setDriver('GV7', self.yoSoilSensor.bool2Nbr(periodAlarm), type=message_type)
                self.my_setDriver('GV8', self.yoSoilSensor.bool2Nbr(alarm_det), type=message_type)                
                bat_lvl = self.yoSoilSensor.get_data('battery')
                self.my_setDriver('BATLVL', bat_lvl, 25, type=message_type)


                if alarm_det != self.alarm_state:
                    if alarm_det and self.cmd_state in [0,1]:
                        self.node.reportCmd('DON')
                    if not alarm_det and self.cmd_state in [0,2]:  
                        self.node.reportCmd('DOF')
                    self.alarm_state = alarm_det                               
                    self.my_setDriver('GV9', self.cmd_state)

                self.my_setDriver('GV30', 1)

                if self.yoSoilSensor.suspended:
                    self.my_setDriver('GV20', 1)
                else:
                    self.my_setDriver('GV20', 0)                
            else:
                self.my_setDriver('GV30', 0)
                self.my_setDriver('GV20', 2)



    def updateStatus(self, data):
        logging.debug('udiYoSprinkler - updateStatus')
        if self.yoSoilSensor is not None:
            self.yoSoilSensor.updateStatus(data)
            self.updateData()

    def set_cmd(self, command):
        ctrl = int(command.get('value'))   
        logging.info('udiYoSprinkler  set_cmd - {}'.format(ctrl))
        self.cmd_state = ctrl
        self.my_setDriver('GV9', self.cmd_state)
        self.save_cmd_state(self.cmd_state)

    def update(self, command = None):
        logging.info('THsensor Update')
        self.yoSoilSensor.refreshDevice()
       
    commands = {
                'SETCMD': set_cmd,             
                'UPDATE': update,
                }





