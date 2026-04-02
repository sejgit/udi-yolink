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
from udiYoSchedule import udiYoSchedule




class udiYoWaterMeterController(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, w_unit2ISY, water_meter_unit2uom, calculate_water_volume, state2ISY, bool2ISY, update_schedule_data, node_queue, wait_for_node_done, checkNameSync

    id = 'yowatermeterCtrl'
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
            {'driver': 'GV0', 'value': 99, 'uom': 25},
            {'driver': 'GV1', 'value': 99, 'uom': 25}, #water use total
            {'driver': 'GV10', 'value': 99, 'uom': 25}, #water use daily             
            {'driver': 'GV2', 'value': 99, 'uom': 25},  #wateruse recent
            {'driver': 'GV3', 'value': 99, 'uom': 44},  #Wateruse duration
            {'driver': 'BATLVL', 'value': 99, 'uom': 25},
            {'driver': 'CLITEMP', 'value': 99, 'uom': 25},            
            #{'driver': 'GV4', 'value': 99, 'uom': 25}, #Measure Unit
            {'driver': 'GV5', 'value': 99, 'uom': 25}, #alarm
            {'driver': 'GV6', 'value': 99, 'uom': 25}, 
            {'driver': 'GV7', 'value': 99, 'uom': 25}, 
            {'driver': 'GV8', 'value': 99, 'uom': 25},                                              
            {'driver': 'GV9', 'value': 99, 'uom': 25}, 

            {'driver': 'GV11', 'value': 99, 'uom' : 25}, # 
            {'driver': 'GV12', 'value': 99, 'uom' : 25}, #  leak limit
            {'driver': 'GV13', 'value': 99, 'uom' : 25}, # auto shutoffg
            {'driver': 'GV14', 'value': 99, 'uom' : 25}, # Water flowing
            #{'driver': 'GV15', 'value': 99, 'uom' : 25}, # auto shutoffg
            #{'driver': 'GV16', 'value': 99, 'uom' : 44}, # Water flowing
            #{'driver': 'GV17', 'value': 99, 'uom' : 25}, # auto shutoffg
            {'driver': 'GV22', 'value': 99, 'uom': 25}, #LeakLimit
            {'driver': 'GV23', 'value': 99, 'uom': 25}, #Overrtun limit
            {'driver': 'GV24', 'value': 99, 'uom': 25}, #Overrun Time
    
            {'driver': 'GV26', 'value': 99, 'uom': 25}, #LEakAC
            {'driver': 'GV27', 'value': 99, 'uom': 25}, #Overrun AC
            {'driver': 'GV28', 'value': 99, 'uom': 25}, #OverrunTIme AC        
            {'driver': 'GV20', 'value': 99, 'uom': 25},
            {'driver': 'GV30', 'value': 99, 'uom': 25},
            {'driver': 'TIME', 'value' :0, 'uom': 151},                
            ]



    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   
        logging.debug('udiYoWaterMeterController INIT- {}'.format(deviceInfo['name']))
        self.name = name
        self.n_queue = []
        self.yoAccess = yoAccess
        self.ValveSupported = True
        self.temp_unit = self.yoAccess.get_temp_unit()
        self.water_unit = self.yoAccess.get_water_unit()  
        model = str(deviceInfo['modelName'][:6])  
        if model in ['YS5007']:
            if self.temp_unit == 1 and self.water_unit == 0:
                self.id = 'yowatermeterCtrlF'
            else:
                self.id = 'yowatermeterCtrl'
            self.ValveSupported = False
            if self.commands.get('DON') is not None:
                del self.commands['DON']
            if self.commands.get('DOF') is not None:
                del self.commands['DOF']
        else: #YS5018 or YS5008 YS5009
            if self.temp_unit == 1 and self.water_unit == 0:
                self.id = 'yowatermeterCtrlF'
            else:   
                self.id = 'yowatermeterCtrl'

        if model in ['YS5029','YS5009']:
            self.scheduleSupport = False
        else:
            self.scheduleSupport = True

        if self.water_unit not in [0,3]:
            logging.error('Only Litere and Gallon supported for now')

        self.devInfo =  deviceInfo
        self.yoWaterCtrl= None
        self.schedule_valve = None
        self.schedule_leak = None
        self.node_ready = False
        self.system_ready=False
        self.last_state = ''
        self.timer_cleared = True
        self.timer_update = 5
        self.timer_expires = 0
        self.onDelay = 0
        self.offDelay = 0
        self.valveState = 99 # needed as class c device - keep value until online again 
        self.ISYmeter_uom = None
        self.ISYwater_unit = None
        #polyglot.subscribe(polyglot.POLL, self.poll)
        polyglot.subscribe(polyglot.START, self.start, self.address)
        polyglot.subscribe(polyglot.STOP, self.stop)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        #known_meters = ['YS5007','YS5018', 'YS5008', 'YS5009', ]
        #if self.yoWaterCtrl.devInfo['model'] in known_meters:
        #    logging.debug(f'Known water meter model {self.yoWaterCtrl.devInfo["model"]}')   
        #    if self.yoWaterCtrl.devInfo['model'] in ['YS5029']: # dual channel model  -  no temps and not 


        # start processing events and create add our controller node
        polyglot.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        self.adr_list = []
        self.adr_list.append(address)
        self.node_ready = True
        logging.debug('udiYoWaterMeterController INIT done- {}'.format(self.commands))


    def start(self):
        logging.info('Start - udiYoWaterMeterController')
        while not self.node_ready:
            time.sleep(0.5)
        self.my_setDriver('GV30', 1)
        self.my_setDriver('GV20', 0)
        self.yoWaterCtrl= YoLinkWaterMeter(self.yoAccess, self.devInfo, self.updateStatus)
        time.sleep(2)
        self.yoWaterCtrl.initDevice()
        time.sleep(1)
        tries = 1
        while not self.yoWaterCtrl.check_system_online() and (tries <= 5 or self.yoWaterCtrl.throttled()):
            logging.info(f'Waiting for device {self.name} to come online...')
            time.sleep(2)
            tries += 1
        self.yoWaterCtrl.getMeterCount()
        self.meter_unit = self.yoWaterCtrl.getMeterUnit()
        #self.my_setDriver('GV30', 1)
        #self.yoWaterCtrl.delayTimerCallback (self.updateDelayCountdown, self.timer_update)

        self.ISYwater_unit = self.yoAccess.get_water_unit()
        #self.my_setDriver('GV4',  self.meter_unit, 25)          
        self.ISYmeter_uom = self.water_meter_unit2uom( self.ISYwater_unit)
        logging.debug(f'meter unit : { self.meter_unit} ISY unit: { self.ISYwater_unit} uom: {self.ISYmeter_uom}')
        if self.scheduleSupport:
        # Create valve schedule child node
            sch_address_valve = self.address[4:14] + '_VSC'
            sch_address_valve = self.poly.getValidAddress(sch_address_valve)
            self.schedule_valve = udiYoSchedule(self.poly, self.address, sch_address_valve, 'Valve Schedules', self.yoAccess, self.devInfo, schedule_type='valve')
            self.adr_list.append(sch_address_valve)
            
            # Create leak schedule child node
            sch_address_leak = self.address[4:14] + '_LSC'
            sch_address_leak = self.poly.getValidAddress(sch_address_leak)
            self.schedule_leak = udiYoSchedule(self.poly, self.address, sch_address_leak, 'Leak Schedules', self.yoAccess, self.devInfo, schedule_type='leak')
            self.adr_list.append(sch_address_leak)        
            time.sleep(2)
            # deferred: refreshSchedules() will be invoked after startup to avoid API bursts

        # Prime schedule data for both child schedule nodes.
            
        #self.updateData()
        self.system_ready=True

    def stop (self):
        logging.info('Stop udiYoWaterMeterController')
        self.my_setDriver('GV30', 0)
        if getattr(self, 'yoWaterCtrl', None):
            self.yoWaterCtrl.shut_down()
        #if self.node:
        #    self.poly.delNode(self.node.address)
            
    def checkOnline(self):
        #get get info even if battery operated 
        self.yoWaterCtrl.refreshDevice()    

    def checkDataUpdate(self):
        if self.yoWaterCtrl.data_updated():
            #self.yoWaterCtrl.refreshDevice() 
            self.updateData()
        #if time.time() >= self.timer_expires - self.timer_update:
        #    self.my_setDriver('GV1', 0)
        #    self.my_setDriver('GV2', 0)

    
    def unit2uom(self) -> int:
        logging.debug(f'unit2uom {self.yoWaterCtrl.uom}')
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
                while not self.node_ready or not self.system_ready:
                    time.sleep(0.5)
                message_type, message_action = self.yoWaterCtrl.get_message_type()
                unix_time = self.yoWaterCtrl.get_report_time('time')
                self.my_setDriver('TIME', unix_time, 151)

                if message_type and 'Schedules' in str(message_type):
                    # Route valve schedules to valve node
                    if 'Valve' in str(message_type) and self.schedule_valve is not None:
                        self.schedule_valve.update_schedule_data(source_device=self.yoWaterCtrl)
                    # Route leak schedules to leak node
                    elif 'Leak' in str(message_type) and self.schedule_leak is not None:
                        self.schedule_leak.update_schedule_data(source_device=self.yoWaterCtrl)
                    return

                if self.yoWaterCtrl.check_system_online():
                    self.my_setDriver('GV30', 1)
                    if self.yoWaterCtrl.emptyData():
                        logging.debug('Empty data received - skip updateData')
                        self.my_setDriver('GV20', 6)
                        return
                    if self.ISYmeter_uom is None:
                        logging.debug(f'meter unit : { self.meter_unit}')
                        #self.my_setDriver('GV4',  self.meter_unit, 25)          
                        self.ISYmeter_uom = self.water_meter_unit2uom( self.meter_unit)
                    if self.ValveSupported:
                        state = self.yoWaterCtrl.get_data( 'valve', 'state')
                        logging.debug(f'valve state: {state}')                    
                        self.my_setDriver('GV0', self.state2ISY(state))
                        if state != None:
                            if state.upper() == 'OPEN':
                                self.valveState = 1
                                #self.my_setDriver('GV0', self.valveState)
                                if self.last_state != state:
                                    self.node.reportCmd('DON')
                            elif state.upper() == 'CLOSED':
                                self.valveState = 0
                                #self.my_setDriver('GV0', self.valveState)
                                if self.last_state != state:
                                    self.node.reportCmd('DOF')
                            #elif state.upper() == 'UNKNOWN':
                            #self.my_setDriver('GV0', 99)                        
                            self.last_state = state
                    

                    #meter  = self.yoWaterCtrl.getMeterReading()
                    #logging.debug(f'meter: {meter}')
                    #if meter != None:
                        #if 'water_runing' in meter:
                        #    self.my_setDriver('ST', meter['water_runing'])
                    water_flowing = self.yoWaterCtrl.get_data('waterFlowing', 'state')
                    logging.debug(f'water flowing : {water_flowing}')       
                    self.my_setDriver('ST', self.state2ISY(water_flowing ), type=message_type)

                    total_meter = self.yoWaterCtrl.get_data('meter', 'state')
                    if isinstance(total_meter, (int,float)):
                        total_meter =round(float(self.calculate_water_volume(total_meter,  self.meter_unit,  self.ISYwater_unit)), 1)
                    logging.debug(f'total meter : {total_meter}')
                    self.my_setDriver('GV1', total_meter,  self.ISYmeter_uom, type=message_type)
    
                    daily_use = self.yoWaterCtrl.get_data('amount', 'dailyUsage')
                    if isinstance(daily_use, (int,float)):   
                        daily_use =round(float(self.calculate_water_volume(daily_use,  self.meter_unit,  self.ISYwater_unit)), 1)
                    logging.debug(f'daily use : {daily_use}')
                    self.my_setDriver('GV10', daily_use,  self.ISYmeter_uom, type=message_type   )
                    recent_amount = self.yoWaterCtrl.get_data('amount','recentUsage')
                    if isinstance(recent_amount, (int,float)):
                        recent_amount = round(float(self.calculate_water_volume(recent_amount,  self.meter_unit,  self.ISYwater_unit)), 1)
                    logging.debug(f'recent amount : {recent_amount}')
                    self.my_setDriver('GV2', recent_amount,  self.ISYmeter_uom, type=message_type)

                    recent_duration = self.yoWaterCtrl.get_data('duration','recentUsage')
                    logging.debug(f'recent duration : {recent_duration}')
                    self.my_setDriver('GV3', recent_duration,  44, type=message_type)   

                    pwr_mode = self.yoWaterCtrl.get_data('powerMode')
                    bat_lvl =  self.yoWaterCtrl.get_data('battery')

                    logging.debug('udiYoWaterMeterController - getBattery: {},  {}  '.format(pwr_mode, bat_lvl))
                    if pwr_mode in ['PowerLine']:
                        self.my_setDriver('BATLVL', 98, 25)  # AC powered
                    else:
                        self.my_setDriver('BATLVL', bat_lvl, 25, type=message_type)
                        
                    water_temp =  self.yoWaterCtrl.get_data('waterTemperature', 'state')
                    logging.debug(f'water temperature : {water_temp}')
                    #NEEDS TO BE FIXED 
                    self.my_setDriver('CLITEMP', water_temp,  4, type=message_type)  
                    
                    #meter_unit = self.yoWaterCtrl.get_data('attributes', 'meterUnit')
                    #logging.debug(f'meter unit : {meter_unit}')
                    #self.my_setDriver('GV4', meter_unit, 25)        
                    #alarms = self.yoWaterCtrl.getAlarms()
                    #if alarms:

                    #   , , highTemp, , lowTemp, , o
    
                    leak = self.yoWaterCtrl.get_data('leak', 'alarm')
                    logging.debug(f'leak : {leak}')
                    self.my_setDriver('GV5', self.state2ISY(leak), type=message_type)
                    amount_overrun = self.yoWaterCtrl.get_data('overrunAmount24H', 'alarm') #amountOverrun24H,amountOverrun 
                    if amount_overrun is None: # try alternate key
                        amount_overrun = self.yoWaterCtrl.get_data('amountOverrun', 'alarm')
                    logging.debug(f'overrunAmount24H : {amount_overrun}')     
                    self.my_setDriver('GV6', self.state2ISY(amount_overrun), type=message_type)

                    duration_overrun = self.yoWaterCtrl.get_data('overrunDurationOnce', 'alarm') #durationOverrun overrunDurationOnce
                    if duration_overrun is None: # try alternate key
                        duration_overrun = self.yoWaterCtrl.get_data('durationOverrun', 'alarm')
                    logging.debug(f'duration overrun : {duration_overrun}')     
                    self.my_setDriver('GV7', self.state2ISY( duration_overrun), type=message_type)

                    times_overrun_24h = self.yoWaterCtrl.get_data('overrunTimes24H', 'alarm') #overrunTimes24H
                    logging.debug(f'times overrun 24h : {times_overrun_24h}')   
                    self.my_setDriver('GV8', self.state2ISY(times_overrun_24h), type=message_type)
                    reminder = self.yoWaterCtrl.get_data('reminder', 'alarm') #reminder
                    logging.debug(f'reminder : {reminder}')     
                    self.my_setDriver('GV9', self.state2ISY(reminder), type=message_type)
                    if self.ValveSupported:
                        supply_type = self.yoWaterCtrl.get_data('supplyType')   #supplyType
                        logging.debug(f'supply type : {supply_type}')     
                        self.my_setDriver('GV10', self.w_unit2ISY(supply_type), type=message_type)
                        open_reminder = self.yoWaterCtrl.get_data('openReminder', 'alarm') #openReminder
                        logging.debug(f'open reminder : {open_reminder}')
                        self.my_setDriver('GV11', self.state2ISY(open_reminder), type=message_type)

                        valve_error = self.yoWaterCtrl.get_data('valveError', 'alarm')   #valveError
                        logging.debug(f'valve error : {valve_error}')   
                        self.my_setDriver('GV12', self.state2ISY(valve_error), type=message_type)   

                    high_T_error = self.yoWaterCtrl.get_data('highTemp', 'alarm')   #valveError
                    logging.debug(f'high temp error : {high_T_error}')
                    self.my_setDriver('GV13', self.state2ISY(high_T_error), type=message_type)    
                    low_T_error = self.yoWaterCtrl.get_data('lowTemp', 'alarm')   #valveError
                    logging.debug(f'low temp error : {low_T_error}')
                    self.my_setDriver('GV14', self.state2ISY(low_T_error), type=message_type)

                    overrun24 = self.yoWaterCtrl.get_data('overrunAmount24H', 'attributes')
                    if overrun24 is not None:
                        overrun24= round(float(self.calculate_water_volume(overrun24,  self.meter_unit,  self.ISYwater_unit)), 1)
                    logging.debug(f'Overrun24  limit : {overrun24}')
                    self.my_setDriver('GV22', overrun24, self.ISYmeter_uom, type=message_type)
                    nbroverrun = self.yoWaterCtrl.get_data('overrunTimes24H', 'attributes')
                    #if nbroverrun is not None:
                    #    overrun_amount = round(float(self.calculate_water_volume(overrun_amount,  self.meter_unit,  self.ISYwater_unit)), 1)                          
                    logging.debug(f'overrun times limit : {nbroverrun}')                    
                    self.my_setDriver('GV23', nbroverrun, 70, type=message_type)
                    overrun_duration = self.yoWaterCtrl.get_data('overrunDuration', 'attributes')
                    if overrun_duration is None:
                        overrun_duration = self.yoWaterCtrl.get_data('overrunDurationOnce', 'attributes')
                    logging.debug(f'overrun duration limit : {overrun_duration}')
                    self.my_setDriver('GV24', overrun_duration, 44, type=message_type)
                    if self.ValveSupported:
                        leak_ac = self.yoWaterCtrl.get_data('leakDetection', 'autoCloseValve')
                        logging.debug(f'leak ACV : {leak_ac}')
                        self.my_setDriver('GV25', self.bool2ISY(leak_ac), type=message_type)
                        overrun_ac = self.yoWaterCtrl.get_data('overrunAmount24H', 'autoCloseValve')
                        logging.debug(f'overrun amount24 ACV : {overrun_ac}')
                        self.my_setDriver('GV26', self.bool2ISY(overrun_ac), type=message_type)
                        overrun_time_ac = self.yoWaterCtrl.get_data('overrunDurationOnce', 'autoCloseValve')
                        logging.debug(f'overrun duration ACV : {overrun_time_ac}')
                        self.my_setDriver('GV27', self.bool2ISY(overrun_time_ac), type=message_type)
                        overrun_time_ac = self.yoWaterCtrl.get_data('overrunTimes24H', 'autoCloseValve')
                        logging.debug(f'overrun times ACV : {overrun_time_ac}')
                        self.my_setDriver('GV28', self.bool2ISY(overrun_time_ac), type=message_type)

                    if self.yoWaterCtrl.suspended:
                        self.my_setDriver('GV20', 1)
                    else:
                        self.my_setDriver('GV20', 0)
                else:
                    self.my_setDriver('GV30', 0)
                    self.my_setDriver('GV20', 2)
                
        except KeyError as e:
            logging.error(f'EXCEPTION - {e}')
            
    def updateStatus(self, data):
        logging.info('updateStatus - udiYoWaterMeterController')
        if self.node is not None:
            while not self.node_ready or not self.system_ready:
                time.sleep(0.5)
        self.yoWaterCtrl.updateStatus(data)
        self.updateData()


    def set_open(self, command = None):
        logging.info('udiYoWaterMeterController - set_open')
        self.yoWaterCtrl.setValveState('open')
        self.valveState  = 1
        self.my_setDriver('GV0',self.valveState )

        #self.node.reportCmd('DON')

    def set_close(self, command = None):
        logging.info('udiYoWaterMeterController - set_close')
        self.yoWaterCtrl.setValveState('closed')
        self.valveState  = 0
        self.my_setDriver('GV0',self.valveState )
        #self.node.reportCmd('DOF')


    def prepOnDelay(self, command ):
        self.onDelay =int(command.get('value'))
        logging.info('prepOnDelay {}'.format(self.onDelay))
        #self.yoWaterCtrl.setOnDelay(delay)
        #self.my_setDriver('GV1', delay*60)
        #self.my_setDriver('GV0',self.valveState)

    def prepOffDelay(self, command):
        logging.info('setOnDelay Executed')
        self.offDelay =int(command.get('value'))
        logging.info('setOnDelay Executed {}'.format(self.offDelay))

        #self.yoWaterCtrl.setOffDelay(delay)
        #self.my_setDriver('GV2', delay*60, True, True)
        #self.my_setDriver('GV0',self.valveState  , True, True)

    def set_attributes(self, command):
        logging.info(f'set_attributes {command}')
        query = command.get("query")
        data={}
        data['attributes'] = {}
        leak_lim = None
        or_lim = None
        if 'LLIMIT.uom69' in query:
            leak_lim = float(query.get('LLIMIT.uom69'))
            or_lim = float(self.calculate_water_volume(or_lim, 0, self.water_unit))
        elif 'LLIMIT.uom6' in query:
            leak_lim = float(query.get('LLIMIT.uom6'))
            leak_lim = float(self.calculate_water_volume(leak_lim, 1, self.water_unit))
        elif 'LLIMIT.uom8' in query:
            leak_lim = float(query.get('LLIMIT.uom8'))
            leak_lim = float(self.calculate_water_volume(leak_lim, 2, self.water_unit))
        elif 'LLIMIT.uom35' in query:
            leak_lim = float(query.get('LLIMIT.uom35'))
            leak_lim = float(self.calculate_water_volume(leak_lim, 3, self.water_unit))
        if leak_lim:
            data['attributes'] ['leakLimit'] = leak_lim

        if 'LOFF.uom25' in query:
            data['attributes'] ['autoCloseValve'] = bool(query.get('LOFF.uom25'))

        if 'ORLIMIT.uom69' in query:
            or_lim = float(query.get('ORLIMIT.uom69'))
            or_lim = float(self.calculate_water_volume(or_lim, 0, self.water_unit))
        elif 'ORLIMIT.uom6' in query:
            or_lim = float(query.get('ORLIMIT.uom6'))
            or_lim = float(self.calculate_water_volume(or_lim, 1, self.water_unit))
        elif 'ORLIMIT.uom8' in query:
            or_lim = float(query.get('ORLIMIT.uom8'))
            or_lim = float(self.calculate_water_volume(or_lim, 2, self.water_unit))
        elif 'ORLIMIT.uom35' in query:
            or_lim = float(query.get('ORLIMIT.uom35'))   
            or_lim = float(self.calculate_water_volume(or_lim, 3, self.water_unit))
        if self.ValveSupported:    
            if or_lim:
                data['attributes'] ['overrunAmount'] = or_lim     
            if 'OROFF.uom25' in query:
                data['attributes'] ['overrunAmountACV'] = bool(query.get('OROFF.uom25')) 
            if 'ORTLIMIT.uom44' in query:
                data['attributes'] ['overrunDuration']  = int(query.get('ORTLIMIT.uom44'))
            if 'ORTOFF' in query:
                data['attributes'] ['overrunDurationACV']  = bool(query.get('ORTOFF.uom25'))

        self.yoWaterCtrl.setAttributes(data)


    def update(self, command = None):
        logging.info('Update Status Executed')
        self.yoWaterCtrl.refreshDevice()
        time.sleep(2)
        # Keep both schedule nodes synchronized on explicit UPDATE.
        if self.scheduleSupport:
            self.yoWaterCtrl.refreshSchedules()
        
    def program_delays(self, command):
        logging.info('udiYoOutlet program_delays {}'.format(command))
        query = command.get("query")
        self.onDelay = int(query.get("ondelay.uom44"))
        self.offDelay = int(query.get("offdelay.uom44"))
        self.my_setDriver('GV1', self.onDelay * 60)
        self.my_setDriver('GV2', self.offDelay * 60 )
        self.yoWaterCtrl.setDelayList([{'on':self.onDelay, 'off':self.offDelay}]) 

    commands = {
                'UPDATE': update,
                'DON'   : set_open,
                'DOF'   : set_close,
                'SETATTRIB' : set_attributes,
                #'VALVECTRL': waterCtrlControl, 
                #'DELAYCTRL' : program_delays,
                #'OFFDELAY' : prepOffDelay 
                }





