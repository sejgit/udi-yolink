
import time
import json

from yolink_mqtt_classV4 import YoLinkMQTTDevice
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)

class YoLinkSoilSensor(YoLinkMQTTDevice):
    def __init__(yolink, yoAccess,  deviceInfo, callback):
        super().__init__( yoAccess,  deviceInfo, callback)    
        yolink.methodList = ['getState' ]
        yolink.eventList = ['Report']
        yolink.tempName = 'THEvent'
        yolink.temperature = 'Temperature'
        yolink.humidity = 'Humidity'
        yolink.eventTime = 'Time'
        yolink.type = deviceInfo['type']
        yolink.sensordata_24_hours = {}
        #time.sleep(2)

    '''    
    def initNode(yolink):
        yolink.refreshSensor()
        time.sleep(2)
            #yolink.online = yolink.getOnlineStatus()
            if not yolink.online:
            logging.error('THsensor not online')
    '''
    def update_data_24_hours(yolink, unix_time, tempC=None, hum=None):
        timeNow = int(time.time())
        yolink.sensordata_24_hours[unix_time] = {'tempC': tempC, 'hum': hum}
        tmax = -273.15
        tmin = 1000
        hmax = -1
        hmin = 101
        for timestamp in list(yolink.sensordata_24_hours.keys()):
            if timeNow - timestamp > 86400:
                del yolink.sensordata_24_hours[timestamp]
            else:
                if isinstance(yolink.sensordata_24_hours[timestamp]['tempC'], (int, float)):
                    if yolink.sensordata_24_hours[timestamp]['tempC'] > tmax:
                        tmax = yolink.sensordata_24_hours[timestamp]['tempC']
                    if yolink.sensordata_24_hours[timestamp]['tempC'] < tmin:
                        tmin = yolink.sensordata_24_hours[timestamp]['tempC']
                if  isinstance(yolink.sensordata_24_hours[timestamp]['hum'], (int, float)):
                    if yolink.sensordata_24_hours[timestamp]['hum'] > hmax:
                        hmax = yolink.sensordata_24_hours[timestamp]['hum']
                    if yolink.sensordata_24_hours[timestamp]['hum'] < hmin:
                        hmin = yolink.sensordata_24_hours[timestamp]['hum']
        
        if tmax == -273.15:
            tmax = None
        if tmin == 1000:
            tmin = None 
        if hmax == -1:
            hmax = None     
        if hmin == 101:
            hmin = None
        logging.debug(f'24H Data - tmin: {tmin}, tmax: {tmax}, hmin: {hmin}, hmax: {hmax} ')
        logging.debug(f'24H Data Store: {json.dumps(yolink.sensordata_24_hours, indent=4)} ')
        return(tmin, tmax, hmin, hmax)
    
    def updateStatus(yolink, data):
        logging.debug('updataStatus THsensor  : {}'.format(data))
        yolink.updateCallbackStatus(data, False)

    def refreshSensor(yolink):
        logging.debug(yolink.type+ ' - refreshSensor')
        return(yolink.refreshDevice( ))

    #def onlineStatus(yolink):
    #    logging.debug(yolink.type+ ' - getOnlineStatus')
    #    return(yolink.getOnlineStatus( ))

       
    #def getTempValueF(yolink):
    #   return(yolink.getStateValue('temperature')*9/5+32)
    
    #def getTempValueC(yolink):
    #    return(yolink.getStateValue('temperature'))

    #def getHumidityValue(yolink):
    #   return(yolink.getStateValue('humidity'))
    
    
    '''
    def getAlarms(yolink):
        return(yolink.getStateValue('alarm'))

    def getBattery(yolink):
        return(yolink.getStateValue('battery'))
    '''    

    #def probeState(yolink):
    #     return(yolink.getState() )

    #def probeData(yolink):
    #    return(yolink.getData() )

