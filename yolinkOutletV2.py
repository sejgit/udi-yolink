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


class YoLinkOutlet(YoLinkMQTTDevice):
    def __init__(yolink, yoAccess,  deviceInfo, callback):
        super().__init__(yoAccess,  deviceInfo, callback)
        
        #yolink.methodList = ['getState', 'setState', 'setDelay', 'getSchedules', 'setSchedules', 'getUpdate'   ]
        #yolink.eventList = ['StatusChange', 'Report', 'getState']
        #yolink.stateList = ['open', 'closed', 'on', 'off']
        #yolink.ManipulatorName = 'OutletEvent'
        #yolink.eventTime = 'Time'
        yolink.type = deviceInfo['type']
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
    
    def updateStatus(self, data):
        self.updateCallbackStatus(data, False)

    def setState(yolink, state):
        logging.debug(yolink.type + ' - setState + {}'.format(state))
        outlet = str(state)
        #yolink.online = yolink.getOnlineStatus()
        if yolink.online:
            if outlet.lower() in [ 'on', 'open']:
                state = 'open'
            if state.lower() in ['off', 'closed']:
                state = 'closed'
            data = {}
            data['params'] = {}
            data['params']['state'] = state.lower()
            return(yolink.setDevice( data))
    

    def getState(yolink):
        
        dev_state = 'Unknown'
        #yolink.online = yolink.getOnlineStatus()
        try:
            state_data = yolink.get_data('state')
            logging.debug(yolink.type+' - getState data {}'.format(state_data))
            state_val = None
            if isinstance(state_data, dict):
                state_val = state_data.get('state')
            elif isinstance(state_data, str):
                state_val = state_data

            if state_val == 'open':
                dev_state = 'ON'
            elif state_val == 'closed':
                dev_state = 'OFF'
            else:
                dev_state = 'Unknown'
            logging.debug(yolink.type+' - getState - return {} '.format(dev_state))
            return(dev_state)
        except Exception as e:
            logging.error('Exception - {} - {} '.format(yolink.type+' - getState' , e))
            return ('Unknown')
        
        
    def getEnergy(yolink):
        logging.debug(yolink.type+' - getEnergy : ')

        #yolink.online = yolink.getOnlineStatus()
        if yolink.online:   
            try:
                power = yolink.get_data('power')
                watt = yolink.get_data('watt')
                if power is None and watt is None:
                    return(None)
                return({'power': power, 'watt': watt})
            except:
                return(None)
    
    
