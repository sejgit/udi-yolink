#!/usr/bin/env python3
"""
Polyglot v3 node server for YoLink Thermostat

Supports Thermostat.getState, setState, setECO, setProperties, setCorrection
MIT License
"""

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)

import time
from yolinkThermostatV2 import YoLinkThermostat


class udiYoThermostat(udi_interface.Node):
    from udiYolinkLib import my_setDriver, node_queue, wait_for_node_done

    id = 'yothermostat'

    drivers = [
        {'driver': 'ST', 'value': 99, 'uom': 66},         # Running state (UoM 66: 0=Idle, 1=Heating, 2=Cooling)
        {'driver': 'CLITEMP', 'value': 0, 'uom': 4},      # Current temperature (UoM 4=Celsius, 17=Fahrenheit)
        {'driver': 'CLIHUM', 'value': 0, 'uom': 51},      # Current humidity (UoM 51=percent)
        {'driver': 'CLISPH', 'value': 0, 'uom': 4},       # Heat setpoint (UoM 4=Celsius, 17=Fahrenheit)
        {'driver': 'CLISPC', 'value': 0, 'uom': 4},       # Cool setpoint (UoM 4=Celsius, 17=Fahrenheit)
        {'driver': 'CLIMD', 'value': 99, 'uom': 67},      # Thermostat mode (UoM 67: 0=Off, 1=Heat, 2=Cool, 3=Auto)
        {'driver': 'CLIFS', 'value': 99, 'uom': 68},      # Fan setting (UoM 68: 0=Auto, 1=On)
        {'driver': 'CLISMD', 'value': 99, 'uom': 25},     # Schedule mode (UoM 25: 0=run, 1=hold)
        {'driver': 'CLIHCS', 'value': 99, 'uom': 66},     # Heat/Cool state (UoM 66: 0=Idle, 1=Heating, 2=Cooling)
        {'driver': 'CLIFRS', 'value': 99, 'uom': 80},     # Fan running state (UoM 80: 0=Off, 1=On)
        {'driver': 'GV0', 'value': 99, 'uom': 4},         # Sensor 1 temp (optional, UoM 4=C)
        {'driver': 'GV1', 'value': 99, 'uom': 4},         # Sensor 2 temp (optional, UoM 4=C)
        {'driver': 'GV2', 'value': 99, 'uom': 25},        # Aux heat running (UoM 25: 0=no, 1=yes)
        {'driver': 'GV3', 'value': 99, 'uom': 25},        # Second stage running (UoM 25: 0=no, 1=yes)
        {'driver': 'GV4', 'value': 99, 'uom': 25},        # ECO mode (UoM 25: 0=off, 1=on)
        {'driver': 'GV5', 'value': 99, 'uom': 25},        # DR running (UoM 25: 0=no, 1=yes)
        {'driver': 'GV6', 'value': 99, 'uom': 44},        # minRuntime (minutes)
        {'driver': 'GV7', 'value': 99, 'uom': 4},         # coolLimit (Celsius)
        {'driver': 'GV8', 'value': 99, 'uom': 4},         # heatLimit (Celsius)
        {'driver': 'GV9', 'value': 99, 'uom': 25},        # mute (0=no, 1=yes)
        {'driver': 'GV10', 'value': 99, 'uom': 25},       # menuLock (0=no, 1=yes)
        {'driver': 'GV11', 'value': 99, 'uom': 44},       # auxStandby (minutes)
        {'driver': 'GV12', 'value': 99, 'uom': 20},       # auxMaxSpan (hours)
        {'driver': 'GV13', 'value': 99, 'uom': 4},        # auxThreshold (Celsius)
        {'driver': 'GV14', 'value': 99, 'uom': 44},       # stage2Standby (minutes)
        {'driver': 'GV15', 'value': 99, 'uom': 20},       # stage2MaxSpan (hours)
        {'driver': 'GV16', 'value': 99, 'uom': 4},        # stage2Threshold (Celsius)
        {'driver': 'GV17', 'value': 99, 'uom': 25},       # master temp source (0=local, 1=sensor1, 2=sensor2)
        {'driver': 'GV20', 'value': 99, 'uom': 25},       # Suspended state (UoM 25: 0=not suspended, 1=suspended, 2=error)
        {'driver': 'GV30', 'value': 99, 'uom': 25},       # Online status (UoM 25: 0=offline, 1=online)
        {'driver': 'TIME', 'value': int(time.time()), 'uom': 151},  # Last update time (UoM 151=Unix Timestamp)
    ]

    def __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__(polyglot, primary, address, name)
        logging.debug(f'udiYoThermostat INIT - {deviceInfo["name"]}')
        
        self.poly = polyglot
        self.address = address
        self.name = name
        self.yoAccess = yoAccess
        self.devInfo = deviceInfo
        self.yoThermostat = None
        self.node_ready = False
        self.system_ready = False
        self.temp_unit = self.yoAccess.get_temp_unit()
        self.n_queue = []

        # Set node ID based on temperature unit
        if self.temp_unit == 1:
            self.id = 'yothermostatf'  # Fahrenheit variant
        else:
            self.id = 'yothermostat'   # Celsius variant (default)

        # Subscribe to events
        polyglot.subscribe(polyglot.START, self.start, self.address)
        polyglot.subscribe(polyglot.STOP, self.stop)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)

        # Add node and wait
        polyglot.ready()
        self.poly.addNode(self, conn_status=None, rename=True)
        self.wait_for_node_done()

        self.node = self.poly.getNode(address)
        self.adr_list = [address]
        self.node_ready = True

    def start(self):
        """Initialize and start the thermostat device"""
        logging.info('Start udiYoThermostat')
        while not self.node_ready:
            time.sleep(0.5)
        self.my_setDriver('GV30', 0)
        self.yoThermostat = YoLinkThermostat(self.yoAccess, self.devInfo, self.updateStatus)
        time.sleep(1)
        self.yoThermostat.initDevice()
        tries = 1
        while not self.yoThermostat.check_system_online() and tries <= 5:
            logging.info('Waiting for thermostat to come online...')
            time.sleep(2)
            tries += 1
        self.system_ready = True
        logging.info('Thermostat online and ready')

    def stop(self):
        """Stop the thermostat device"""
        logging.info('Stop udiYoThermostat')
        self.my_setDriver('GV30', 0)
        if self.yoThermostat:
            self.yoThermostat.shut_down()

    def updateStatus(self, data):
        """Handle MQTT status updates from the device"""
        logging.debug('udiYoThermostat - updateStatus')
        if self.yoThermostat:
            self.yoThermostat.updateStatus(data)
            self.updateData()

    def updateData(self):
        """Parse device state and update drivers"""
        logging.info('udiYoThermostat - updateData')
        if self.node is not None:
            while not self.node_ready or not self.system_ready:
                time.sleep(0.5)
            
            message_type, message_action = self.yoThermostat.get_message_type()
            
            # Update timestamp
            unix_time = self.yoThermostat.get_report_time('time')
            self.my_setDriver('TIME', unix_time, 151)
            
            if self.yoThermostat.check_system_online():
                self.my_setDriver('GV30', 1)
                
                # Current readings from state
                currentTemp = self.yoThermostat.get_data('temperature', 'state')
                humidity = self.yoThermostat.get_data('humidity', 'state')
                
                # Setpoints
                lowTemp = self.yoThermostat.get_data('lowTemp', 'state')
                highTemp = self.yoThermostat.get_data('highTemp', 'state')
                
                # Operating mode
                mode = self.yoThermostat.get_data('mode', 'state')
                fan = self.yoThermostat.get_data('fan', 'state')
                sche = self.yoThermostat.get_data('sche', 'state')
                running = self.yoThermostat.get_data('running', 'state')
                fanRunning = self.yoThermostat.get_data('fanRunning', 'state')

                # Sensors (optional)
                sensor1 = self.yoThermostat.get_data('sensor1', 'state')
                sensor2 = self.yoThermostat.get_data('sensor2', 'state')

                # Optional states in 'other'
                auxHeat = self.yoThermostat.get_data('auxiliaryHeat', ('state', 'other'))
                stage2 = self.yoThermostat.get_data('secondStage', ('state', 'other'))
                drRunning = self.yoThermostat.get_data('drRunning', ('state', 'other'))

                # Eco mode
                eco = self.yoThermostat.get_data('eco')

                # Current temperature
                if isinstance(currentTemp, (int, float)):
                    if self.temp_unit == 1:  # Fahrenheit
                        self.my_setDriver('CLITEMP', round(currentTemp * 9/5 + 32, 1), 17, type=message_type)
                    else:
                        self.my_setDriver('CLITEMP', round(currentTemp, 1), 4, type=message_type)

                # Humidity
                if isinstance(humidity, (int, float)):
                    self.my_setDriver('CLIHUM', round(humidity, 1), 51, type=message_type)

                # Heat setpoint (low temp = heat setpoint)
                if isinstance(lowTemp, (int, float)):
                    if self.temp_unit == 1:
                        self.my_setDriver('CLISPH', round(lowTemp * 9/5 + 32, 1), 17, type=message_type)
                    else:
                        self.my_setDriver('CLISPH', round(lowTemp, 1), 4, type=message_type)

                # Cool setpoint (high temp = cool setpoint)
                if isinstance(highTemp, (int, float)):
                    if self.temp_unit == 1:
                        self.my_setDriver('CLISPC', round(highTemp * 9/5 + 32, 1), 17, type=message_type)
                    else:
                        self.my_setDriver('CLISPC', round(highTemp, 1), 4, type=message_type)

                # Mode: UoM 67: 0=Off, 1=Heat, 2=Cool, 3=Auto
                if mode:
                    mode_map = {'off': 0, 'heat': 1, 'cool': 2, 'auto': 3}
                    self.my_setDriver('CLIMD', mode_map.get(mode.lower(), 99), 67, type=message_type)

                # Fan setting: UoM 68: 0=Auto, 1=On
                if fan:
                    fan_map = {'auto': 0, 'on': 1}
                    self.my_setDriver('CLIFS', fan_map.get(fan.lower(), 99), 68, type=message_type)

                # Schedule mode: 0=run, 1=hold
                if sche:
                    sche_map = {'run': 0, 'hold': 1}
                    self.my_setDriver('CLISMD', sche_map.get(sche.lower(), 99), 25, type=message_type)

                # Running state: UoM 66: 0=Idle, 1=Heating, 2=Cooling
                if running:
                    running_map = {'idle': 0, 'heat': 1, 'cool': 2}
                    self.my_setDriver('CLIHCS', running_map.get(running.lower(), 99), 66, type=message_type)
                    self.my_setDriver('ST', running_map.get(running.lower(), 99), 66, type=message_type)

                # Fan running state: UoM 80: 0=Off, 1=On
                if fanRunning is not None:
                    fan_running_map = {'off': 0, 'on': 1}
                    if isinstance(fanRunning, str):
                        self.my_setDriver('CLIFRS', fan_running_map.get(fanRunning.lower(), 99), 80, type=message_type)
                    else:
                        self.my_setDriver('CLIFRS', 1 if fanRunning else 0, 80, type=message_type)

                # Optional sensors
                if isinstance(sensor1, (int, float)):
                    if self.temp_unit == 1:
                        self.my_setDriver('GV0', round(sensor1 * 9/5 + 32, 1), 17, type=message_type)
                    else:
                        self.my_setDriver('GV0', round(sensor1, 1), 4, type=message_type)

                if isinstance(sensor2, (int, float)):
                    if self.temp_unit == 1:
                        self.my_setDriver('GV1', round(sensor2 * 9/5 + 32, 1), 17, type=message_type)
                    else:
                        self.my_setDriver('GV1', round(sensor2, 1), 4, type=message_type)

                # Optional other states (UoM 25 = index)
                if auxHeat is not None:
                    self.my_setDriver('GV2', 1 if auxHeat else 0, 25, type=message_type)
                if stage2 is not None:
                    self.my_setDriver('GV3', 1 if stage2 else 0, 25, type=message_type)

                # ECO mode (UoM 25 = index)
                if eco and isinstance(eco, dict):
                    eco_mode = eco.get('mode', 'off')
                    self.my_setDriver('GV4', 1 if eco_mode.lower() == 'on' else 0, 25, type=message_type)

                # DR running state (UoM 25: 0=no, 1=yes)
                if drRunning is not None:
                    self.my_setDriver('GV5', 1 if drRunning else 0, 25, type=message_type)

                # Properties
                properties = self.yoThermostat.get_data('properties')
                if properties and isinstance(properties, dict):
                    minRuntime = properties.get('minRuntime')
                    if isinstance(minRuntime, (int, float)):
                        self.my_setDriver('GV6', int(minRuntime), 44, type=message_type)
                    
                    coolLimit = properties.get('coolLimit')
                    if isinstance(coolLimit, (int, float)):
                        if self.temp_unit == 1:
                            self.my_setDriver('GV7', round(coolLimit * 9/5 + 32, 1), 17, type=message_type)
                        else:
                            self.my_setDriver('GV7', round(coolLimit, 1), 4, type=message_type)
                    
                    heatLimit = properties.get('heatLimit')
                    if isinstance(heatLimit, (int, float)):
                        if self.temp_unit == 1:
                            self.my_setDriver('GV8', round(heatLimit * 9/5 + 32, 1), 17, type=message_type)
                        else:
                            self.my_setDriver('GV8', round(heatLimit, 1), 4, type=message_type)
                    
                    mute = properties.get('mute')
                    if mute is not None:
                        self.my_setDriver('GV9', 1 if mute else 0, 25, type=message_type)
                    
                    menuLock = properties.get('menuLock')
                    if menuLock is not None:
                        self.my_setDriver('GV10', 1 if menuLock else 0, 25, type=message_type)
                    
                    auxStandby = properties.get('auxStandby')
                    if isinstance(auxStandby, (int, float)):
                        self.my_setDriver('GV11', int(auxStandby), 44, type=message_type)
                    
                    auxMaxSpan = properties.get('auxMaxSpan')
                    if isinstance(auxMaxSpan, (int, float)):
                        self.my_setDriver('GV12', int(auxMaxSpan), 20, type=message_type)
                    
                    auxThreshold = properties.get('auxThreshold')
                    if isinstance(auxThreshold, (int, float)):
                        if self.temp_unit == 1:
                            self.my_setDriver('GV13', round(auxThreshold * 9/5 + 32, 1), 17, type=message_type)
                        else:
                            self.my_setDriver('GV13', round(auxThreshold, 1), 4, type=message_type)
                    
                    stage2Standby = properties.get('stage2Standby')
                    if isinstance(stage2Standby, (int, float)):
                        self.my_setDriver('GV14', int(stage2Standby), 44, type=message_type)
                    
                    stage2MaxSpan = properties.get('stage2MaxSpan')
                    if isinstance(stage2MaxSpan, (int, float)):
                        self.my_setDriver('GV15', int(stage2MaxSpan), 20, type=message_type)
                    
                    stage2Threshold = properties.get('stage2Threshold')
                    if isinstance(stage2Threshold, (int, float)):
                        if self.temp_unit == 1:
                            self.my_setDriver('GV16', round(stage2Threshold * 9/5 + 32, 1), 17, type=message_type)
                        else:
                            self.my_setDriver('GV16', round(stage2Threshold, 1), 4, type=message_type)
                    
                    master = properties.get('master')
                    if master:
                        master_map = {'local': 0, 'sensor1': 1, 'sensor2': 2}
                        self.my_setDriver('GV17', master_map.get(master.lower(), 99), 25, type=message_type)

                # Suspended state check
                if self.yoThermostat.suspended:
                    self.my_setDriver('GV20', 1)
                else:
                    self.my_setDriver('GV20', 0)
            else:
                self.my_setDriver('GV30', 0)
                self.my_setDriver('GV20', 2)

    def update(self, command=None):
        """Refresh device state"""
        logging.info('udiYoThermostat update')
        if self.yoThermostat:
            self.yoThermostat.refreshDevice()

    def setLowTemp(self, command):
        """Set low temperature setpoint"""
        try:
            temp = float(command.get('value'))
            # Convert from Fahrenheit to Celsius if needed (API expects Celsius)
            if self.temp_unit == 1:
                temp_celsius = round((temp - 32) * 5/9, 1)
                logging.info(f'udiYoThermostat setLowTemp - {temp}°F ({temp_celsius}°C)')
                if self.yoThermostat:
                    self.yoThermostat.setLowTemp(temp_celsius)
            else:
                logging.info(f'udiYoThermostat setLowTemp - {temp}°C')
                if self.yoThermostat:
                    self.yoThermostat.setLowTemp(temp)
        except (ValueError, TypeError) as e:
            logging.error(f'setLowTemp invalid value: {e}')

    def setHighTemp(self, command):
        """Set high temperature setpoint"""
        try:
            temp = float(command.get('value'))
            # Convert from Fahrenheit to Celsius if needed (API expects Celsius)
            if self.temp_unit == 1:
                temp_celsius = round((temp - 32) * 5/9, 1)
                logging.info(f'udiYoThermostat setHighTemp - {temp}°F ({temp_celsius}°C)')
                if self.yoThermostat:
                    self.yoThermostat.setHighTemp(temp_celsius)
            else:
                logging.info(f'udiYoThermostat setHighTemp - {temp}°C')
                if self.yoThermostat:
                    self.yoThermostat.setHighTemp(temp)
        except (ValueError, TypeError) as e:
            logging.error(f'setHighTemp invalid value: {e}')

    def setMode(self, command):
        """Set operating mode (UoM 67: 0=Off, 1=Heat, 2=Cool, 3=Auto)"""
        try:
            mode_val = int(command.get('value'))
            mode_map = {0: 'off', 1: 'heat', 2: 'cool', 3: 'auto'}
            mode = mode_map.get(mode_val, 'off')
            logging.info(f'udiYoThermostat setMode - {mode}')
            if self.yoThermostat:
                self.yoThermostat.setMode(mode)
        except (ValueError, TypeError) as e:
            logging.error(f'setMode invalid value: {e}')

    def setFan(self, command):
        """Set fan mode (UoM 68: 0=Auto, 1=On)"""
        try:
            fan_val = int(command.get('value'))
            fan_map = {0: 'auto', 1: 'on'}
            fan = fan_map.get(fan_val, 'auto')
            logging.info(f'udiYoThermostat setFan - {fan}')
            if self.yoThermostat:
                self.yoThermostat.setFan(fan)
        except (ValueError, TypeError) as e:
            logging.error(f'setFan invalid value: {e}')

    def setScheduleMode(self, command):
        """Set schedule mode (run/hold)"""
        try:
            sche_val = int(command.get('value'))
            sche_map = {0: 'run', 1: 'hold'}
            sche = sche_map.get(sche_val, 'run')
            logging.info(f'udiYoThermostat setScheduleMode - {sche}')
            if self.yoThermostat:
                self.yoThermostat.setScheduleMode(sche)
        except (ValueError, TypeError) as e:
            logging.error(f'setScheduleMode invalid value: {e}')

    def setEco(self, command):
        """Set ECO mode (0=off, 1=on)"""
        try:
            eco_val = int(command.get('value'))
            eco_mode = 'on' if eco_val == 1 else 'off'
            logging.info(f'udiYoThermostat setEco - {eco_mode}')
            if self.yoThermostat:
                self.yoThermostat.setECO(mode=eco_mode)
        except (ValueError, TypeError) as e:
            logging.error(f'setEco invalid value: {e}')

    def setMinRuntime(self, command):
        """Set minimum runtime in minutes"""
        try:
            minutes = int(command.get('value'))
            logging.info(f'udiYoThermostat setMinRuntime - {minutes}')
            if self.yoThermostat:
                self.yoThermostat.setProperties(minRuntime=minutes)
        except (ValueError, TypeError) as e:
            logging.error(f'setMinRuntime invalid value: {e}')

    def setCoolLimit(self, command):
        """Set cool limit temperature"""
        try:
            temp = float(command.get('value'))
            if self.temp_unit == 1:
                temp_celsius = round((temp - 32) * 5/9, 1)
                logging.info(f'udiYoThermostat setCoolLimit - {temp}°F ({temp_celsius}°C)')
                if self.yoThermostat:
                    self.yoThermostat.setProperties(coolLimit=temp_celsius)
            else:
                logging.info(f'udiYoThermostat setCoolLimit - {temp}°C')
                if self.yoThermostat:
                    self.yoThermostat.setProperties(coolLimit=temp)
        except (ValueError, TypeError) as e:
            logging.error(f'setCoolLimit invalid value: {e}')

    def setHeatLimit(self, command):
        """Set heat limit temperature"""
        try:
            temp = float(command.get('value'))
            if self.temp_unit == 1:
                temp_celsius = round((temp - 32) * 5/9, 1)
                logging.info(f'udiYoThermostat setHeatLimit - {temp}°F ({temp_celsius}°C)')
                if self.yoThermostat:
                    self.yoThermostat.setProperties(heatLimit=temp_celsius)
            else:
                logging.info(f'udiYoThermostat setHeatLimit - {temp}°C')
                if self.yoThermostat:
                    self.yoThermostat.setProperties(heatLimit=temp)
        except (ValueError, TypeError) as e:
            logging.error(f'setHeatLimit invalid value: {e}')

    def setMute(self, command):
        """Set mute setting (0=off, 1=on)"""
        try:
            mute_val = int(command.get('value'))
            mute = True if mute_val == 1 else False
            logging.info(f'udiYoThermostat setMute - {mute}')
            if self.yoThermostat:
                self.yoThermostat.setProperties(mute=mute)
        except (ValueError, TypeError) as e:
            logging.error(f'setMute invalid value: {e}')

    def setMenuLock(self, command):
        """Set menu lock (0=off, 1=on)"""
        try:
            lock_val = int(command.get('value'))
            lock = True if lock_val == 1 else False
            logging.info(f'udiYoThermostat setMenuLock - {lock}')
            if self.yoThermostat:
                self.yoThermostat.setProperties(menuLock=lock)
        except (ValueError, TypeError) as e:
            logging.error(f'setMenuLock invalid value: {e}')

    def setMaster(self, command):
        """Set master temperature source (0=local, 1=sensor1, 2=sensor2)"""
        try:
            master_val = int(command.get('value'))
            master_map = {0: 'local', 1: 'sensor1', 2: 'sensor2'}
            master = master_map.get(master_val, 'local')
            logging.info(f'udiYoThermostat setMaster - {master}')
            if self.yoThermostat:
                self.yoThermostat.setProperties(master=master)
        except (ValueError, TypeError) as e:
            logging.error(f'setMaster invalid value: {e}')

    commands = {
        'UPDATE': update,
        'SETLOWTEMP': setLowTemp,
        'SETHIGHTEMP': setHighTemp,
        'SETMODE': setMode,
        'SETFAN': setFan,
        'SETSCHE': setScheduleMode,
        'SETECO': setEco,
        'SETMINRUNTIME': setMinRuntime,
        'SETCOOLLIMIT': setCoolLimit,
        'SETHEATLIMIT': setHeatLimit,
        'SETMUTE': setMute,
        'SETMENULOCK': setMenuLock,
        'SETMASTER': setMaster,
    }




