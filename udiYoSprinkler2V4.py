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
from yolinkSprinklerV2 import YoLinkSprinkler




class udiYoSprinkler2(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, w_unit2ISY, water_meter_unit2uom, calculate_water_volume, state2ISY, bool2ISY, state2Nbr, prep_schedule, activate_schedule, update_schedule_data, node_queue, wait_for_node_done, mask2key

    id = 'yosprinklerv2'
    '''
       drivers = [
            'GV0' = Manipulator State
            'GV1' = Meter count
            'GV2' = OnDelay
            'GV3' = OffDelay
            'BATLVL' = BatteryLevel
            'GV4-9' = alarms
            'GV10' = Supply type
            'ST' = GV0 
            ]
    ''' 
    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 70}, # Water flow
           
            {'driver': 'GV0', 'value': 99, 'uom': 25}, #Water running 
            {'driver': 'GV1', 'value': 99, 'uom': 25}, #no Water When running 
            {'driver': 'GV2', 'value': 99, 'uom': 25}, #water mode

            {'driver': 'GV3', 'value': 99, 'uom': 25},  #running mode 
            {'driver': 'GV4', 'value': 99, 'uom': 25},  #running total mode 
            {'driver': 'GV5', 'value': 99, 'uom': 70},  #Wateruse 
            {'driver': 'GV6', 'value': 99, 'uom': 70},  # progress


            {'driver': 'GV7', 'value': 99, 'uom': 25}, #manualwatering type
            {'driver': 'GV8', 'value': 99, 'uom': 70}, #manualwatering type values                                             
            {'driver': 'GV9', 'value': 99, 'uom': 25}, #waterdelay type
            {'driver': 'GV10', 'value': 99, 'uom': 70}, #waterdelay type values

            {'driver': 'GV12', 'value': 99, 'uom' : 44}, # delay valuetype
     
            {'driver': 'GV20', 'value': 99, 'uom': 25},
            {'driver': 'GV30', 'value': 99, 'uom': 25},
            {'driver': 'BATLVL', 'value': 99, 'uom': 25},
            {'driver': 'TIME', 'value' :0, 'uom': 151},                
            ]



    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   
        logging.debug('udiYoWaterMeterController INIT- {}'.format(deviceInfo['name']))
        self.n_queue = []
        self.yoAccess = yoAccess
        self.ValveSupported = True
        self.temp_unit = self.yoAccess.get_temp_unit()
        self.water_unit = self.yoAccess.get_water_unit()  
        model = str(deviceInfo['modelName'][:6])  
    
        if self.water_unit not in [0,3]:
            logging.error('Only Liter and Gallon supported for now')

        self.devInfo =  deviceInfo
        self.yoSprinkler= None
        self.node_ready = False
        self.last_state = ''
        self.timer_cleared = True
        self.timer_update = 5
        self.timer_expires = 0
        self.mode = ''
        
        self.step_factor = 1
        self.ISYmeter_uom = None
        self.ISYwater_unit = None
        self.meter_unit = None

        self.valveState = 99 # needed as class c device - keep value until online again 
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
        logging.debug('udiYoSprinkler2 INIT done- {}'.format(self.commands))


    def start(self):
        logging.info('Start - udiYoSprinkler2')
        self.my_setDriver('GV30', 1)
        self.my_setDriver('GV20', 0)
        self.yoSprinkler= YoLinkSprinkler(self.yoAccess, self.devInfo, self.updateStatus)
        self.yoSprinkler.initNode()
        while not self.yoSprinkler.online:
            logging.info('waiting for watermeter to be online')
            time.sleep(5)
      
        self.meter_unit = self.yoSprinkler.get_data('meterUnit', 'attributes')
        self.step_factor = self.yoSprinkler.get_data('meterStepFactor', 'attributes')
        #self.my_setDriver('GV30', 1)
        #self.yoSprinkler.delayTimerCallback (self.updateDelayCountdown, self.timer_update)

        self.ISYwater_unit = self.yoAccess.get_water_unit()
        #self.my_setDriver('GV4',  self.meter_unit, 25)          
        self.ISYmeter_uom = self.water_meter_unit2uom( self.ISYwater_unit)
        logging.debug(f'meter unit : { self.meter_unit} ISY unit: { self.ISYwater_unit} uom: {self.ISYmeter_uom} meterFactor: {self.step_factor}')
        self.node_ready = True
        self.updateData()

    def stop (self):
        logging.info('Stop udiYoSprinkler2')
        self.my_setDriver('GV30', 0)
        self.yoSprinkler.shut_down()
        #if self.node:
        #    self.poly.delNode(self.node.address)
            
    def checkOnline(self):
        #get get info even if battery operated 
        self.yoSprinkler.refreshDevice()    

    def checkDataUpdate(self):
        if self.yoSprinkler.data_updated():
            #self.yoSprinkler.refreshDevice() 
            self.updateData()
        #if time.time() >= self.timer_expires - self.timer_update:
        #    self.my_setDriver('GV1', 0)
        #    self.my_setDriver('GV2', 0)

    
    def unit2uom(self) -> int:
        logging.debug(f'unit2uom {self.yoSprinkler.uom}')
        isy_uom = None
        if self.water_unit == 0:
            isy_uom = 69 # gallon
        if self.water_unit== 1:
            isy_uom = 6 #ft^3
        if self.water_unit == 2:
            isy_uom = 8 #m^3
        if self.water_unit == 3:
            isy_uom = 35 # liter          
        logging.debug(f'unit2uom {isy_uom}')             
        return(isy_uom)
    
    def updateData(self):
        try:
            if self.node is not None:
                message_type = self.yoSprinkler.get_last_message_type()
                unix_time = self.yoSprinkler.get_report_time('time')
                self.my_setDriver('TIME', unix_time, 151)
                if self.yoSprinkler.online:
                    self.my_setDriver('GV30', 1)
                    if self.yoSprinkler.emptyData():
                        logging.debug('Empty data received - skip updateData')
                        self.my_setDriver('GV20', 6)
                        return
                    if self.ISYmeter_uom is None:
                        logging.debug(f'meter unit : { self.meter_unit}')
                        #self.my_setDriver('GV4',  self.meter_unit, 25)          
                        self.ISYmeter_uom = self.water_meter_unit2uom( self.meter_unit)


                    water_amount = self.yoSprinkler.get_data('waterFlowing')
                    logging.debug(f'water manualWater value: {water_amount}')
                    if isinstance(water_amount, (int,float)):

                        water_amount = round(float(self.calculate_water_volume(water_amount/self.step_factor,  self.meter_unit,  self.ISYwater_unit)), 1)
                        self.my_setDriver('GV4', water_amount, type=message_type)
                
                    water_running = self.yoSprinkler.get_data('running', 'state')
                    logging.debug(f'water running : {water_running}')       
                    self.my_setDriver('GV0', self.state2ISY(water_running ), type=message_type)

                    water_running = self.yoSprinkler.get_data('noWaterWhenRunning', 'state')
                    logging.debug(f'water noWaterWhenRunning : {water_running}')       
                    self.my_setDriver('GV1', self.state2ISY(water_running ), type=message_type)


                    sprinkler_mode = self.yoSprinkler.get_data('waterMode')
                    logging.debug(f'water Mode: {sprinkler_mode}')       
                    if sprinkler_mode in ['manual']:
                        self.my_setDriver('GV2', 0, type=message_type)
                    elif sprinkler_mode in ['schedule']:
                        self.my_setDriver('GV2', 1, type=message_type)
                    else:
                        self.my_setDriver('GV2', 99, type=message_type)


                    water_method = self.yoSprinkler.get_data('type', 'manualWater')
                    logging.debug(f'water manualWater: {water_method}')       
                    if water_method in ['amount']:
                        self.my_setDriver('GV3', 0, type=message_type) 
                        self.mode = 'amount'
                    elif water_method in ['duration']:
                        self.my_setDriver('GV3', 1, type=message_type)
                        self.mode = 'duration'
                    else:
                        self.my_setDriver('GV3', 99, type=message_type) 
                
                    method_amount = self.yoSprinkler.get_data('value', 'manualWater')
                    logging.debug(f'water manualWater value: {method_amount}')
                    if isinstance(method_amount, (int,float)):
                        if self.mode == 'amount':
                            method_amount = round(float(self.calculate_water_volume(method_amount/self.step_factor,  self.meter_unit,  self.ISYwater_unit)), 1)
                            self.my_setDriver('GV4', method_amount, type=message_type, Unit=self.ISYmeter_uom)
                        else:
                            self.my_setDriver('GV4', method_amount, type=message_type, Unit=44)

                    sprinkler_mode = self.yoSprinkler.get_data('mode', 'running')
                    logging.debug(f'water Mode: {sprinkler_mode}')       
                    if sprinkler_mode in ['manual']:
                        self.my_setDriver('GV7', 0, type=message_type)
                    elif sprinkler_mode in ['schedule']:
                        self.my_setDriver('GV7', 1, type=message_type)
                    else:
                        self.my_setDriver('GV7', 99, type=message_type)

                    water_method = self.yoSprinkler.get_data('type', 'total')
                    logging.debug(f'water total: {water_method}')
                    if water_method in ['amount']:
                        self.my_setDriver('GV8', 0, type=message_type)  
                    elif water_method in ['duration']:
                        self.my_setDriver('GV8', 1, type=message_type)
                    else:
                        self.my_setDriver('GV8', 99, type=message_type) 
                    method_amount = self.yoSprinkler.get_data('value', 'total')
                    logging.debug(f'water total value: {method_amount}')
                    if isinstance(method_amount, (int,float)):
                        if water_method == 'amount':
                            method_amount = round(float(self.calculate_water_volume(method_amount/self.step_factor,  self.meter_unit,  self.ISYwater_unit)), 1)
                            self.my_setDriver('GV9', method_amount, type=message_type, Unit=self.ISYmeter_uom)
                        else:
                            self.my_setDriver('GV9', method_amount, type=message_type, Unit=44)
                    
                    method_amount = self.yoSprinkler.get_data('progress', 'running')
                    logging.debug(f'water progress: {method_amount}')
                    if isinstance(method_amount, (int,float)):
                        if water_method == 'amount':
                            method_amount = round(float(self.calculate_water_volume(method_amount/self.step_factor,  self.meter_unit,  self.ISYwater_unit)), 1)
                            self.my_setDriver('GV10', method_amount, type=message_type, Unit=self.ISYmeter_uom)
                        else:
                            self.my_setDriver('GV10', method_amount, type=message_type, Unit=44)

                    water_delay = self.yoSprinkler.get_data('duration', 'waterDelay')
                    logging.debug(f'water delay value: {water_delay}')
                    if isinstance(water_delay, (int,float)):
                        self.my_setDriver('GV12', water_delay, type=message_type)

   
                    pwr_mode = self.yoSprinkler.get_data('powerMode')
                    bat_lvl =  self.yoSprinkler.get_data('battery')

                    logging.debug('udiYoWaterMeterController - getBattery: {},  {}  '.format(pwr_mode, bat_lvl))
                    if pwr_mode in ['PowerLine']:
                        self.my_setDriver('BATLVL', 98, 25, type=message_type)  # AC powered
                    else:
                        self.my_setDriver('BATLVL', bat_lvl, 25, type=message_type)
    
                
                    if self.yoSprinkler.suspended:
                        self.my_setDriver('GV20', 1, type=message_type)
                    else:
                        self.my_setDriver('GV20', 0)
                else:
                    self.my_setDriver('GV30', 0)
                    self.my_setDriver('GV20', 2)
                
        except KeyError as e:
            logging.error(f'EXCEPTION - {e}')
            
    def updateStatus(self, data):
        logging.info('updateStatus - udiYoSprinkler2')
        self.yoSprinkler.updateStatus(data)
        self.updateData()


    def start_stop(self, command):
        logging.info('udiYoSprinkler2 - set_open')
        query = command.get("query")
        action = query.get('w_startstop.uom25')
        data={}
        data['params'] = {}
        logging.debug(f'start_stop action: {action}')
        if action in [ 0, 1]:  # stop
            data['params']['running'] = action == 1

        
        self.yoSprinkler.setDevice(data)


        #self.node.reportCmd('DON')


    def set_watermode(self, command):
        logging.info(f'set_attributes {command}')

        data={}
        data['params'] = {}
        query = command.get("query")
        if 'w_mode.uom25' in query:
            mode = int (query.get('w_mode.uom25'))
            if mode == 0:
                data['params']['waterMode'] = 'manual'
            elif mode == 1:
                data['params']['waterMode'] = 'schedule'    
        self.yoSprinkler.setDevice(data)

    def set_attributes(self, command):
        logging.info(f'set_attributes {command}')
        query = command.get("query")
        data={}
        data['params'] = {}
        leak_lim = None
        or_lim = None
        if 'w_method.uom25' in query:
            method = int (query.get('w_method.uom25'))
            if method == 0:
                self.mode = 'amount'
                data['params'] ['manualWater']['type'] = 'amount'
            elif method == 1:
                self.mode = 'duration'
                data['params'] ['manualWater']['type'] = 'duration'
            #self.my_setDriver('GV8', method)


        if 'w_amount.uom70' in query:
            amount = float (query.get('w_amount.uom70'))
            self.my_setDriver('GV9', amount)
            if self.mode == 'amount':
                if self.ISYmeter_unit == 0:#gallon
                    amount = amount / 0.264172
                amount = amount * self.step_factor
            data['params'] ['manualWater']['value'] = int(amount) 
           
        self.yoSprinkler.setAttributes(data)


    def update(self, command = None):
        logging.info('Update Status Executed')
        self.yoSprinkler.refreshDevice()
        



    def set_delay(self, command):
        logging.info(f'set_delay {command}')
        query = command.get("query")
        delay_time = int(query.get('w_del_time.uom44'))
        self.yoSprinkler.setDelayTime(delay_time)   

    commands = {
                'UPDATE': update,
                'STARTSTOP'   : start_stop,
                'WATERMODE' : set_watermode,
                'W_ATTRIB' : set_attributes,
                'W_DELAY' : set_delay,

                }




