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
from yolinkSprinklerV2 import YoLinkSprinkler
from udiYoSchedule import udiYoSchedule




class udiYoSprinkler2(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, start_done, configDoneHandler,   water_meter_unit2uom, calculate_water_volume, state2ISY, update_schedule_data, node_queue, wait_for_node_done, checkNameSync

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
            #{'driver': 'ST', 'value': 0, 'uom': 70}, # Water flow
           
            {'driver': 'ST', 'value': 99, 'uom': 25}, #Water running 
            {'driver': 'GV1', 'value': 99, 'uom': 25}, #no Water When running 
            {'driver': 'GV10', 'value': 99, 'uom': 151}, #Time for lateest operatiowaterdelay type

            #{'driver': 'GV2', 'value': 99, 'uom': 25}, #water mode attrib
            #{'driver': 'GV3', 'value': 99, 'uom': 25},  #Water Method attrib 
            #{'driver': 'GV4', 'value': 99, 'uom': 25},  #Amount attrib 

            {'driver': 'GV5', 'value': 99, 'uom': 25},  #Latest operation
            #{'driver': 'GV6', 'value': 99, 'uom': 25},  # Latest Mode
            {'driver': 'GV7', 'value': 99, 'uom': 25}, #Latest Method
            {'driver': 'GV8', 'value': 99, 'uom': 25}, #Latest Volume                                             
            {'driver': 'GV9', 'value': 99, 'uom': 25}, #Latest Alert
            #{'driver': 'GV10', 'value': 99, 'uom': 25}, #no Water When Last run 

            #{'driver': 'GV10', 'value': 99, 'uom': 70}, #waterdelay type values
            {'driver': 'GV12', 'value': 99, 'uom' : 44}, # delay valuetype
     
            {'driver': 'GV20', 'value': 99, 'uom': 25},
            {'driver': 'GV30', 'value': 99, 'uom': 25},
            {'driver': 'BATLVL', 'value': 99, 'uom': 25},
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
    
        if self.water_unit not in [0,3]:
            logging.error('Only Liter and Gallon supported for now')

        self.devInfo =  deviceInfo
        self.yoSprinkler= None
        self.schedule = None
        self.node_ready = False
        self.configDone = False
        self.system_ready = False        
        self._update_lock = threading.Lock()
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
        self.poly.subscribe(self.poly.CONFIGDONE, self.configDoneHandler)

        polyglot.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        self.adr_list = []
        self.adr_list.append(address)
        logging.debug('udiYoSprinkler2 INIT done- {}'.format(self.commands))
        self.node_ready = True



    def start(self):
        logging.info('Start - udiYoSprinkler2')
        while not self.node_ready  or not self.configDone:
            time.sleep(0.5)
        self.my_setDriver('GV30', 1)
        self.my_setDriver('GV20', 0)
        # Create schedule node before device online check
        time.sleep(2)
        self.yoSprinkler.initNode()
        time.sleep(1)
        tries = 1
        while not self.yoSprinkler.check_system_online() and (tries <= 5 or self.yoSprinkler.throttled()):
            logging.info(f'Waiting for device {self.name} to come online...')
            time.sleep(2)
            tries += 1
        self.yoSprinkler = YoLinkSprinkler(self.yoAccess, self.devInfo, self.updateStatus)

        self.meter_unit = self.yoSprinkler.get_data('meterUnit', 'attributes')
        self.step_factor = self.yoSprinkler.get_data('meterStepFactor', 'attributes')
        self.ISYwater_unit = self.yoAccess.get_water_unit()
        self.ISYmeter_uom = self.water_meter_unit2uom(self.ISYwater_unit)
        logging.debug(f'meter unit : {self.meter_unit} ISY unit: {self.ISYwater_unit} uom: {self.ISYmeter_uom} meterFactor: {self.step_factor}')
        self.start_done()

    def create_schedule_nodes(self):
        sch_address = self.address[4:14] + '_SCH'
        sch_address = self.poly.getValidAddress(sch_address)
        self.schedule = udiYoSchedule(self.poly, self.address, sch_address, 'Schedules', self.yoAccess, self.devInfo)
        self.adr_list.append(sch_address)
        return [sch_address]

    def stop (self):
        logging.info('Stop udiYoSprinkler2')
        self.my_setDriver('GV30', 0)
        if getattr(self, 'yoSprinkler', None):
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
                while not self.node_ready or not self.system_ready or not self.configDone:
                    time.sleep(0.5)
                message_type, message_action = self.yoSprinkler.get_message_type()
                unix_time = self.yoSprinkler.get_report_time('time')
                self.my_setDriver('TIME', unix_time, 151)
                if message_type and 'Schedules' in str(message_type):
                    if self.schedule is not None:
                        self.schedule.update_schedule_data(source_device=self.yoSprinkler)
                    return
                if self.yoSprinkler.check_system_online():
                    self.my_setDriver('GV30', 1)
                    if self.yoSprinkler.emptyData():
                        logging.debug('Empty data received - skip updateData')
                        self.my_setDriver('GV20', 6)
                        return
                    if self.ISYmeter_uom is None:
                        logging.debug(f'meter unit : { self.meter_unit}')
                        #self.my_setDriver('GV4',  self.meter_unit, 25)          
                        self.ISYmeter_uom = self.water_meter_unit2uom( self.meter_unit)
                    running = self.yoSprinkler.get_data('running', 'state')
                    if isinstance(running, bool):
                        logging.debug(f'water running : {running}')
                        self.my_setDriver('ST', self.state2ISY(running), type=message_type)
                    no_water = self.yoSprinkler.get_data('noWaterWhenRunning', 'state')
                    if isinstance(no_water, bool):
                        logging.debug(f'water noWaterWhenRunning : {no_water}')       
                        self.my_setDriver('GV1', self.state2ISY(no_water), type=message_type)   

                    events_happened = self.yoSprinkler.get_data('metadata')
                    if isinstance(events_happened, dict) and events_happened is not {}:
                        if 'events' in events_happened:
                            events = events_happened['events']
                            logging.debug(f'events: {events}')
                            if isinstance(events, list) and len(events) > 0:
                                for event in events:
                                    if event in [ 'WaterStart', 'WaterStop', 'WaterDone']:
                                        self.my_setDriver('GV5', self.state2ISY(event in ['WaterStart']), type=message_type)
                                        #self.my_setDriver('ST', self.state2ISY(event in ['WaterStart']), type=message_type)
                            if 'NoWater' in events or 'FlowProtect' in events:
                                self.my_setDriver('GV9', 1, type=message_type, UOM=25)
                                type = self.yoSprinkler.get_data('type', 'water')
                                amount = self.yoSprinkler.get_data('value', 'water')
                                if isinstance(amount, (int,float)):
                                    if type in ['amount']:
                                        self.my_setDriver('GV7', 0, UOM=25)
                                        if self.ISYwater_unit == 0: #gallon
                                            amount = amount * 0.264172
                                        amount = round(float(self.calculate_water_volume(amount/self.step_factor,  self.meter_unit,  self.ISYwater_unit)), 1)
                                        self.my_setDriver('GV8', amount, UOM =self.ISYmeter_uom)
                                    elif type in ['duration']:
                                        self.my_setDriver('GV7', 1, UOM=25)
                                        self.my_setDriver('GV8', amount, type=message_type, UOM=44)
                            else:
                                self.my_setDriver('GV9', 0, type=message_type, UOM=25)

                        if 'data' in events_happened:
                            eventsdata = events_happened['data']
                            logging.debug(f'events data: {eventsdata}') 
                            if isinstance(eventsdata, dict):
                                type = self.yoSprinkler.get_data('type', 'water')
                                amount = self.yoSprinkler.get_data('value', 'water')

                                if isinstance(amount, (int,float)):
                                    if type in ['amount']:
                                        self.my_setDriver('GV7', 0, UOM=25)
                                        if self.ISYwater_unit == 0: #gallon
                                            amount = amount * 0.264172
                                        #amount = round(float(self.calculate_water_volume(amount/self.step_factor,  self.meter_unit,  self.ISYwater_unit)), 1)
                                        self.my_setDriver('GV8', round(amount,1), UOM =self.ISYmeter_uom)
                                    elif type in ['duration']:
                                        self.my_setDriver('GV7', 1, UOM=25)
                                        self.my_setDriver('GV8', amount, type=message_type, UOM=44)

                        self.my_setDriver('GV10', unix_time, type=message_type, UOM=151)
                            
                    water_amount = self.yoSprinkler.get_data('waterFlowing')
                    logging.debug(f'water manualWater value: {water_amount}')
                    if isinstance(water_amount, (int,float)):
                        #round(float(self.calculate_water_volume(water_amount/self.step_factor,  self.meter_unit,  self.ISYwater_unit)), 1)
                        self.my_setDriver('ST', self.state2ISY( water_amount != 0), type=message_type)
                
                    water_delay = self.yoSprinkler.get_data('duration', 'waterDelay')
                    logging.debug(f'water delay value: {water_delay}')
                    if isinstance(water_delay, (int,float)):
                        self.my_setDriver('GV12', water_delay, type=message_type, UOM=44)

   
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
        if self.yoSprinkler is not None:
            with self._update_lock:
                self.yoSprinkler.updateStatus(data)
                self.updateData()


    def start_stop(self, command):
        logging.info(f'udiYoSprinkler2 - start_stop {command}')
        
        #action = int(command.get('value'))
        query = command.get("query")
        data={}
        data['params'] = {}
        logging.debug(f'start_stop action: {query}')
        if 'startstop.uom25' in query:
            action = int(query.get('startstop.uom25'))
            if action in [ 0, 1]:  # stop
                data['params']['running'] = action == 1
        if 'watermode.uom25' in query:
            mode = int(query.get('watermode.uom25'))
            logging.debug(f'start_stop watermode: {mode}')      
            if mode == 0:
                data['params']['waterMode'] = 'manual'
            elif mode == 1:
                data['params']['waterMode'] = 'schedule'    

        self.yoSprinkler.setDevice(data)


        #self.node.reportCmd('DON')


    def set_watermode(self, command):
        logging.info(f'set_watermode {command}')

        data={}
        data['params'] = {}

        mode = int(command.get("value"))
        logging.debug(f'set_watermode mode: {mode}')      
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
        data['params']['manualWater'] = {}
        leak_lim = None
        or_lim = None
        if 'wmethod.uom25' in query:
            method = int (query.get('wmethod.uom25'))
            if method == 0:
                self.mode = 'amount'
                data['params']['manualWater']['type'] = 'amount'
            elif method == 1:
                self.mode = 'duration'
                data['params']['manualWater']['type'] = 'duration'
            #self.my_setDriver('GV8', method)

        if 'wamount.uom70' in query:
            amount = float (query.get('wamount.uom70'))
            #self.my_setDriver('GV9', amount)
            if self.mode == 'amount':
                if self.ISYwater_unit == 0: #gallon
                    amount = amount / 0.264172
                amount = amount * self.step_factor
            data['params'] ['manualWater']['value'] = int(amount) 
           
        self.yoSprinkler.setAttributes(data)


    def update(self, command = None):
        logging.info('Update Status Executed')
        self.yoSprinkler.refreshDevice()
        # Keep schedule child node in sync when user requests UPDATE.
        self.yoSprinkler.refreshSchedules()
        



    def set_delay(self, command):
        logging.info(f'set_delay {command}')
        delay_time = int(command.get('value'))
        self.yoSprinkler.setAttributes(delay_time)   

    commands = {
                'UPDATE': update,
                'STARTSTOP'   : start_stop,
                #'WATERMODE' : set_watermode,
                'WATTRIB' : set_attributes,
                'WDELAY' : set_delay,

                }





