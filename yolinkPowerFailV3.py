import time
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.DEBUG)

from yolink_mqtt_classV4 import YoLinkMQTTDevice


class YoLinkPowerFailSensor(YoLinkMQTTDevice):
    def __init__(yolink, yoAccess,  deviceInfo, callback):
        super().__init__(yoAccess,  deviceInfo, callback)
        #yolink.methodList = ['getState' ]
        #yolink.eventList = ['Alert' , 'getState', 'StatusChange']
        #yolink.eventName = 'PowerFailurerationEvent'
        #yolink.eventTime = 'Time'
        yolink.type = deviceInfo['type']
        #time.sleep(2)
       
    
    def updateStatus(yolink, data):
        yolink.updateCallbackStatus(data, False)

    def getPowerSupplyConnected(yolink):

        tmp = yolink.getDataStateValue('powerSupply') # from getStatus
        logging.debug('getPowerSupplyState: {}'.format(tmp))
        return(tmp)


    def getAlertType(yolink):
        tmp = yolink.getDataStateValue('alertType')
        logging.debug('{} getAlertType: {}'.format(yolink.type, tmp))
        if None == tmp:
            return(0)
        else:
            return(1)
              

    def muted(yolink):
        tmp = yolink.getDataStateValue('mute')
        logging.debug('getAlertType: {}'.format(tmp))
        return(tmp)        

    def getAlertState(yolink):
        tmp = yolink.getDataStateValue('state')
        logging.debug('{} - getState: {}'.format(yolink.type, tmp))
        if "normal"  == tmp:
            return(0)
        elif "alert" == tmp:
            return(1)
        elif "off" == tmp:
            return(2)
        else:
            return(99)
        



    '''    
    def getVibrationState(yolink):
        return(yolink.getState())
    
    def refreshSensor(yolink):
        logging.debug(yolink.type+ ' - refreshSensor')
        return(yolink.refreshDevice( ))
    '''

