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

from yolinkThermostatV2 import YoLinkThermostat



class udiYoThermostat(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, save_cmd_state, retrieve_cmd_state, state2Nbr, prep_schedule, activate_schedule, update_schedule_data, node_queue, wait_for_node_done, mask2key

    id = 'yothermostat'
    
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

            {'driver': 'CLITEMP', 'value': 0, 'uom': 4},
            {'driver': 'GV1', 'value': 2, 'uom': 25}, 
            {'driver': 'GV2', 'value': 2, 'uom': 25},           
            {'driver': 'CLIHUM', 'value': 0, 'uom': 51},
            {'driver': 'GV4', 'value': 2, 'uom': 25},
            {'driver': 'GV5', 'value': 2, 'uom': 25},
            {'driver': 'BATLVL', 'value': 99, 'uom': 25},
            {'driver': 'GV7', 'value': 2, 'uom': 25},
            {'driver': 'GV8', 'value': 2, 'uom': 25},
            {'driver': 'GV9', 'value': 99, 'uom': 25},
            {'driver': 'GV10', 'value': 0, 'uom': 4},
            {'driver': 'GV11', 'value': 0, 'uom': 4},
            {'driver': 'GV12', 'value': 0, 'uom': 51},
            {'driver': 'GV13', 'value': 0, 'uom': 51},
            {'driver': 'ST', 'value': 0, 'uom': 25},
            {'driver': 'GV30', 'value': 99, 'uom': 25},            
            {'driver': 'GV20', 'value': 99, 'uom': 25},            
             {'driver': 'TIME', 'value' :int(time.time()), 'uom': 151},    
            ]


    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   
        #super(YoLinkSW, self).__init__( csName, csid, csseckey, devInfo,  self.updateStatus, )
        #  
        logging.debug('udiYoThermostat INIT- {}'.format(deviceInfo['name']))
        self.n_queue = []  
        self.yoAccess = yoAccess
        self.devInfo =  deviceInfo
        self.yoTHsensor  = None
        self.node_ready = False
        self.temp_unit = self.yoAccess.get_temp_unit()   

        self.cmd_state = self.retrieve_cmd_state()
        model = str(self.devInfo['modelName'][:6])
        
        '''        if model in ['YS8017', 'YS8014', 'YS8004', 'YS8008', 'YS8003']:
            self.meas_support = ['temp']
        else:
            self.meas_support = ['temp', 'hum']
        if self.temp_unit == 1:
            if 'hum' not in self.meas_support:
                self.id = 'yotsensF'
            else:
                self.id = 'yothsensF'   
        else:
            if 'hum' not in self.meas_support:
                self.id = 'yotsens'  
        '''
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


  

    def start(self):
        logging.info('Start udiYoThermostat')
        self.my_setDriver('GV30', 0)
        self.yoTHsensor  = YoLinkThermostat(self.yoAccess, self.devInfo, self.updateStatus)
        time.sleep(1)
        self.yoTHsensor.initNode()
        time.sleep(1)
        #while not self.yoTHsensor.check_system_online():
        #    logging.info('Waiting for TH sensor to come online...')
        #    time.sleep(2)

        self.temp_unit = self.yoAccess.get_temp_unit()
        self.node_ready = True
        #self.my_setDriver('GV30', 1)

    def initNode(self):
        self.yoTHsensor.refreshSensor()

    
    def stop (self):
        logging.info('Stop udiYoThermostat')
        self.my_setDriver('GV30', 0)
        self.yoTHsensor.shut_down()
        #if self.node:
        #    self.poly.delNode(self.node.address)

    def checkOnline(self):
        self.yoTHsensor.refreshDevice()

    def checkDataUpdate(self):
        if self.yoTHsensor.data_updated():
            self.updateData()


    def get_alarms_state (self):
        alarm_on = False
        alarms = self.yoTHsensor.getAlarms()
        logging.debug(f'Alarms: {alarms}')
        if alarms:
            for a_type in alarms:
                if alarms[a_type]:
                    alarm_on = True
        return(alarm_on)


    def updateData(self):
        #alarms = self.yoTHsensor.getAlarms()
        #limits = self.yoTHsensor.getLimits()
        if self.node is not None:
            while not self.node_ready:
                time.sleep(0.5)
            logging.info('yoTHsensor -  updateData')
            alarm_det = False 

            message_type = self.yoTHsensor.get_message_type() # if event some data may not be updated 
            unix_time = self.yoTHsensor.get_report_time('reportAt')
            self.my_setDriver('TIME', unix_time, 151)
            if self.yoTHsensor.check_system_online():
                tempC = self.yoTHsensor.get_data('temperature', 'state')
                tempLimMin = self.yoTHsensor.get_data('min', 'tempLimit')
                tempLimMax = self.yoTHsensor.get_data('max', 'tempLimit')    
                lowTempAlarm = self.yoTHsensor.get_data('lowTemp', 'alarms')
                highTempAlarm = self.yoTHsensor.get_data('highTemp', 'alarms')     
                alarm_det = alarm_det or lowTempAlarm or highTempAlarm        
                hum = None
                if 'hum' in self.meas_support:
                    hum = self.yoTHsensor.get_data('humidity', 'state')
                    humLimMin = self.yoTHsensor.get_data('min', 'humidityLimit')
                    humLimMax = self.yoTHsensor.get_data('max', 'humidityLimit') 
                    lowHumAlarm = self.yoTHsensor.get_data('lowHumidity', 'alarms')
                    highHumAlarm = self.yoTHsensor.get_data('highHumidity', 'alarms')  
                    alarm_det = alarm_det or lowHumAlarm or highHumAlarm
                tempMeasMin, tempMeasMax, humMeasMin, humMeasMax = self.yoTHsensor.update_data_24_hours(unix_time, tempC, hum)
                bat_lvl = self.yoTHsensor.get_data('battery', 'state')
                bat_alarm = self.yoTHsensor.get_data('batteryLow', 'alarms')
                #tempMeas = self.yoTHsensor.get_data('temperature', 'statistics')
                #if isinstance(tempMeas, dict):
                #    tempMeasMin = tempMeas.get('min', None)
                ##    tempMeasMax = tempMeas.get('max', None)
                #else:

                #    tempMeasMin = None
                #    tempMeasMax = None
                
                if isinstance(tempC, (int, float)):
                    if self.temp_unit == 0:
                        self.my_setDriver('CLITEMP', round(tempC,1),  4, type=message_type)
                        self.my_setDriver('ST', round(tempC,1),  4)
                        #if 'tempLimit' in limits:
                        self.my_setDriver('GV10', tempLimMin,  4, type=message_type)
                        self.my_setDriver('GV11', tempLimMax,  4, type=message_type)
                        self.my_setDriver('GV14', tempMeasMin,  4, type=message_type)
                        self.my_setDriver('GV15', tempMeasMax,  4, type=message_type)                        

                    elif self.temp_unit == 1:
                        self.my_setDriver('CLITEMP', round(tempC*9/5+32,1),  17, type=message_type)
                        self.my_setDriver('ST', round(tempC*9/5+32,1),  17, type=message_type)
                        if isinstance(tempLimMin, (int, float)):
                            self.my_setDriver('GV10', round(tempLimMin*9/5+32,1),  17, type=message_type)
                        if isinstance(tempLimMax, (int, float)):
                            self.my_setDriver('GV11', round(tempLimMax*9/5+32,1),  17, type=message_type) 
                        if isinstance(tempMeasMin, (int, float)):   
                            self.my_setDriver('GV14', round(tempMeasMin*9/5+32,1),  17, type=message_type)
                        if isinstance(tempMeasMax, (int, float)):   
                            self.my_setDriver('GV15', round(tempMeasMax*9/5+32,1),  17, type=message_type)      
                else:
                    self.my_setDriver('CLITEMP', 99,  25)
                    self.my_setDriver('ST', 99,  25)
                    self.my_setDriver('GV10', 99, 25)
                    self.my_setDriver('GV11', 99, 25)
                    self.my_setDriver('GV14', 99, 25)
                    self.my_setDriver('GV15', 99, 25)
   
                
            
                self.my_setDriver('GV1', self.yoTHsensor.bool2Nbr(lowTempAlarm), type=message_type)
                self.my_setDriver('GV2', self.yoTHsensor.bool2Nbr(highTempAlarm), type=message_type)

                if 'hum' in self.meas_support:
                    if isinstance(hum,(int,float)):
                        self.my_setDriver('CLIHUM', hum, 51, type=message_type )
        
                        self.my_setDriver('GV12', humLimMin, 51, type=message_type)
                        self.my_setDriver('GV13', humLimMax, 51, type=message_type)
                        self.my_setDriver('GV16', humMeasMin, 51, type=message_type)
                        self.my_setDriver('GV17', humMeasMax, 51, type=message_type)
                    self.my_setDriver('GV4', self.yoTHsensor.bool2Nbr(lowHumAlarm), type=message_type)
                    self.my_setDriver('GV5', self.yoTHsensor.bool2Nbr(highHumAlarm), type=message_type)
                    if alarm_det or lowHumAlarm or highHumAlarm:
                        alarm_det = True
                else:
                    self.my_setDriver('CLIHUM', 98, 25)
                    self.my_setDriver('GV12', 98, 25)
                    self.my_setDriver('GV13', 98, 25)
                    self.my_setDriver('GV16', 98, 25)
                    self.my_setDriver('GV17', 98, 25)   
                    self.my_setDriver('GV4', 98, 25)
                    self.my_setDriver('GV5', 98, 25)


                self.my_setDriver('BATLVL', bat_lvl, 25, type=message_type)
                self.my_setDriver('GV7', self.yoTHsensor.bool2Nbr(bat_alarm))
                alarm_det = alarm_det or bat_alarm

                if alarm_det != self.alarm_state:
                    if alarm_det and self.cmd_state in [0,1]:
                        self.node.reportCmd('DON')
                    if not alarm_det and self.cmd_state in [0,2]:  
                        self.node.reportCmd('DOF')
                    self.alarm_state = alarm_det                


                    self.my_setDriver('GV8', self.yoTHsensor.bool2Nbr(self.alarm_state))
                    self.my_setDriver('GV9', self.cmd_state)

                self.my_setDriver('GV30', 1)

                if self.yoTHsensor.suspended:
                    self.my_setDriver('GV20', 1)
                else:
                    self.my_setDriver('GV20', 0)                
            else:
                self.my_setDriver('GV30', 0)
                self.my_setDriver('GV20', 2)



    def updateStatus(self, data):
        logging.debug('udiYoThermostat - updateStatus')
        self.yoTHsensor.updateStatus(data)
        self.updateData()

    def set_cmd(self, command):
        ctrl = int(command.get('value'))   
        logging.info('udiYoThermostat  set_cmd - {}'.format(ctrl))
        self.cmd_state = ctrl
        self.my_setDriver('GV9', self.cmd_state)
        self.save_cmd_state(self.cmd_state)

    def update(self, command = None):
        logging.info('THsensor Update')
        self.yoTHsensor.refreshDevice()
       
    commands = {
                'SETCMD': set_cmd,             
                'UPDATE': update,
                }




