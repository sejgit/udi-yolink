#!/usr/bin/env python3
import ast
import time
import pytz
import json
import requests
import threading
#from logger import getLogger
from yolink_devices import YoLinkDevice
#from yolink_mqtt_client import YoLinkMQTTClient
from yolinkMultiOutlet import YoLinkMultiOutlet
from yolinkTHsensor import YoLinkTHSensor
from yolinkLeakSensor import YoLinkLeakSensor
from yolinkManipulator import YoLinkManipulator
from yolinkSwitch import YoLinkSwitchSA
from yolinkSwitch import YoLinkSwitchCB
from yolinkGarageDoorToggle import YoLinkGarageDoorToggle
from yolinkGarageDoorSensor import YoLinkGarageDoorSensor
from yolinkMotionSensor import YoLinkMotionSensor
from yolinkOutlet import YoLinkOutlet
from yolinkDoorSensor import YoLinkDoorSensor
#import yolinkSwitch
from cryptography.fernet import Fernet
#from yolink_mqtt_device import YoLinkGarageDoor
#from oauthlib.oauth2 import BackendApplicationClient
#from requests.auth import HTTPBasicAuth
#from rauth import OAuth2Service
from requests_oauthlib import OAuth2Session

'''
    CSID : 60dd7fa7960d177187c82039

    CSName : Panda88

    CSSecKey : 3f68536b695a435d8a1a376fc8254e70

    SVR_URL : https://api.yosmart.com 

    API Doc : http://www.yosmart.com/doc/lorahomeapi/#/YLAS/
'''
'''
Hub
1374B849C6164E93989C8CFD56B00E89
Garage relay
D36C052E35BC4B62A409B200EB3CB0A5
Garage sensor
43B25F8585AE45D89300FFE08CFE2C52
Motion sensor
A69DA7A252D74CFDA1E7CEF416245B98



    
# decrypt the file
decrypt_file = fernet.decrypt(file)
# open the file and wite the encrypted data
with open('test.txt', 'wb') as decrypted_file:
    decrypted_file.write(decrypt_file)
print('File is decrypted')
'''
# read the key
with open('file_key.key', 'rb') as filekey:
    key = filekey.read()
# crate instance of Fernet
# with encryption key
fernet = Fernet(key)
# read the file to decrypt
with open('yolinkDeviceList.txt', 'rb') as f:
    file = f.read()
devfile = fernet.decrypt(file)
devstr = devfile.decode('utf-8')
InstalledDevices = ast.literal_eval(devstr)
yolinkURL =  'https://api.yosmart.com/openApi' 
mqttURL = 'api.yosmart.com'
csid = '60dd7fa7960d177187c82039'
csseckey = '3f68536b695a435d8a1a376fc8254e70'
csName = 'Panda88'

DeviceList = InstalledDevices['data']['list']
HubUS = DeviceList[17] 
HubDS = DeviceList[16] 
WineCoolerTemp =DeviceList[15] 
OutdoorTemp = DeviceList[14]
PoolLevel = DeviceList[13]
GarageSensor = DeviceList[12]
GarageCTRL =DeviceList[11]
USB_Outlet = DeviceList[10]
Playground = DeviceList[9]
GardenPlayground = DeviceList[8]
DoorSensor = DeviceList[7]
DeckLight = DeviceList[6]
PoolTemp = DeviceList[5]
MultiOUtlet2 = DeviceList[4]
MotionSensor1 = DeviceList[3]
Irrigation = DeviceList[2]
HouseValve = DeviceList[1]
FishTank = DeviceList[0]
def test(self):
    print('testing 123 ')

#FishMultiOutput = YoLinkMultiOutlet(csName, csid, csseckey, FishTank)
#MultiOutput = YoLinkMultiOutlet(csName, csid, csseckey, MultiOUtlet2)
#WineCellarTemp =  YoLinkTHSensor(csName, csid, csseckey, WineCoolerTemp)
#PoolTemp =  YoLinkTHSensor(csName, csid, csseckey, PoolTemp)
#WaterLevel = YoLinkWaterSensor(csName, csid, csseckey, PoolLevel)
#GarageController = YoLinkGarageDoorToggle(csName, csid, csseckey, GarageCTRL)
#GarageSensor = YoLinkGarageDoorSensor(csName, csid, csseckey, GarageSensor)
#MotionSensor = YoLinkMotionSensor(csName, csid, csseckey, MotionSensor1 )
#IrrigationValve = YoLinkManipulator(csName, csid, csseckey, Irrigation )
#HouseValve = YoLinkManipulator(csName, csid, csseckey, HouseValve )
#DeckLight = YoLinkMultiOutlet(csName, csid, csseckey, DeckLight)
#PlaygroundGardenLight = YoLinkSwitch(csName, csid, csseckey, GardenPlayground)
PlaygroundLight = YoLinkSwitchCB(csName, csid, csseckey, Playground, test)
#USB_Outlet = YoLinkOutlet(csName, csid, csseckey, USB_Outlet)
#doorSensor = YoLinkDoorSensor(csName, csid, csseckey, DoorSensor)
#outdoorTemp = YoLinkTHSensor(csName, csid, csseckey, OutdoorTemp)

