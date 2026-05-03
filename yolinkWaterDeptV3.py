
import time


from yolink_mqtt_classV4 import YoLinkMQTTDevice
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)

class YoLinkWaterDeptSensor(YoLinkMQTTDevice):
    def __init__(yolink, yoAccess,  deviceInfo, callback):
        super().__init__( yoAccess,  deviceInfo, callback)    
        #yolink.methodList = ['getState', 'setAttributes' ]
        #yolink.eventList = ['Report']
        #yolink.tempName = 'WaterDept'
        #yolink.temperature = 'Temperature'
        #yolink.humidity = 'Humidity'
        #yolink.eventTime = 'Time'
        yolink.type = deviceInfo['type']
        #time.sleep(2)
        yolink.alarmSettings = {'standby':None, 'interval':None, 'high':None, 'low':None}

    
    def updateStatus(yolink, data):
        logging.debug('updataStatus WaterDept  : {}'.format(data))
        yolink.updateCallbackStatus(data, False)
        yolink.alarmSettings = yolink.getAlarmSettings()

    def refreshSensor(yolink):
        logging.debug(yolink.type+ ' - refreshSensor')
        return(yolink.refreshDevice( ))

    def setAttributes(yolink, attribs):
        logging.debug(yolink.type+ ' - setAttributes')
        data = {}
        data['params'] = {}
        try:
            if 'setAttributes' in yolink.methodList:
                alarm_settings = yolink.get_data('alarmSettings', 'state')
                if not isinstance(alarm_settings, dict):
                    yolink.refreshDevice()
                    alarm_settings = yolink.get_data('alarmSettings', 'state')
                logging.debug('alarmSettings data: {}'.format(alarm_settings))
                if 'low' in attribs:
                    yolink.alarmSettings['low'] = attribs['low']
                else:
                    yolink.alarmSettings['low'] = alarm_settings.get('low') if isinstance(alarm_settings, dict) else None
                if 'high' in attribs:
                    yolink.alarmSettings['high'] = attribs['high']
                else:
                    yolink.alarmSettings['high'] = alarm_settings.get('high') if isinstance(alarm_settings, dict) else None

                if 'standby' in attribs:
                    yolink.alarmSettings['standby'] = attribs['standby']
                else:
                    yolink.alarmSettings['standby'] = alarm_settings.get('standby') if isinstance(alarm_settings, dict) else None
                if 'interval' in attribs:
                    yolink.alarmSettings['interval'] = attribs['interval']    
                else:
                    yolink.alarmSettings['interval'] = alarm_settings.get('interval') if isinstance(alarm_settings, dict) else None

                data['params']['alarmSetting'] = yolink.alarmSettings
                return(yolink.setDevice( data))

        except Exception as e:
            logging.error(f'Exception - setAttributes {e}' )
            return(False)
        
    
    def getAlarms(yolink):
        logging.debug(yolink.type+ ' - getAlarms')
        try:
            alarms = {}
            if yolink.check_system_online():
                alarm_data = yolink.get_data('alarm', 'state')
                if isinstance(alarm_data, dict):
                    alarms['low'] = alarm_data.get('lowAlarm')
                    alarms['high'] = alarm_data.get('highAlarm')
                    alarms['error'] = alarm_data.get('detectorError')
            return(alarms)
        
        except Exception as e:
            logging.error(f'Exception - getAlarms data not found {e}' )
            return({})
        
    def getAlarmSettings(yolink):
        logging.debug(yolink.type+ ' - getAlarmsLevels')
        try:
            if yolink.check_system_online():
                alarm_settings = yolink.get_data('alarmSettings', 'state')
                if isinstance(alarm_settings, dict):
                    yolink.alarmSettings['low'] = alarm_settings.get('low')
                    yolink.alarmSettings['high'] = alarm_settings.get('high')
                    yolink.alarmSettings['standby'] = alarm_settings.get('standby')
                    yolink.alarmSettings['interval'] = alarm_settings.get('interval')
            return(yolink.alarmSettings)
        
        except Exception as e:
            logging.error(f'Exception - getAlarmSettings not found {e}' )
            return({})
    

    def getWaterDepth(yolink):
        logging.debug(yolink.type+ ' - getWaterDepth')
        try:
            waterDepth = None
            if yolink.check_system_online():
                waterDepth = yolink.get_data('waterDepth', 'state')
                if waterDepth is None:
                    waterDepth = yolink.get_data('waterDepth')
            return(waterDepth)
        
        except Exception as e:
            logging.error(f'Exception - getWaterDepth not found' )
        
'''
Stand-Alone Operation of WaterDept (no call back to live update data - pooling data in upper APP)
''' 

    