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


class YoLinkLock(YoLinkMQTTDevice):
    def __init__(yolink, yoAccess,  deviceInfo, callback):
        super().__init__(yoAccess,  deviceInfo, callback)
        
        #yolink.methodList = ['getState', 'fetchState', 'setState' ]
        #yolink.eventList = ['StatusChange', 'Report', 'getState']
        #yolink.stateList = ['open', 'closed', 'lock', 'unlock']
        #yolink.eventTime = 'Time'
        yolink.type = deviceInfo['type']
        yolink.MQTT_type = 'c'
        yolink.alertType = ModuleNotFoundError
        yolink.doorBellRing = False
        yolink.lock_type = deviceInfo['type']
        #time.sleep(2)
        
        #yolink.refreshState()
        #input()
        #yolink.refreshSchedules()
        #yolink.refreshFWversion()

    '''
    def initNode(yolink):
        attemps = 0
        maxAttemts = 3
        yolink.refreshState()
        time.sleep(1)
        #yolink.online = yolink.getOnlineStatus()
        while not yolink.online and attemps <= maxAttemts:
            yolink.refreshState()
            time.sleep(1)
        if yolink.online:    
            logging.error('Outlet not online')
        #else:
        #   yolink.refreshSchedules()
        #self.refreshFWversion()
        #print(' YoLinkSW - finished intializing')
    '''
    
    def updateStatus(yolink, data):
        yolink.updateCallbackStatus(data, False)
        if 'event' in data:
            if '.Alert' in data['event']:
                if 'alert' in data['data']:
                    if ['type'] in  data['data']['alert']:
                        yolink.alertType = data['data']['alert']['type']
                elif 'alertType' in data['data']:
                    yolink.alertType = data['data']['alertType']
        else:
            yolink.alertType = None

    def getDoorBellRing(yolink):
        logging.debug('getDoorBellRing')
        if yolink.alertType == None:
            return (False)
        else:
            return(yolink.alertType =='DoorBell' or yolink.alertType =='bell')


    def getDoorState(yolink):
        logging.debug('getDoorState')
        return(yolink.getStateValue('door'))

    def setState(yolink, state):
        logging.debug(yolink.type + ' - setState')
        lock_st = str(state)
        #yolink.online = yolink.getOnlineStatus()
        if yolink.online:

            if lock_st.lower() == 'lock':
                state = 'lock'
            if state.lower() == 'unlock':
                state = 'unlock'
            if yolink.lock_type == 'LockV2':
                data = {}
                data['params'] = {}
                data['params']['state'] = {}
                data['params']['state']['lock'] = state.lower()
            else:
                data = {}
                data['params'] = {}
                data['params']['state'] = state.lower()
        return(yolink.setDevice( data))

    

    def getState(yolink):
        logging.debug(yolink.type+' - getState')
        logging.debug(f'yolink.data {yolink.data}')
        #yolink.online = yolink.getOnlineStatus()
        if yolink.online:       
            if yolink.lock_type == 'LockV2':
                lock_state = yolink.get_data('lock', 'state')
                if lock_state == 'locked':
                    return('LOCK')
                elif lock_state == 'unlocked':
                    return('UNLOCK')
                else:
                    return('Unkown')              
            else:
                lock_state = yolink.get_data('state')
                if lock_state == 'locked':
                    return('LOCK')
                elif lock_state == 'unlocked':
                    return('UNLOCK')
                else:
                    return('Unkown')   
        else:
            return('Unkown')


    def fetchState(yolink):
        logging.debug(yolink.type+' - fetchState')
        #yolink.online = yolink.getOnlineStatus()
        yolink.getState()
    
    