#print(MultiOutput.getStateValue())
#print(MultiOutput.getSchedules())
#print(MultiOutput.getDelays())
#print(MultiOutput.getStatus())
#print(MultiOutput.getInfoAll())
#print(MultiOutput.getInfoAPI())

#MultiOutput.setState([1, 0], 'ON')
#MultiOutput.setState([0], 'off')
#print(MultiOutput.getInfoAPI())
#MultiOutput.refreshMultiOutput()
#print(MultiOutput.getInfoAPI())
#MultiOutput.refreshSchedules()

#print(MultiOutput.getInfoAPI())
#MultiOutput.refreshFWversion()
#WineCellarTemp.refreshSensor()
'''
PoolTemp.refreshSensor()
print(str(PoolTemp.getTempValue())  )
print(str(PoolTemp.getHumidityValue() ))
print(str(PoolTemp.getAlarms()))
print()
print(str(PoolTemp.sensorOnline()))
print()
info = PoolTemp.getInfoAPI()
print()
PoolTemp.eventPending()

WineCellarTemp.refreshSensor()
print(str(WineCellarTemp.getTempValue()))
print(str(WineCellarTemp.getHumidityValue()))
print(str(WineCellarTemp.getAlarms()))
print()
print(str(WineCellarTemp.eventPending()))
print()
print(str(WineCellarTemp.sensorOnline()))
print()
info = WineCellarTemp.getInfoAPI()

WaterLevel.refreshSensor()
print(str(WaterLevel.probeState() ))
print(str(WaterLevel.eventPending()))
print()
print(str(WaterLevel.sensorOnline()))
print()
info = WaterLevel.getInfoAPI()
'''
while True :
    #print(MultiOutput.getMultiOutletState())
    #print(MultiOutput.getSchedules())
    #print(MultiOutput.getDelays())
 #
    #print(MultiOutput.getInfoAll())
    #print(MultiOutput.getInfoAPI())

    #MultiOutput.setMultiOutletState([1, 0], 'ON')
    #MultiOutput.setMultiOutletState([0], 'off')
    #MultiOutput.getMultiOutletData()
    #print(MultiOutput.getInfoAPI())
    #MultiOutput.refreshMultiOutlet()
    #print(MultiOutput.getInfoAPI())
    #MultiOutput.refreshSchedules()

    #print(MultiOutput.getInfoAPI())
    
    #oTest1 = USB_Outlet.refreshState()
    #input('press enter')
    #oTest2 = USB_Outlet.getState()
    #while USB_Outlet.eventPending():
    #   print('USB_outlet event: ' + USB_Outlet.getEvent())
    #input('press enter')
    swTest1 = PlaygroundLight.refreshState()
    #input('press enter')
    swTest2 = PlaygroundLight.getState()
    while PlaygroundLight.eventPending():
        print('PlaygroundLight event: ' + PlaygroundLight.getEvent())
    #input('press enter')

    #gtest = GarageController.toggleDevice()

    #mtest = MotionSensor.motionState()
    #mtest2 = MotionSensor.motionData()
    #while MotionSensor.eventPending():
    #    print('MotionSensor event: ' + MotionSensor.getEvent())

    #swTest3 = PlaygroundLight.getSchedules()
    #input('press enter')
    #swTest4 = PlaygroundLight.setDelay([{'delayOn':1, 'delayOff':2}])
    #input('press enter')
    #swTest5 = PlaygroundLight.setState('ON')
    #input('press enter')
    #swTest6 = PlaygroundLight.getState()
    #input('press enter')
    #swTest7 = PlaygroundLight.getEnergy()
    #input('press enter')
    #swTest8 = PlaygroundLight.getInfoAPI()

    #sch1indx = PlaygroundLight.addSchedule({'week':['mon','wed', 'fri'], 'on':'16:30', 'off':'17:30','isValid':False })
    #sch2indx =PlaygroundLight.addSchedule({'week':['thu','tue', 'sun'], 'on':'16:31', 'off':'17:30','isValid':False})
    #sch3indx = PlaygroundLight.addSchedule({'week':['mon','wed', 'sat'], 'on':'16:32', 'off':'17:00','isValid':False})
    #print (IrrigationValve.scheduleList)
    #test = PlaygroundLight.activateSchedules(sch3indx, True)

    #test = PlaygroundLight.deleteSchedule(sch2indx)
    #sch2 =PlaygroundLight.addSchedule({'week':['thu','tue', 'sun'], 'off':'17:30','isValid':True })
    #swTest3 = PlaygroundLight.getSchedules()
    #test = PlaygroundLight.setSchedules()
    '''
    iTest1 = IrrigationValve.refreshState()
    iTest2 = IrrigationValve.getState()
    iTmp = IrrigationValve.refreshSchedules() 
    #iTest3 = IrrigationValve.refreshDelays() 
  
    iDel2 = MultiOutput.setDelay([{'OnDelay':2, 'OffDelay':1}])
    iDel3 = MultiOutput.setDelay()
    #IrrigationValve.refreshFWversion()
    
    mTest = MultiOutput.refreshMultiOutlet()
    mState = MultiOutput.getMultiOutletState()
    mSchedules = MultiOutput.getSchedules()
    mDelays = MultiOutput.getDelays()
    mRes1 = MultiOutput.setMultiOutletState([0, 1], 'ON')
    mRes2 = MultiOutput.setMultiOutletState([1], 'CLOSED')
    mDel1 = MultiOutput.resetDelayList()
    mDel2 = MultiOutput.appendDelay({'port':0,'OnDelay':2, 'OffDelay':1})
    mDel3 = MultiOutput.setDelay()
    mTmp = MultiOutput.getInfoAPI()
    #print(MultiOutput.getInfoAPI())
    #MotionSensor.refreshSensor()
    #print(str(MotionSensor.motionState() ))
    #print(str(MotionSensor.getMotionData()))

    #print(str(MotionSensor.eventPending()))
    #if MotionSensor.eventPending():
    #    print('Motion Event:')
    #    print(str(MotionSensor.extractEventData()))
    #print()
    #print(str(MotionSensor.sensorOnline()))
    print()
    #info = MotionSensor.getInfoAPI()
    '''
    time.sleep(10)

