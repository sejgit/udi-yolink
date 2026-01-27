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
from yolinkWaterMeterControllerV3 import YoLinkWaterMeter




class udiYoSprinkler2(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, w_unit2ISY, water_meter_unit2uom, calculate_water_volume, state2ISY, bool2ISY, state2Nbr, prep_schedule, activate_schedule, update_schedule_data, node_queue, wait_for_node_done, mask2key

    id = 'yospriklerv2'
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
            {'driver': 'ST', 'value': 0, 'uom': 25}, # Water flowing
           
            #{'driver': 'GV0', 'value': 99, 'uom': 25}, #State running 
            {'driver': 'GV1', 'value': 99, 'uom': 25}, #no Water When running 
            {'driver': 'GV2', 'value': 99, 'uom': 25}, #water mode

            {'driver': 'GV3', 'value': 99, 'uom': 25},  #running mode 
            {'driver': 'GV4', 'value': 99, 'uom': 25},  #running total mode 
            {'driver': 'GV5', 'value': 99, 'uom': 70},  #Wateruse 
            {'driver': 'GV6', 'value': 99, 'uom': 70},  # progress


            {'driver': 'GV7', 'value': 99, 'uom': 25}, #manualwatering type
            {'driver': 'GV8', 'value': 99, 'uom': 70}, #manualwatering type values                                             
            {'driver': 'GV9', 'value': 99, 'uom': 25}, #waterdelay type
            {'driver': 'GV10', 'value': 99, 'uom' : 44}, # delay valuetype
     
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
        self.onDelay = 0
        self.offDelay = 0
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
        self.yoSprinkler= udiYoSprinkler2(self.yoAccess, self.devInfo, self.updateStatus)
        self.yoSprinkler.initNode()
        while not self.yoSprinkler.online:
            logging.info('waiting for watermeter to be online')
            time.sleep(5)
        self.yoSprinkler.getMeterCount()
        self.meter_unit = self.yoSprinkler.getMeterUnit()
        #self.my_setDriver('GV30', 1)
        #self.yoSprinkler.delayTimerCallback (self.updateDelayCountdown, self.timer_update)

        self.ISYwater_unit = self.yoAccess.get_water_unit()
        #self.my_setDriver('GV4',  self.meter_unit, 25)          
        self.ISYmeter_uom = self.water_meter_unit2uom( self.ISYwater_unit)
        logging.debug(f'meter unit : { self.meter_unit} ISY unit: { self.ISYwater_unit} uom: {self.ISYmeter_uom}')
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

                
                    water_running = self.yoSprinkler.get_data('running', 'state')
                    logging.debug(f'water running : {water_running}')       
                    self.my_setDriver('ST', self.state2ISY(water_running ), type=message_type)

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
                    elif water_method in ['duration']:
                        self.my_setDriver('GV3', 1, type=message_type)
                    else:
                        self.my_setDriver('GV3', 99, type=message_type) 
                
                    method_amount = self.yoSprinkler.get_data('value', 'manualWater')
                    logging.debug(f'water manualWater value: {method_amount}')
                    if isinstance(method_amount, (int,float)):
                        self.my_setDriver('GV4', method_amount, type=message_type)
            

                    '''
                    total_meter = self.yoSprinkler.get_data('meter', 'state')
                    if isinstance(total_meter, (int,float)):
                        total_meter =round(float(self.calculate_water_volume(total_meter,  self.meter_unit,  self.ISYwater_unit)), 1)
                    logging.debug(f'total meter : {total_meter}')
                    self.my_setDriver('GV1', total_meter,  self.ISYmeter_uom, type=message_type)
    
                    daily_use = self.yoSprinkler.get_data('amount', 'dailyUsage')
                    if isinstance(daily_use, (int,float)):   
                        daily_use =round(float(self.calculate_water_volume(daily_use,  self.meter_unit,  self.ISYwater_unit)), 1)
                    logging.debug(f'daily use : {daily_use}')
                    self.my_setDriver('GV10', daily_use,  self.ISYmeter_uom, type=message_type   )
                    recent_amount = self.yoSprinkler.get_data('amount','recentUsage')
                    if isinstance(recent_amount, (int,float)):
                        recent_amount = round(float(self.calculate_water_volume(recent_amount,  self.meter_unit,  self.ISYwater_unit)), 1)
                    logging.debug(f'recent amount : {recent_amount}')
                    self.my_setDriver('GV2', recent_amount,  self.ISYmeter_uom, type=message_type)

                    recent_duration = self.yoSprinkler.get_data('duration','recentUsage')
                    logging.debug(f'recent duration : {recent_duration}')
                    self.my_setDriver('GV3', recent_duration,  44, type=message_type)   
                    '''
                    pwr_mode = self.yoSprinkler.get_data('powerMode')
                    bat_lvl =  self.yoSprinkler.get_data('battery')

                    logging.debug('udiYoWaterMeterController - getBattery: {},  {}  '.format(pwr_mode, bat_lvl))
                    if pwr_mode in ['PowerLine']:
                        self.my_setDriver('BATLVL', 98, 25)  # AC powered
                    else:
                        self.my_setDriver('BATLVL', bat_lvl, 25, type=message_type)


                    #meter_unit = self.yoSprinkler.get_data('attributes', 'meterUnit')
                    #logging.debug(f'meter unit : {meter_unit}')
                    #self.my_setDriver('GV4', meter_unit, 25)        
                    #alarms = self.yoSprinkler.getAlarms()
                    #if alarms:

                    #   , , highTemp, , lowTemp, , o
    
                    leak = self.yoSprinkler.get_data('leak', 'alarm')
                    logging.debug(f'leak : {leak}')
                    self.my_setDriver('GV5', self.state2ISY(leak), type=message_type)
                    amount_overrun = self.yoSprinkler.get_data('overrunAmount24H', 'alarm') #amountOverrun24H,amountOverrun 
                    if amount_overrun is None: # try alternate key
                        amount_overrun = self.yoSprinkler.get_data('amountOverrun', 'alarm')
                    logging.debug(f'overrunAmount24H : {amount_overrun}')     
                    self.my_setDriver('GV6', self.state2ISY(amount_overrun), type=message_type)

                    duration_overrun = self.yoSprinkler.get_data('overrunDurationOnce', 'alarm') #durationOverrun overrunDurationOnce
                    if duration_overrun is None: # try alternate key
                        duration_overrun = self.yoSprinkler.get_data('durationOverrun', 'alarm')
                    logging.debug(f'duration overrun : {duration_overrun}')     
                    self.my_setDriver('GV7', self.state2ISY( duration_overrun), type=message_type)

                    times_overrun_24h = self.yoSprinkler.get_data('overrunTimes24H', 'alarm') #overrunTimes24H
                    logging.debug(f'times overrun 24h : {times_overrun_24h}')   
                    self.my_setDriver('GV8', self.state2ISY(times_overrun_24h), type=message_type)
                    reminder = self.yoSprinkler.get_data('reminder', 'alarm') #reminder
                    logging.debug(f'reminder : {reminder}')     
                    self.my_setDriver('GV9', self.state2ISY(reminder), type=message_type)
                    if self.ValveSupported:
                        supply_type = self.yoSprinkler.get_data('supplyType')   #supplyType
                        logging.debug(f'supply type : {supply_type}')     
                        self.my_setDriver('GV10', self.w_unit2ISY(supply_type), type=message_type)
                        open_reminder = self.yoSprinkler.get_data('openReminder', 'alarm') #openReminder
                        logging.debug(f'open reminder : {open_reminder}')
                    if self.yoSprinkler.suspended:
                        self.my_setDriver('GV20', 1)
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
        action = query.get('ACTION.uom25')
        mode = query.get('MODE.uom25')
        logging.debug(f'start_stop action: {action} mode: {mode}')
        if action == 0:  # stop
            self.yoSprinkler.setValveState('close')
            self.valveState  = 0
            self.my_setDriver('GV0',self.valveState )
            #self.node.reportCmd('DOF')
        self.yoSprinkler.setValveState('open')
        self.valveState  = 1
        self.my_setDriver('GV0',self.valveState )

        #self.node.reportCmd('DON')


    def set_watermode(self, command):
        logging.info(f'set_attributes {command}')
        query = command.get("query")
        data={}
        data['attributes'] = {}
        leak_lim = None
        or_lim = None
        if 'L_LIMIT.uom69' in query:
            leak_lim = float(query.get('L_LIMIT.uom69'))
            or_lim = float(self.calculate_water_volume(or_lim, 0, self.water_unit))
        elif 'L_LIMIT.uom6' in query:
            leak_lim = float(query.get('L_LIMIT.uom6'))
            leak_lim = float(self.calculate_water_volume(leak_lim, 1, self.water_unit))
        elif 'L_LIMIT.uom8' in query:
            leak_lim = float(query.get('L_LIMIT.uom8'))
            leak_lim = float(self.calculate_water_volume(leak_lim, 2, self.water_unit))
        elif 'L_LIMIT.uom35' in query:
            leak_lim = float(query.get('L_LIMIT.uom35'))
            leak_lim = float(self.calculate_water_volume(leak_lim, 3, self.water_unit))
        if leak_lim:
            data['attributes'] ['leakLimit'] = leak_lim

        if 'L_OFF.uom25' in query:
            data['attributes'] ['autoCloseValve'] = bool(query.get('L_OFF.uom25'))

        if 'OR_LIMIT.uom69' in query:
            or_lim = float(query.get('OR_LIMIT.uom69'))
            or_lim = float(self.calculate_water_volume(or_lim, 0, self.water_unit))
        elif 'OR_LIMIT.uom6' in query:
            or_lim = float(query.get('OR_LIMIT.uom6'))
            or_lim = float(self.calculate_water_volume(or_lim, 1, self.water_unit))
        elif 'OR_LIMIT.uom8' in query:
            or_lim = float(query.get('OR_LIMIT.uom8'))
            or_lim = float(self.calculate_water_volume(or_lim, 2, self.water_unit))
        elif 'OR_LIMIT.uom35' in query:
            or_lim = float(query.get('OR_LIMIT.uom35'))   
            or_lim = float(self.calculate_water_volume(or_lim, 3, self.water_unit))
        if self.ValveSupported:    
            if or_lim:
                data['attributes'] ['overrunAmount'] = or_lim     
            if 'OR_OFF.uom25' in query:
                data['attributes'] ['overrunAmountACV'] = bool(query.get('OR_OFF.uom25')) 
            if 'ORT_LIMIT.uom44' in query:
                data['attributes'] ['overrunDuration']  = int(query.get('ORT_LIMIT.uom44'))
            if 'ORT_OFF' in query:
                data['attributes'] ['overrunDurationACV']  = bool(query.get('ORT_OFF.uom25'))

        self.yoSprinkler.setAttributes(data)


    def update(self, command = None):
        logging.info('Update Status Executed')
        self.yoSprinkler.refreshDevice()
        

    commands = {
                'UPDATE': update,
                'STARTSTOP'   : start_stop,
                'WATERMODE' : set_watermode,
                #'VALVECTRL': waterCtrlControl, 
                #'DELAYCTRL' : program_delays,
                #'OFFDELAY' : prepOffDelay 
                }




