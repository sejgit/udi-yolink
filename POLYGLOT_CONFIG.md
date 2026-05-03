# udi-yolink
    Support for YoLink devices.
    
## Yolink Node server
    Current list of devices supported is as follows:

    'Switch', 'THSensor', 'MultiOutlet', 'DoorSensor','Manipulator', 
    'MotionSensor', 'Outlet', 'GarageDoor', 'LeakSensor', 'Hub', 
    'SpeakerHub', 'VibrationSensor', 'Finger', 'Lock' , 'LockV2', 'Dimmer', 'InfraredRemoter',
    'PowerFailureAlarm', 'SmartRemoter', 'COSmokeSensor', 'Siren', 'WaterMeterController',
    'WaterDepthSensor', 'WaterMeterMultiController', 'SprinklerV2', 'Thermostat',
    'SoilThcSensor'


    Code uses MQTT communications.
    ###SHORT POLL sends a heartbeat to the ISY - default is 60 seconds.
    ###LONG POLL checks the online state of the devices (if a device goes offline, it will not be detected until this is called - for battery-operated devices it may take even longer, as data appears to be cached in the cloud - battery devices are not queried as part of the LONG POLL).
    A device will be redetected once it is back online.
    Default is 3600 (1 hour).  

    Note: if set too often, it will affect battery consumption (especially the Manipulator). If set to more than 2 hours, the token will expire (but a new one should be obtained).


## Code
    Code uses V2 of the YoLink API - PAC/UAC authentication - the node only supports 1 home at a time. More homes can have separate PAC/UAC generated in the YoLink app.

    Coded in Python 3 - MIT license.

## Installation
    Credentials need to be added to configuration. In the YoLink app, go to Settings->Account->Advanced Settings->User Access Credentials and copy UAID and SecretKey (alternative path in the app is Profile->Advanced Settings->User Access Credentials). It is also possible to set the temp unit (C/F/K).

    Note: it is possible to create more than 1 home in the app - each home will have its own credentials. If more than one home is to be supported, a separate node server must be used for each home.

    Enter both UAID and SecretKey under YoLink node (PG3) configuration in the browser (scroll down to see fields), then restart. Sometimes it seems to require 2 restarts to fully get all devices synchronized (I have looked but cannot find a pattern). Note: if devices are offline when restarting, they will get removed (they will stay if offline during normal operation).

    SpeakerHub requires the desired sentences to be input in config (up to 10 are supported). You will need to reboot the ISY after running the node server for this to take effect (there is no way to update these while ISY is running).

## Notes 
    
    Remaining delay time shown in ISY is estimated - countdown is running on the node server, not the device.
    Schedules are not supported (you can use ISY for the same purpose, and the YoLink app can be used to set schedules).
    The latest version of the node reports the latest report time for each device - the AC home automation will get a time.now() option so seconds between the two can be used in conditions.
    