#print(PoolTemp.getInfoAll())
#print(PoolTemp.getTemp())
#print(PoolTemp.getHumidity())
#print(PoolTemp.getState())
'''

GarageController.toggleGarageDoorCtrl()


GarageSensor.refreshGarageDoorSensor()
print(str(GarageSensor.DoorState() ))
print(str(GarageSensor.sensorOnline()))
print()
print(str(GarageSensor.eventPending()))
print()
info = GarageSensor.getInfoAPI()

#GarageSensor.refreshGarageDoorSensor()

WaterLevel.refreshSensor()
print(str(WaterLevel.probeState() ))
print(str(WaterLevel.eventPending()))
print()
print(str(WaterLevel.sensorOnline()))
print()
info = WaterLevel.getInfoAPI()


MotionSensor.refreshSensor()
print(str(MotionSensor.motionState() ))
print(str(MotionSensor.getMotionData()))
print()
print(str(MotionSensor.eventPending()))
print()
print(str(MotionSensor.sensorOnline()))
print()
info = MotionSensor.getInfoAPI()

'''

'''
IrrigationValve.refreshState()
IrrigationValve.refreshSchedules()
#IrrigationValve.refreshFWversion()

IrrigationValve.resetSchedules()
sch1 = IrrigationValve.addSchedule({'days':['mon','wed', 'fri'], 'onTime':'16:30', 'offTime':'17:30','isValid':'Disabled' })
sch2 =IrrigationValve.addSchedule({'days':['thu','tue', 'sun'], 'onTime':'16:31', 'offTime':'17:30','isValid':'Disabled' })
sch3 = IrrigationValve.addSchedule({'days':['mon','wed', 'sat'], 'onTime':'16:32', 'offTime':'17:00','isValid':'Disabled' })
#print (IrrigationValve.scheduleList)
test = IrrigationValve.activateSchedules(sch3, True)
#print (IrrigationValve.scheduleList)
#test = IrrigationValve.deleteSchedule(sch2)
print (IrrigationValve.scheduleList)
sch2 =IrrigationValve.addSchedule({'days':['thu','tue', 'sun'], 'offTime':'17:30','isValid':'Enabled' })

test = IrrigationValve.transferSchedules()
IrrigationValve.refreshState()
IrrigationValve.refreshSchedules()
IrrigationValve.refreshFWversion()

#WaterLevel.refreshSensor()

#print(str(WaterLevel.getState())  )
#print(str(WaterLevel.getInfoAll()) )
#print(str(WaterLevel.getTimeSinceUpdate())+'\n')

IrrigationValve.refreshState()


'''
while True :
    time.sleep(10)
print('end')

yolink_client.shurt_down()
