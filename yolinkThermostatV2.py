
import json
import time

from yolink_mqtt_classV4 import YoLinkMQTTDevice
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)


class YoLinkThermostat(YoLinkMQTTDevice):
    """Wrapper for YoLink Thermostat device via MQTT"""
    
    def __init__(yolink, yoAccess, deviceInfo, callback):
        super().__init__(yoAccess, deviceInfo, callback)
        yolink.type = deviceInfo['type']
        logging.debug(f'YoLinkThermostat init: {yolink.type}')

    def updateStatus(yolink, data):
        """Handle incoming MQTT status updates"""
        logging.debug(f'YoLinkThermostat updateStatus: {data}')
        yolink.updateCallbackStatus(data, False)

   # def refreshDevice(yolink):
   #     """Request current device state via getState method"""
   #     logging.debug(f'{yolink.type} - refreshDevice')
   #     data={}
   #     return yolink.getDevice(data)

    def setLowTemp(yolink, lowTemp):
        """Set lower temperature setpoint (Celsius)"""
        logging.debug(f'{yolink.type} - setLowTemp: {lowTemp}')
        data={}
        data['params'] = {'lowTemp': float(lowTemp)}
        return yolink.setDevice(data)

    def setHighTemp(yolink, highTemp):
        """Set upper temperature setpoint (Celsius)"""
        logging.debug(f'{yolink.type} - setHighTemp: {highTemp}')
        data={}
        data['params'] = {'highTemp': float(highTemp)}
        return yolink.setDevice(data)

    def setMode(yolink, mode):
        """Set thermostat mode: 'cool', 'heat', 'auto', or 'off'"""
        logging.debug(f'{yolink.type} - setMode: {mode}')
        if mode.lower() not in ['cool', 'heat', 'auto', 'off']:
            logging.error(f'Invalid mode: {mode}')
            return False
        data={}
        data['params'] = {'mode': mode.lower()}
        return yolink.setDevice(data)

    def setFan(yolink, fan):
        """Set fan mode: 'on' or 'auto'"""
        logging.debug(f'{yolink.type} - setFan: {fan}')
        if fan.lower() not in ['on', 'auto']:
            logging.error(f'Invalid fan mode: {fan}')
            return False
        data={}
        data['params'] = {'fan': fan.lower()}
        return yolink.setDevice(data)

    def setScheduleMode(yolink, sche):
        """Set schedule mode: 'run' or 'hold'"""
        logging.debug(f'{yolink.type} - setScheduleMode: {sche}')
        if sche.lower() not in ['run', 'hold']:
            logging.error(f'Invalid schedule mode: {sche}')
            return False
        data={}
        data['params'] = {'sche': sche.lower()}
        return yolink.setDevice(data)

    def setECO(yolink, mode=None, lowTemp=None, highTemp=None):
        """Set ECO mode settings
        
        Args:
            mode: 'on' or 'off'
            lowTemp: Lower adjustment temperature (0-5°C)
            highTemp: Upper adjustment temperature (0-5°C)
        """
        logging.debug(f'{yolink.type} - setECO')
        data = {'method': 'Thermostat.setECO', 'targetDevice': yolink.deviceInfo['deviceId'], 'token': yolink.deviceInfo['token']}
        data['params'] = {}
        
        if mode is not None and mode.lower() in ['on', 'off']:
            data['params']['mode'] = mode.lower()
        if lowTemp is not None:
            data['params']['lowTemp'] = float(lowTemp)
        if highTemp is not None:
            data['params']['highTemp'] = float(highTemp)
        
        if not data['params']:
            logging.warning('setECO called with no valid parameters')
            return False
        
        return yolink.yoAccess.publish_data(data)

    def setProperties(yolink, minRuntime=None, coolLimit=None, heatLimit=None, mute=None, 
                      menuLock=None, auxStandby=None, auxMaxSpan=None, auxThreshold=None,
                      stage2Standby=None, stage2MaxSpan=None, stage2Threshold=None, master=None):
        """Set thermostat properties
        
        Args:
            minRuntime: Minimum running time (minutes)
            coolLimit: Minimum cooling temperature (Celsius)
            heatLimit: Maximum heating temperature (Celsius)
            mute: Mute setting (bool)
            menuLock: Menu lock setting (bool)
            auxStandby: AUX standby duration (minutes)
            auxMaxSpan: AUX max runtime (hours)
            auxThreshold: AUX threshold temperature (Celsius)
            stage2Standby: Stage2 standby duration (minutes)
            stage2MaxSpan: Stage2 max runtime (hours)
            stage2Threshold: Stage2 threshold temperature (Celsius)
            master: Temperature source ('local', 'sensor1', 'sensor2')
        """
        logging.debug(f'{yolink.type} - setProperties')
        data = {'method': 'Thermostat.setProperties', 'targetDevice': yolink.deviceInfo['deviceId'], 'token': yolink.deviceInfo['token']}
        data['params'] = {}
        
        if minRuntime is not None:
            data['params']['minRuntime'] = int(minRuntime)
        if coolLimit is not None:
            data['params']['coolLimit'] = float(coolLimit)
        if heatLimit is not None:
            data['params']['heatLimit'] = float(heatLimit)
        if mute is not None:
            data['params']['mute'] = bool(mute)
        if menuLock is not None:
            data['params']['menuLock'] = bool(menuLock)
        if auxStandby is not None:
            data['params']['auxStandby'] = int(auxStandby)
        if auxMaxSpan is not None:
            data['params']['auxMaxSpan'] = int(auxMaxSpan)
        if auxThreshold is not None:
            data['params']['auxThreshold'] = float(auxThreshold)
        if stage2Standby is not None:
            data['params']['stage2Standby'] = int(stage2Standby)
        if stage2MaxSpan is not None:
            data['params']['stage2MaxSpan'] = int(stage2MaxSpan)
        if stage2Threshold is not None:
            data['params']['stage2Threshold'] = float(stage2Threshold)
        if master is not None and master.lower() in ['local', 'sensor1', 'sensor2']:
            data['params']['master'] = master.lower()
        
        if not data['params']:
            logging.warning('setProperties called with no valid parameters')
            return False
        
        return yolink.yoAccess.publish_data(data)

    def setCorrection(yolink, temperature=None, humidity=None):
        """Set temperature and humidity sensor corrections
        
        Args:
            temperature: Temperature correction value (-5 to +5°C)
            humidity: Humidity correction value (-10 to +10%)
        """
        logging.debug(f'{yolink.type} - setCorrection')
        data = {'method': 'Thermostat.setCorrection', 'targetDevice': yolink.deviceInfo['deviceId'], 'token': yolink.deviceInfo['token']}
        data['params'] = {}
        
        if temperature is not None:
            data['params']['temperature'] = float(temperature)
        if humidity is not None:
            data['params']['humidity'] = int(humidity)
        
        if not data['params']:
            logging.warning('setCorrection called with no valid parameters')
            return False
        
        return yolink.setDevice(data)

    def getVersion(yolink):
        """Get firmware version info"""
        logging.debug(f'{yolink.type} - getVersion')
        data = {'method': 'Thermostat.getVersion', 'targetDevice': yolink.deviceInfo['deviceId'], 'token': yolink.deviceInfo['token']}
        return yolink.setDevice(data)

    def getState(yolink):
        """Get current device state"""
        logging.debug(f'{yolink.type} - getState')
        return yolink.refreshDevice()