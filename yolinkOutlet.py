import json
import time
import logging

from yolink_mqtt_class import YoLinkMQTTDevice
logging.basicConfig(level=logging.DEBUG)


class YoLinkOutlet(YoLinkMQTTDevice):
    def __init__(yolink, csName, csid, csseckey, deviceInfo, yolink_URL ='https://api.yosmart.com/openApi' , mqtt_URL= 'api.yosmart.com', mqtt_port = 8003):
        super().__init__( csName, csid, csseckey, yolink_URL, mqtt_URL, mqtt_port, deviceInfo, yolink.updateStatus)
        
        yolink.methodList = ['getState', 'setState', 'setDelay', 'getSchedules', 'setSchedules', 'getUpdate'   ]
        yolink.eventList = ['StatusChange', 'Report', 'getState']
        yolink.stateList = ['open', 'closed', 'on', 'off']
        yolink.ManipulatorName = 'ManipulatorEvent'
        yolink.eventTime = 'Time'
        yolink.type = 'Outlet'
        time.sleep(2)
        
        yolink.refreshState()
        #input()
        yolink.refreshSchedules()
        #yolink.refreshFWversion()


 
    def setState(yolink, state):
        logging.debug(yolink.type + ' - setState')

        if 'setState'  in yolink.methodList:          
            if state.lower() not in yolink.stateList:
                logging.error('Unknows state passed')
                return(False)
            if state.lower() == 'on':
                state = 'open'
            if state.lower() == 'off':
                state = 'closed'
            data = {}
            data['params'] = {}
            data['params']['state'] = state.lower()
            return(yolink.setDevice( data))
        else:
            return(False)
    

    def getState(yolink):
        logging.debug(yolink.type+' - getState')
        attempts = 0
        while yolink.dataAPI[yolink.dData][yolink.dState]  == {} and attempts < 5:
            time.sleep(1)
            attempts = attempts + 1
        if attempts <= 5:
            if  yolink.dataAPI[yolink.dData][yolink.dState]['state'] == 'open':
                return('ON')
            elif yolink.dataAPI[yolink.dData][yolink.dState]['state'] == 'closed':
                return('OFF')
            else:
                return('Unkown')
        else:
            return('Unkown')
    '''
    def getEnergy(yolink):
        logging.debug(yolink.type+' - getEnergy')
        return({'power':yolink.dataAPI[yolink.dData][yolink.dState]['power'], 'watt':yolink.dataAPI[yolink.dData][yolink.dState]['power']})
    '''