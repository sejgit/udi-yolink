# udi-yolink
    Support for YoLink devices.
    Suggested installation is on PG3x from version 1.1.x going forward. PG3x is updated to Python 3.11. It still works under PG3, but we cannot guarantee how long that will remain possible.
    
## Yolink Node server
    Enables YoLink (https://shop.yosmart.com/) devices to be controlled using the ISY.
    Current list of devices supported is as follows:
    
    'Switch', 'THSensor', 'MultiOutlet', 'DoorSensor','Manipulator', 
    'MotionSensor', 'Outlet', 'GarageDoor', 'LeakSensor', 'Hub', 
    'SpeakerHub', 'VibrationSensor', 'Finger', 'Lock' , 'LockV2', 'Dimmer', 'InfraredRemoter',
    'PowerFailureAlarm', 'SmartRemoter', 'COSmokeSensor', 'Siren', 'WaterMeterController',
    'WaterDepthSensor', 'WaterMeterMultiController', 'SprinklerV2', 'Thermostat',
    'SoilThcSensor'

    
    Code uses MQTT communications.
    ###SHORT POLL sends a heartbeat to the ISY - default is 60 seconds - It also checks whether data has been updated since the last update. This can happen when a command has a very slow reply from the cloud. The server uses separate threads for sending commands and receiving results.
    
    ###LONG POLL checks the online state of the devices (if a device goes offline, it will not be detected until this is called - for battery-operated devices it may take even longer, as data appears to be cached in the cloud - battery devices are not queried as part of the LONG POLL).
    A device will be redetected once it is back online.
    Default is 3600 (1 hour).  

    Note: if set too often, it will affect battery consumption (especially the Manipulator). If set to more than 2 hours, the token will expire (but a new one should be obtained).


## Code
    Code uses V2 of the YoLink API - PAC/UAC authentication - currently this API only supports a single home (even if the app supports more).

    Coded in Python 3 - MIT license.

## Installation
    Credentials need to be added to configuration in the YoLink node server under PG3. In the YoLink app, go to Settings->Account->Advanced Settings->User Access Credentials and copy UAID and SecretKey (alternative path in the app is Profile->Advanced Settings->User Access Credentials).
    It is possible to get credentials for each home that is defined, but the node server can only handle one of them currently.

    Enter both UAID and SecretKey under configuration in the node in PG#'s browser page (scroll down if you do not see the fields) and then restart. Sometimes it seems to require 2 restarts to fully get all devices synchronized (I have looked but cannot find a pattern).
    Sometimes a reboot of the ISY is required to make the node server show up correctly.

UAID/SecretKey
    Credentials need to be added to configuration in the YoLink node server under PG3. In the YoLink app, go to Settings->Account->Advanced Settings->User Access Credentials and copy UAID and SecretKey (alternative path in the app is Profile->Advanced Settings->User Access Credentials).
    It is possible to get credentials for each separate home defined in the YoLink app, but the node server can only handle one of them currently.
    
TEMP_UNIT
    Select F or C
     
WATER_UNIT
    Select Liter or Gallon

NBR_TTS
    Number of speakerhub Text to Speech messages to support (see below)
    

## Notes 
    One node server can only handle 1 home - you can get credentials for each home in the app by selecting the home and getting credentials - multiple credentials can exist at the same time, but the node server can only handle one.

    Remaining delay time shown in ISY is estimated - countdown is running on the node server, not the device.

    <SpeakerHub> supports up to 10 Text-to-Speech messages. You specify the number of messages desired, and then add the text of the message in TTS<n>. Restart the node server. After this, a restart of the ISY/PoI is needed to transfer the messages to the UI. The ISY/PoI only reads the file containing the messages during startup.

    In configuration, TEMP_UNIT can be used to set the temperature unit to C, F.

    YoLink schedules are now supported.
    
    Remaining delay time shown in ISY is estimated - countdown is running on the node server, not the device.
   
    
    The latest version of the node reports the latest report time for each device - the AC home automation will get a time.now() option so seconds between the two can be used in conditions.
    

    
