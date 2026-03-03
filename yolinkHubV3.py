import json
import time
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)

from yolink_mqtt_classV4 import YoLinkMQTTDevice


class YoLinkHub(YoLinkMQTTDevice):
    def __init__(yolink, yoAccess,  deviceInfo, callback):
        super().__init__(yoAccess,  deviceInfo, callback)
        yolink.methodList = ['getState', 'setWiFi' ]
        yolink.eventList = ['Report']
        yolink.HubName = 'HubEvent'
        yolink.eventTime = 'Time'
        yolink.type = deviceInfo['type']
        yolink.refreshHub()
  
    def refreshHub(yolink):
        logging.debug('refreshHub') 
        return(yolink.refreshDevice( ))

    
    def updateStatus(yolink, data):
        yolink.updateCallbackStatus(data, False)

    def setWiFi (yolink, SSID, password):
        logging.debug(yolink.type+' - setWiFi')
        maxAttempts = 2
        wifi_info = yolink.get_dict_data('wifi')
        wifi_enabled = isinstance(wifi_info, dict) and wifi_info.get('enable')
        if wifi_enabled:
            if password != '' and SSID != '' and wifi_enabled:
                data = {}
                data['params'] = {}
                data['method'] = yolink.type+'.setWiFi'
                data["targetDevice"] =  yolink.deviceInfo['deviceId']
                data["token"]= yolink.deviceInfo['token']
                data['params']['ssid'] = SSID
                data['params']['password'] = password
            
            yolink.publish_data( data)
            yolink.lastControlPacket = data
        else:
            logging.error('WiFi is not enabled so one cannot change ssid and password')

    def getPowerInfo(yolink):
        logging.debug('getPowerInfo')
        temp = {}
        try:
            temp['powered'] = yolink.get_data('dc', 'power')
            temp['battery'] = yolink.get_data('battery', 'power')
            temp['batteryState'] = yolink.get_data('batteryState', 'power')
            return(temp)
        except KeyError as e: 
            logging.error('No Battery Info available')
            return(temp)


    def getWiFiInfo(yolink):
        logging.debug('getWiFiInfo')
        return(yolink.get_dict_data('wifi'))


    def getEthernetInfo(yolink):
        logging.debug('getEthernetInfo')
        return(yolink.get_dict_data('eth'))

