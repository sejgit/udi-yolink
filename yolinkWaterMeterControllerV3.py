import json
import time

from typing import Any, Union, List, Dict
from yolink_mqtt_classV3 import YoLinkMQTTDevice
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)





class YoLinkWaterMeter(YoLinkMQTTDevice):
    def __init__(yolink, yoAccess,  deviceInfo, callback):
        super().__init__( yoAccess,  deviceInfo, callback)
  
        yolink.maxSchedules = 6
        yolink.methodList = ['setAttributes', 'getState', 'setState', 'setDelay', 'getSchedules', 'setSchedules', 'getUpdate'   ]
        yolink.eventList = ['StatusChange', 'Report', 'HourlyReport']
        yolink.stateList = ['open', 'closed', 'on', 'off']
        yolink.ManipulatorName = 'WaterMeterControllerEvent'
        yolink.eventTime = 'Time'
        yolink.type = deviceInfo['type']
        yolink.MQTT_type = 'c'
        yolink.uom = None
        #time.sleep(1)


    
    def initNode(yolink):
        logging.debug('init node')
        yolink.WMcount = None
        yolink.meter_unit = None
        yolink.water_meter_count = 1 
        yolink.refreshDevice()
        time.sleep(2)

        if not yolink.online:
            logging.error('Water Meter Controller device not online')
        #    yolink.refreshSchedules()
        #else:
        #    
        #yolink.refreshFW
    

    
    def updateStatus(yolink, data, WM_index = None):
        yolink.updateCallbackStatus(data, False)


    def getMeterCount(yolink):
        yolink.water_meter_count = 1
        if yolink.online:
            if yolink.get_data('state', 'valve') is not None:
                yolink.water_meter_count = 1

            else:
                valve_list = yolink.get_data('state','meters')
                logging.debug(f'valve_list: {valve_list}')  
                if valve_list is not None and isinstance(valve_list, dict):
                    yolink.water_meter_count = len(valve_list)
        logging.debug(f'Water Meter Controller - meter count set to {yolink.water_meter_count}')
        return(yolink.water_meter_count)

    def getMeterUnit(yolink):   
        yolink.meter_unit = None
        if yolink.online:
            meter_unit = yolink.get_data('attributes', 'meterUnit')
            yolink.meter_unit = meter_unit
            logging.info(f'Water Meter Controller - meter unit set to {yolink.meter_unit}')
        return(yolink.meter_unit)

    def setValveState(yolink, state, WM_index=None):
        #yolink.online = yolink.getOnlineStatus()
        try:
            if yolink.online:   
                data = {}
                state = state.lower()
                data['params'] = {}
                if isinstance(state, str):
                    if state in ['on', 'open']:
                        state = 'open'
                    if state in ['off', 'closed', 'close']:
                        state = 'close'              
                    if isinstance(WM_index, int) :
                        data['params']['valves']={str(WM_index):state}
                    else:
                        data['params']['valve'] = state
                elif isinstance(state, dict) and len(state) > 0:
                    data['params']['valves'] = state

                return(yolink.setDevice(data))
        except Exception as e:
            logging.error(f'Exception for {state}, {WM_index} as {e} ')
    #def setAttrib(yolink, attributes):
    #    logging.debug(yolink.type+' - setAttributes')
    #    return(yolink.setAttributes(attributes))


    
    def getBattery(yolink):
        logging.debug(yolink.type+' - getBattery')
        bat_lvl = None
        pwr_mode = None
        logging.debug('online {} , data {}'.format(yolink.online, yolink.dataAPI[yolink.dData] ))
        if yolink.online:   
            if 'battery' in yolink.dataAPI[yolink.dData]:
                bat_lvl = yolink.dataAPI[yolink.dData]['battery']
            elif yolink.dState in yolink.dataAPI[yolink.dData] and 'battery' in yolink.dataAPI[yolink.dData][yolink.dState]: 
                bat_lvl = yolink.dataAPI[yolink.dData][yolink.dState]['battery']    
            if 'powerSupply' in yolink.dataAPI[yolink.dData]:                
                pwr_mode = yolink.dataAPI[yolink.dData]['powerSupply']
            elif yolink.dState in yolink.dataAPI[yolink.dData] and 'powerSupply' in yolink.dataAPI[yolink.dData][yolink.dState]:
                pwr_mode = yolink.dataAPI[yolink.dData][yolink.dState]['powerSupply']                   
        return(pwr_mode, bat_lvl)
    

    def getWaterTemperature(yolink):
        logging.debug(yolink.type+' - getWaterTemperature')
        water_temp = None
        #yolink.online = yolink.getOnlineStatus()
        if yolink.online:   
            if yolink.dState in yolink.dataAPI[yolink.dData]:
                if 'temperature' in yolink.dataAPI[yolink.dData][yolink.dState]:
                    water_temp = yolink.dataAPI[yolink.dData][yolink.dState]['temperature']
        return(water_temp)
       

    def getValveState(yolink, WM_index = None):
        logging.debug(yolink.type+' - getValveState')
        #yolink.online = yolink.getOnlineStatus()
        valves = None
        if yolink.online:   
            if yolink.dState in yolink.dataAPI[yolink.dData]:
                if 'valve' in yolink.dataAPI[yolink.dData][yolink.dState]:
                    valves = yolink.dataAPI[yolink.dData][yolink.dState]['valve']
                if 'state' in yolink.dataAPI[yolink.dData][yolink.dState] and 'valves' in yolink.dataAPI[yolink.dData][yolink.dState]['state'] :                    
                    valves = yolink.dataAPI[yolink.dData][yolink.dState]['state']['valves']
                    if isinstance(yolink.dataAPI[yolink.dData][yolink.dState]['state']['valves'], dict):
                        valves = yolink.dataAPI[yolink.dData][yolink.dState]['state']['valves']
                        if isinstance( WM_index, int):
                            if str(WM_index) in valves:
                                valves[str(WM_index)] == yolink.dataAPI[yolink.dData][yolink.dState]['state']['valves'][str(WM_index)]

        return(valves)
   

    def getMeterReading(yolink, WM_index = None):
        try:
            meter_correction_factor = 1
            logging.debug(yolink.type+f' - getMeterReading {json.dumps(yolink.dataAPI[yolink.dData], indent=4)}')
            temp = {'total':None, 'water_runing':None, 'recent_amount':None, 'recent_duration':None, 'daily_usage':None}
            #yolink.online = yolink.getOnlineStatus()
            logging.debug(f'temp1 {temp}')
            if yolink.online:   
                #logging.debug(f'yolink.dataAPI[yolink.dData][yolink.dState]: {yolink.dataAPI[yolink.dData][yolink.dState]} ')
                #if 'attributes' in yolink.dataAPI[yolink.dData] and 'meterStepFactor' in yolink.dataAPI[yolink.dData]['attributes']:
                #    meter_correction_factor = yolink.dataAPI[yolink.dData]['attributes']['meterStepFactor']
                meter_correction_factor = float(yolink.get_data('attributes', 'meterStepFactor', WM_index))
                if meter_correction_factor is None:     
                    meter_correction_factor = 1.0   
                #logging.debug(f'logic {yolink.dState in yolink.dataAPI[yolink.dData]}')
                if 'meter' in yolink.dataAPI[yolink.dData][yolink.dState]:
                    meter = yolink.get_data(yolink.dState, 'meter')
                    waterFlowing = yolink.get_data(yolink.dState, 'waterFlowing')
                elif 'state' in yolink.dataAPI[yolink.dData][yolink.dState] and 'meters' in yolink.dataAPI[yolink.dData][yolink.dState]['state']:                    
                    meter = yolink.get_data(yolink.dState, 'meters')
                    waterFlowing = yolink.get_data(yolink.dState, 'waterFlowing')
                logging.debug(f'meter {meter} waterFlowing {waterFlowing} ')
                
                #if yolink.dState in yolink.dataAPI[yolink.dData]:
                logging.debug(f'type of meter {type(meter)} type of waterFlowing {type(waterFlowing)} ')
                if not isinstance(meter, dict):
                    temp['total'] = round(meter/meter_correction_factor,1)
                    temp['water_runing'] = waterFlowing
                else:
                    for index in meter:
                        meter[WM_index] = round(meter[index]/meter_correction_factor,1)
                    temp['total'] = meter
                    temp['water_runing'] = waterFlowing

                recent_amount  = yolink.get_data('recentUsage', 'amount', WM_index)
                recent_duration = yolink.get_data('recentUsage', 'duration', WM_index)
                daily_usage = yolink.get_data('dailyUsage', 'amount', WM_index)
                daily_duration = yolink.get_data('dailyUsage', 'duration', WM_index) 
                if recent_amount is not None:
                    temp['recent_amount'] = round(recent_amount/meter_correction_factor,1)
                if recent_duration is not None:
                    temp['recent_duration'] = recent_duration
                if daily_usage is not None:
                    temp['daily_usage'] = round(daily_usage/meter_correction_factor,1)  
                else:
                    daily_usage = yolink.get_data(None, 'dailyUsage', WM_index)
                if daily_duration is not None:
                    temp['daily_duration'] = daily_duration

                
                if 'recentUsage' in yolink.dataAPI[yolink.dData]:
                    if 'amount' in yolink.dataAPI[yolink.dData]['recentUsage']:
                        temp['recent_amount'] = round(yolink.dataAPI[yolink.dData]['recentUsage']['amount']/meter_correction_factor,1)
                    if 'duration' in yolink.dataAPI[yolink.dData]['recentUsage']:
                        temp['recent_duration'] = yolink.dataAPI[yolink.dData]['recentUsage']['duration']
                if 'dailyUsage' in yolink.dataAPI[yolink.dData]:
                    if isinstance(yolink.dataAPI[yolink.dData]['dailyUsage'], dict):
                        if 'amount' in yolink.dataAPI[yolink.dData]['dailyUsage']:
                            temp['daily_usage'] = round(yolink.dataAPI[yolink.dData]['dailyUsage']['amount']/meter_correction_factor,1)
                        if 'duration' in yolink.dataAPI[yolink.dData]['dailyUsage']:
                            temp['daily_duration'] = yolink.dataAPI[yolink.dData]['dailyUsage']['duration']           
                        else:
                            temp['daily_duration'] = None     
                    elif isinstance(yolink.dataAPI[yolink.dData]['dailyUsage'], int) or isinstance(yolink.dataAPI[yolink.dData]['dailyUsage'], float):
                        temp['daily_usage'] = round(yolink.dataAPI[yolink.dData]['dailyUsage']/meter_correction_factor,1)
                
            logging.debug(f' temp {temp}')   
            return(temp)

        except KeyError as e:
            logging.error(f'EXCEPTION - getMeterReading Key error {e}') 
            return(None)
        except ValueError as e:
            logging.error(f'EXCEPTION - getMeterReading Value error {e}') 
            return(None)
    

   
    
    def getAlarms(yolink, WM_index = None):
        try:
            logging.debug(yolink.type+' - getAlarms')
            alarms = {}
            if yolink.online:   

                if 'alarm' in yolink.dataAPI[yolink.dData]:
                    alarms = yolink.dataAPI[yolink.dData]['alarm']
                    if isinstance( WM_index, int):
                        for item in yolink.dataAPI[yolink.dData]['alarm']:
                            if isinstance(yolink.dataAPI[yolink.dData]['alarm'][item], dict):
                                if str(WM_index) in item:
                                    alarms[item] = yolink.dataAPI[yolink.dData]['alarm'][item][str(WM_index)]
            return(alarms)

        except KeyError as e:
            logging.error(f'Exception : {e}')
            return(None)
        

    def getAttributes(yolink,  WM_index = None):
        try:
            logging.debug(yolink.type+' - getAttributes')
            attributes = {}
            if yolink.online: 
                data = yolink.get_data('attributes', 'meterUnit')  
                if 'attributes' in yolink.dataAPI[yolink.dData]:
                    attributes = yolink.dataAPI[yolink.dData]['attributes' ]
                    if 'meterUnit' in attributes and yolink.uom is None:
                        yolink.uom = attributes['meterUnit']
                    if isinstance( WM_index, int):
                        for item in yolink.dataAPI[yolink.dData]['attributes']:
                            if isinstance(yolink.dataAPI[yolink.dData]['attributes'][item], dict):
                                if str(WM_index) in item:
                                    attributes[item] = yolink.dataAPI[yolink.dData]['attributes'][item][str(WM_index)]                        
                                    
            return(attributes)

        except KeyError as e:
            logging.error(f'Exception : {e}')
            return(None)
        




class YoLinkWaterMeterCtrl(YoLinkWaterMeter):
    def __init__(yolink, yoAccess,  deviceInfo):
        super().__init__(  yoAccess,  deviceInfo, yolink.updateStatus)
        yolink.initNode()


    def updateStatus(yolink, data):
        yolink.updateCallbackStatus(data, True)