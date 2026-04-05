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
import threading
#import udi_interface
#import sys
import time
from yolinkWaterMeterControllerV3 import YoLinkWaterMeter




class udiYoWaterMeterOnly(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, water_meter_unit2uom, calculate_water_volume, bool2ISY, node_queue, wait_for_node_done, checkNameSync

    id = 'yowatermeterOnly'
    '''
       drivers = [
            'GV0' = Manipulator State
            'GV1' = Meter count
            'GV2' = OnDelay
            'GV3' = OffDelay
            'BATLVL' = BatteryLevel
            'GV4-9' = alarms
            'GV10' = Supply type
            'ST' = Online
            ]
    ''' 
    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 25},
            {'driver': 'GV30', 'value': 99, 'uom': 25},  # Water flowing
            #{'driver': 'GV0', 'value': 99, 'uom': 25},
            {'driver': 'GV1', 'value': 0, 'uom': 69}, #water use total
            {'driver': 'GV10', 'value': 99, 'uom': 25}, #water use daily             
            {'driver': 'GV2', 'value': 0, 'uom': 69},  #wateruse recent
            {'driver': 'GV3', 'value': 0, 'uom': 44},  #Wateruse duration
            #{'driver': 'GV4', 'value': 99, 'uom': 25}, #alarm
            {'driver': 'GV5', 'value': 99, 'uom': 25}, 
            {'driver': 'GV6', 'value': 99, 'uom': 25}, 
            {'driver': 'GV7', 'value': 99, 'uom': 25}, 
            #{'driver': 'GV8', 'value': 99, 'uom': 25},                                              
            {'driver': 'GV9', 'value': 99, 'uom': 25}, 
            {'driver': 'BATLVL', 'value': 99, 'uom': 25},
            {'driver': 'CLITEMP', 'value': 99, 'uom': 25},
            {'driver': 'GV11', 'value': 99, 'uom' : 25}, # Unit
            {'driver': 'GV12', 'value': 99, 'uom' : 6}, #  leak limit
            {'driver': 'GV13', 'value': 99, 'uom' : 25}, # auto shutoffg
            {'driver': 'GV14', 'value': 99, 'uom' : 6}, # Water flowing
            #{'driver': 'GV15', 'value': 99, 'uom' : 25}, # auto shutoffg
            {'driver': 'GV16', 'value': 99, 'uom' : 44}, # Water flowing
            #{'driver': 'GV17', 'value': 99, 'uom' : 25}, # auto shutoffg
            {'driver': 'GV20', 'value': 0, 'uom': 25},
            {'driver': 'TIME', 'value' :0, 'uom': 151},                
            ]



    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   
        logging.debug('udiYoWaterMeterController INIT- {}'.format(deviceInfo['name']))
        self.name = name
        self.n_queue = []
        self.yoAccess = yoAccess
        self.temp_unit = self.yoAccess.get_temp_unit()
        if self.temp_unit == 1:
            self.id = 'yowatermeterOnlyF'

        self.water_unit = self.yoAccess.get_water_unit()              
        if self.water_unit == 0:
            self.id = 'yowatermeterOnlyF'    
        elif self.water_unit == 3:
            self.id = 'yowatermeterOnly'   
        else:
            logging.error('Only Litere and Gallon supported for now')

        self.devInfo =  deviceInfo
        self.yoWaterCtrl= None
        self.node_ready = False
        self.configDone = False
        self.system_ready=False
        self._update_lock = threading.Lock()
        self.last_state = ''
        self.timer_cleared = True
        self.timer_update = 5
        self.timer_expires = 0
        self.onDelay = 0
        self.offDelay = 0
        self.ISYmeter_uom = None
        self.ISYwater_unit = None
        self.valveState = 99 # needed as class c device - keep value until online again 
        #polyglot.subscribe(polyglot.POLL, self.poll)
        polyglot.subscribe(polyglot.START, self.start, self.address)
        polyglot.subscribe(polyglot.STOP, self.stop)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        self.poly.subscribe(self.poly.CONFIGDONE, self.configDoneHandler)

        # start processing events and create add our controller node
        polyglot.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        self.adr_list = []
        self.adr_list.append(address)
        self.node_ready = True



    def configDoneHandler(self):
        logging.info(f'configDoneHandler called  - {self.name}')
        self.configDone = True

    def start(self):
        logging.info('Start - udiYoWaterMeterController')
        while not self.node_ready and not self.configDone:
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
        self.meter_unit = self.yoWaterCtrl.getMeterUnit()
        #self.my_setDriver('GV30', 1)
        #self.yoWaterCtrl.delayTimerCallback (self.updateDelayCountdown, self.timer_update)

        self.ISYwater_unit = self.yoAccess.get_water_unit()
        #self.my_setDriver('GV4',  self.meter_unit, 25)          
        self.ISYmeter_uom = self.water_meter_unit2uom( self.ISYwater_unit)
        logging.debug(f'meter unit : { self.meter_unit} ISY unit: { self.ISYwater_unit} uom: {self.ISYmeter_uom}')


        time.sleep(2)
        #self.my_setDriver('ST', 1)
        #self.yoWaterCtrl.delayTimerCallback (self.updateDelayCountdown, self.timer_update)
        self.yoWaterCtrl.getMeterCount()
        self.meter_unit = self.yoWaterCtrl.getMeterUnit()
        #self.my_setDriver('GV30', 1)
        #self.yoWaterCtrl.delayTimerCallback (self.updateDelayCountdown, self.timer_update)

        self.ISYwater_unit = self.yoAccess.get_water_unit()
        #self.my_setDriver('GV4', self.yoWaterCtrl.meter_unit, 25)          
        self.meter_ISYuom = self.water_meter_unit2uom(self.ISYwater_unit)
        logging.debug(f'meter unit : {self.yoWaterCtrl.meter_unit} ISY unit: {self.ISYwater_unit} uom: {self.meter_ISYuom}')
        self.system_ready=True
        #self.updateData()

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


    def updateData(self):
        try:
            if self.node is not None:
                while not self.node_ready or not self.system_ready:
                    time.sleep(0.5)
                message_type, message_action = self.yoWaterCtrl.get_message_type() # if event some data may not be updated 
                unix_time = self.yoWaterCtrl.get_report_time('reportAt')
                self.my_setDriver('TIME', unix_time, 151)
                if self.yoWaterCtrl.check_system_online():
                    self.my_setDriver('GV30', 1)
                    if self.ISYmeter_uom is None:
                        logging.debug(f'meter unit : { self.meter_unit}')
                        #self.my_setDriver('GV4',  self.meter_unit, 25)          
                        self.ISYmeter_uom = self.water_meter_unit2uom( self.meter_unit)

                    #meter  = self.yoWaterCtrl.getMeterReading()
                    #logging.debug(f'meter: {meter}')
                    #meter != None:
   
                    self.my_setDriver('ST', self.bool2ISY(self.yoWaterCtrl.get_data('waterFlowing', 'state')), type=message_type)
                    #meter_total = self.yoWaterCtrl.get_data('meter', 'state')
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


                    pwr_mode, bat_lvl =  self.yoWaterCtrl.getBattery()  
                    logging.debug('udiYoWaterMeterController - getBattery: {},  {}  '.format(pwr_mode, bat_lvl))
                    if pwr_mode == 'PowerLine':
                        self.my_setDriver('BATLVL', 98, 25)
                    else:
                        self.my_setDriver('BATLVL', bat_lvl, 25)
                    self.my_setDriver('CLITEMP', self.yoWaterCtrl.getWaterTemperature())
                    
                    alarms = self.yoWaterCtrl.getAlarms()
                    if alarms:
                        #if 'openReminder' in alarms:
                        #    self.my_setDriver('GV4', self.bool2ISY(alarms['openReminder']))
                        
                        if 'leak' in alarms:
                            self.my_setDriver('GV5', self.bool2ISY(alarms['leak']))
        
                        if 'amountOverrun' in alarms:
                            self.my_setDriver('GV6', self.bool2ISY(alarms['amountOverrun']))

                        if 'durationOverrun' in alarms:
                            self.my_setDriver('GV7', self.bool2ISY(alarms['durationOverrun']))
        
                        #if 'valveError' in alarms:
                        #    self.my_setDriver('GV8', self.bool2ISY(alarms['valveError']))

                        if 'reminder' in alarms:
                            self.my_setDriver('GV9', self.bool2ISY(alarms['reminder']))

                    attributes = self.yoWaterCtrl.getAttributes()
                    if attributes:
                        if 'meterUnit' in attributes:
                            self.my_setDriver('GV11', attributes['meterUnit'], 25)                    
                        if 'leakLimit' in attributes:
                            self.my_setDriver('GV12', attributes['leakLimit'],  self.meter_ISYuom )
                        #if 'autoCloseValve' in attributes:
                        #    self.my_setDriver('GV13', self.bool2ISY(attributes['autoCloseValve']), 25)
                        #if 'overrunAmountACV' in attributes:
                        #    self.my_setDriver('GV15', self.bool2ISY(attributes['overrunAmountACV']), 25)
                        #if 'overrunDurationACV' in attributes:
                        #    self.my_setDriver('GV17', self.bool2ISY(attributes['overrunDurationACV']), 25)
                        if 'overrunAmount' in attributes:
                            self.my_setDriver('GV14', attributes['overrunAmount'], self.meter_ISYuom )
                        if 'overrunDuration' in attributes:
                            self.my_setDriver('GV16', attributes['overrunDuration'], 44)


                    if self.yoWaterCtrl.suspended:
                        self.my_setDriver('GV20', 1)
                    else:
                        self.my_setDriver('GV20', 0)

                else:

                    self.my_setDriver('GV20', 2)
                
        except KeyError as e:
            logging.error(f'EXCEPTION - {e}')

    def updateStatus(self, data):
        logging.info('updateStatus - udiYoWaterMeterController')
        if self.yoWaterCtrl is not None:        
            with self._update_lock:
                self.yoWaterCtrl.updateStatus(data)
                self.updateData()

    '''
    def updateDelayCountdown( self, timeRemaining):

        logging.debug('udiYoWaterMeterController updateDelayCountDown:  delays {}'.format(timeRemaining))
        max_delay = 0
        for delayInfo in range(0, len(timeRemaining)):
            if 'ch' in timeRemaining[delayInfo]:
                if timeRemaining[delayInfo]['ch'] == 1:
                    if 'on' in timeRemaining[delayInfo]:
                        self.my_setDriver('GV2', timeRemaining[delayInfo]['on'])
                        if max_delay < timeRemaining[delayInfo]['on']:
                            max_delay = timeRemaining[delayInfo]['on']
                    if 'off' in timeRemaining[delayInfo]:
                        self.my_setDriver('GV3', timeRemaining[delayInfo]['off'])
                        if max_delay < timeRemaining[delayInfo]['off']:
                            max_delay = timeRemaining[delayInfo]['off']
                    self.my_setDriver('GV0', self.valveState)
        self.timer_expires = time.time()+max_delay
    
    def waterCtrlControl(self, command):
        logging.info('udiYoWaterMeterController manipuControl')
        state = int(command.get('value'))
        if state == 1:
            self.yoWaterCtrl.setState('open')
            self.valveState = 1
            self.my_setDriver('GV0',self.valveState)
   
            #self.node.reportCmd('DON')
        elif state == 0:
            self.yoWaterCtrl.setState('closed')
            self.valveState  = 0
            self.my_setDriver('GV0',self.valveState)
            #self.node.reportCmd('DOF')
        elif state == 5:
            logging.info('udiYoWaterMeterController set Delays Executed: {} {}'.format(self.onDelay, self.offDelay))
            #self.yolink.setMultiOutDelay(self.port, self.onDelay, self.offDelay)
            self.my_setDriver('GV1', self.onDelay * 60)
            self.my_setDriver('GV2', self.offDelay * 60)
            self.yoWaterCtrl.setDelayList([{'on':self.onDelay, 'off':self.offDelay}]) 
    '''

    def set_open(self, command = None):
        logging.info('udiYoWaterMeterController - set_open')
        self.yoWaterCtrl.setState('open')
        self.valveState  = 1
        self.my_setDriver('GV0',self.valveState )

        #self.node.reportCmd('DON')

    def set_close(self, command = None):
        logging.info('udiYoWaterMeterController - set_close')
        self.yoWaterCtrl.setState('closed')
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
        elif 'LLIMIT.uom6' in query:
            leak_lim = float(query.get('LLIMIT.uom6'))
        elif 'LLIMIT.uom8' in query:
            leak_lim = float(query.get('LLIMIT.uom8'))
        elif 'LLIMIT.uom35' in query:
            leak_lim = float(query.get('LLIMIT.uom35'))
        if leak_lim:
            data['attributes'] ['leakLimit'] = leak_lim

        #if 'LOFF.uom25' in query:
        #    data['attributes'] ['autoCloseValve'] = bool(query.get('LOFF.uom25'))

        if 'ORLIMIT.uom69' in query:
            or_lim = float(query.get('ORLIMIT.uom69'))
        elif 'ORLIMIT.uom6' in query:
            or_lim = float(query.get('ORLIMIT.uom6'))
        elif 'ORLIMIT.uom8' in query:
            or_lim = float(query.get('ORLIMIT.uom8'))
        elif 'ORLIMIT.uom35' in query:
            or_lim = float(query.get('ORLIMIT.uom35'))   
        if or_lim:
            data['attributes'] ['overrunAmount'] = or_lim     
        #if 'OROFF.uom25' in query:
        #    data['attributes'] ['overrunAmountACV'] = bool(query.get('OROFF.uom25')) 
        if 'ORTLIMIT.uom44' in query:
            data['attributes'] ['overrunDuration']  = int(query.get('ORTLIMIT.uom44'))
        #if 'ORTOFF' in query:
        #    data['attributes'] ['overrunDurationACV']  = bool(query.get('ORTOFF.uom25'))

        self.yoWaterCtrl.setAttributes(data)
        
    def update(self, command = None):
        logging.info('Update Status Executed')
        self.yoWaterCtrl.refreshDevice()
        
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
                #'DON'   : set_open,
                #'DOF'   : set_close,
                'SETATTRIB' : set_attributes,
                #'VALVECTRL': waterCtrlControl, 
                #'DELAY_CTRL' : program_delays,
                #'OFFDELAY' : prepOffDelay 
                }





