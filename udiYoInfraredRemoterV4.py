#!/usr/bin/env python3
"""
MIT License
"""

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)

from ctypes import set_errno
from os import truncate
import threading
#import udi_interface
#import sys
import time
from yolinkInfraredRemoterV3 import YoLinkInfraredRemoter
from udiYoSchedule import udiYoSchedule

class udiYoInfraredCode(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, node_queue, wait_for_node_done, set_node_custom, get_node_custom, checkNameSync

    '''
       drivers = [

            'GV2' = Command status
            'GV5' = Online
            ]
    ''' 
    
    id = 'yoircode'
    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 25},
            {'driver': 'GV30', 'value': 99, 'uom': 25},
            {'driver': 'GV20', 'value': 99, 'uom': 25},       
            {'driver': 'TIME', 'value' :int(time.time()), 'uom': 151},                 
            ] 
    def  __init__(self, polyglot, primary, address, name, code_indx, yoIRrem):
        logging.debug('udiIRcode'.format(code_indx))
        super().__init__( polyglot, primary, address, name)   
        self.yoIRrem = yoIRrem
        self.code = code_indx
        self.n_queue = []   
        self.poly.ready()
       
        #self.poly.subscribe(polyglot.START, self.start, self.address)
        #self.poly.subscribe(polyglot.STOP, self.stop)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)

        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        # persist current node name if not set, or restore saved name
        try:
            saved = self.get_node_custom('saved_name')
            if saved:
                saved = self.poly.getValidName(saved)
                self._name_sync_saved = saved
                self.set_node_custom('saved_name', saved)
                if self.node.name != saved:
                    try:
                        self.node.rename(saved)
                        logging.info(f'Restored node name for {self.address} to saved name {saved}')
                    except Exception as e:
                        logging.debug(f'Failed to restore node name for {self.address}: {e}')
            else:
                self.set_node_custom('saved_name', self.node.name)
                self._name_sync_saved = self.node.name
        except Exception as e:
            logging.debug(f'Error handling custom name for {self.address}: {e}')
        time.sleep(2)
        #self.updateData()


    def checkDataUpdate(self):
        if self.yoIRrem.data_updated():
            self.updateData()
            
    def checkOnline(self):
        pass  #is it a sub node - do nothing

    def updateData(self):
        if self.node is not None:
            #while not self.node_ready or not self.system_ready:
            #    time.sleep(0.5)
            #logging.debug('updateData - {}'.format(self.yoIRrem.check_system_online()))
            self.my_setDriver('TIME', self.yoIRrem.getLastUpdateTime(), 151)
            #self.my_setDriver('ST', 0)
            if self.yoIRrem.suspended:
                self.my_setDriver('GV20', 1)
            else:
                self.my_setDriver('GV20', 0)
        else:
            self.my_setDriver('GV20', 2)

    def clear_delay(self, delay=5):
        time.sleep(delay)
        self.my_setDriver('ST', 0)

    def send_IRcode(self, command=None):
        try:
            logging.info('udiIRremote send_IRcode')
            if self.yoIRrem.send_code( self.code):
                #time.sleep(0.5)
                #res = self.yoIRrem.get_send_status()
                #while res is {} and self.yoIRrem.check_system_online():
                time.sleep(1)
                #res = self.yoIRrem.get_send_status()
                #logging.debug(f'Send code {self.code} {res}')
                if self.yoIRrem.get_data('success') and self.yoIRrem.get_data('key') == self.code:
                    logging.info('Code {} sent successfully'.format(self.code))
                    self.node.reportCmd('DON')  
                    self.my_setDriver('ST', 1)
                    self.clear_delay(5)
                    return
                else:
                    logging.info('Failed to send code {}'.format(self.code))
                    self.my_setDriver('ST', 2)
                    self.clear_delay(5)
                    return
            else:
                logging.info('Failed to send code {}'.format(self.code))
                self.my_setDriver('ST', 2)
                self.clear_delay(5)
                return
        except Exception as E:
            logging.error('udiIRcode send_IRcode - Exception: {}'.format(E))        
        '''   
            if 'success' in res:
                if  res['success'] == True:
                    logging.info('Code {} sent successfully'.format(self.code))
                    self.node.reportCmd('DON')  
                    self.my_setDriver('ST', 1)
                else:
                    self.my_setDriver('ST', 0)
            else:
                self.my_setDriver('ST', 0)              
        else:
            self.my_setDriver('ST', 0)
        
        if self.yoIRrem.suspended:
            self.my_setDriver('GV20', 1)
        else:
            self.my_setDriver('GV20', 0)  
        '''
    commands = {
            'TXCODE': send_IRcode,
            }


class udiYoInfraredRemoter(udi_interface.Node):
    from  udiYolinkLib import my_setDriver, update_schedule_data, node_queue, wait_for_node_done, set_node_custom, get_node_custom, checkNameSync as sharedCheckNameSync, saveCurrentNodeNames


    '''
       drivers = [
            'GV0' = Nbr codes
            'GV1' = Battery Level
            'GV2' = Command status
            ]
    ''' 
    id = 'yoirremote'
    drivers = [
            {'driver': 'ST', 'value': 0, 'uom': 25},
            {'driver': 'GV30', 'value': 99, 'uom': 25},
            {'driver': 'GV0', 'value': 0, 'uom': 56},
            {'driver': 'GV1', 'value': 0, 'uom': 25},
            {'driver': 'GV2', 'value': 0, 'uom': 25},
            {'driver': 'GV20', 'value': 99, 'uom': 25},       
            {'driver': 'TIME', 'value' :int(time.time()), 'uom': 151},                 
            ]


    def  __init__(self, polyglot, primary, address, name, yoAccess, deviceInfo):
        super().__init__( polyglot, primary, address, name)   

        logging.debug('udiIRremote INIT- {}'.format(deviceInfo['name']))
        self.name = name

        self.yoAccess = yoAccess
        self.poly = polyglot
        self.devInfo =  deviceInfo
        self.address = address
        self.primary = primary
        self.yoIRrem = None
        self.schedule = None
        self.node_ready = False
        self.configDone = False
        self.system_ready=False
        self._update_lock = threading.Lock()
        self.powerSupported = True # assume 
        self.n_queue = []     

        self.poly.subscribe(polyglot.START, self.start, self.address)
        self.poly.subscribe(polyglot.STOP, self.stop)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        self.poly.subscribe(self.poly.CONFIGDONE, self.configDoneHandler)
          

        # start processing events and create add our controller node
        self.poly.ready()
        self.poly.addNode(self, conn_status = None, rename = True)
        self.wait_for_node_done()
        self.node = self.poly.getNode(address)
        # persist or restore parent node name
        try:
            saved = self.get_node_custom('saved_name')
            if saved:
                saved = self.poly.getValidName(saved)
                self._name_sync_saved = saved
                self.set_node_custom('saved_name', saved)
                if self.node.name != saved:
                    try:
                        self.node.rename(saved)
                        logging.info(f'Restored parent node name for {self.address} to saved name {saved}')
                    except Exception as e:
                        logging.debug(f'Failed to restore parent node name for {self.address}: {e}')
            else:
                self.set_node_custom('saved_name', self.node.name)
                self._name_sync_saved = self.node.name
        except Exception as e:
            logging.debug(f'Error handling parent custom name for {self.address}: {e}')
        self.adr_list = []
        self.adr_list.append(address)   
        self.codes_used = []
        self.code_nodes = {}
        self.node_ready = True

    def add_code_node(self, code):
        nde_address = self.address[-11:] + 'x' + str(code)
        logging.debug(f'ircode {self.primary} {code} {nde_address}')
        if code < 9:
            name = 'Code 0' + str(code+1)
        else:
            name = 'Code ' + str(code+1)
        name = self.poly.getValidName(name)
        self.code_nodes[code] = udiYoInfraredCode(self.poly, self.primary, nde_address, name, code, self.yoIRrem)

    def configDoneHandler(self):
        logging.info(f'configDoneHandler called  - {self.name}')
        self.configDone = True

    def start(self):
        logging.info('start - udiIRremote')
        while not self.node_ready and not self.configDone:
            time.sleep(0.5)
        self.my_setDriver('ST', 0)
        # Create schedule node before device online check
        sch_address = self.address[4:14] + '_SCH'
        sch_address = self.poly.getValidAddress(sch_address)
        self.schedule = udiYoSchedule(self.poly, self.address, sch_address, 'Schedules', self.yoAccess, self.devInfo)
        self.adr_list.append(sch_address)
        self.yoIRrem = YoLinkInfraredRemoter(self.yoAccess, self.devInfo, self.updateStatus)
        time.sleep(2)
        self.yoIRrem.initNode()
        time.sleep(1)
        while not self.yoIRrem.check_system_online() and (self.yoIRrem.throttled()):
            logging.info(f'Waiting for device {self.name} to come online.. Must be online to get learned codes')
            time.sleep(2)
        #self.my_setDriver('ST', 1)
        self.my_setDriver('GV30', 1)
        code_dict_temp = self.yoIRrem.get_code_dict()
        logging.debug(f'Code dict temp: {code_dict_temp}')
        time.sleep(2)
        for code in range(0, len(code_dict_temp)):
            if code_dict_temp[code]:
                logging.info(f'Adding code {code} to node list')
                self.codes_used.append(code)
                self.add_code_node(code)
        self.poly.updateProfile()
        logging.info('YoLink Infrared Remoter Node Ready')
        self.system_ready = True

    def stop (self):
        logging.info('Stop udiIRremote')
        self.my_setDriver('ST', 0)
        if getattr(self, 'yoIRrem', None):
            self.yoIRrem.shut_down()
        #if self.node:
        #    self.poly.delNode(self.node.address)

    def checkDataUpdate(self):
        if self.yoIRrem.data_updated():
            self.updateData()

    def checkNameSync(self):
        self.sharedCheckNameSync()
        for code_node in self.code_nodes.values():
            if hasattr(code_node, 'checkNameSync'):
                code_node.checkNameSync()

    def err_code2nbr(self, status_code):
        #if status_code == 'notLearn':
        #    return(0)
        if isinstance(status_code, bool):
            if status_code == True: 
                return(1)
            else: 
                return(2)
        else:
            return(99)


    def updateData(self):
        if self.node is not None:
            while not self.node_ready or not self.system_ready:
                time.sleep(0.5)
            logging.debug('updateData - {}'.format(self.yoIRrem.check_system_online()))
            message_type, message_action = self.yoIRrem.get_message_type()
            unix_time = self.yoIRrem.get_report_time('reportAt')
            self.my_setDriver('TIME', unix_time, 151)

            if message_type and 'Schedules' in str(message_type):
                if self.schedule is not None:
                    self.schedule.update_schedule_data(source_device=self.yoIRrem)
                return

        if  self.yoIRrem.check_system_online():
            res = self.yoIRrem.get_status_code()
            logging.debug(f'IR remote status code: {res}')
            self.my_setDriver('ST', self.err_code2nbr(res), type=message_type)
            self.my_setDriver('GV0',len(self.codes_used) )                 
            self.my_setDriver('GV1',self.yoIRrem.get_data('battery'), type=message_type)
            self.my_setDriver('GV2',self.err_code2nbr(res), type=message_type)

            self.my_setDriver('GV30', 1)
            if self.yoIRrem.suspended:
                self.my_setDriver('GV20', 1)
            else:
                self.my_setDriver('GV20', 0)
        else:
            self.my_setDriver('ST', 0)
            self.my_setDriver('GV20', 2)
            self.my_setDriver('GV30', 0)




    def updateStatus(self, data):
        logging.info('udiIRremote updateStatus')
        if self.yoIRrem is not None:
            with self._update_lock:
                self.yoIRrem.updateStatus(data)
                self.updateData()
                #res = self.yoIRrem.getIRstatus_info()
                #logging.debug(f'IR status info: {res}')
                logging.debug(f'Code nodes: {self.code_nodes}')
                update_type = self.yoIRrem.get_info('type')
                action = self.yoIRrem.get_info('action')
                if action in ['send', 'report'] or update_type == 'event':
                    res_code = self.yoIRrem.get_data('key')
                    if isinstance(res_code, int) and res_code in self.code_nodes:
                        logging.debug(f'Updating code node {res_code}')
                        self.code_nodes[res_code].updateData()
                    
    def checkOnline(self):
        self.yoIRrem.refreshDevice()


    def update(self, command = None):
        logging.info('Update Status Executed')
        self.saveCurrentNodeNames()
        self.yoIRrem.refreshDevice()
        # Keep schedule child node in sync when UPDATE is requested.
        self.yoIRrem.refreshSchedules()
    
    
    def find_next_code(self):  
        for code in range(1, 65):
            if code not in self.codes_used:
                return(code)
        return(None)


    
    def learn_IRcode(self, command=None):
        logging.info('udiIRremote learn_IRcode')
        if self.yoIRrem.nbr_codes < 64:
            code = self.find_next_code()
            if  not isinstance(code, int):
                logging.info('Maximum number of codes already learned')
                return() 
            self.codes_used.append(code)
            logging.info(f'Learning code {code}')

            self.yoIRrem.learn(code)
            time.sleep(1)
            res = self.yoIRrem.check_learn_completed(code)
            logging.debug(f'Initial learn res: {res}')  
            attempts = 1
            while res in ['learning', 'ignore'] and attempts < 10:
                time.sleep(1)
                res = self.yoIRrem.check_learn_completed(code)
                attempts += 1   
                logging.debug(f'Learn res: {res}')  

            if res == 'success':
                logging.info(f'Learned code {code} successfully')
                logging.info(f'Code {code} learned - creating new node')
                self.add_code_node(code)
                                                                   
                self.yoIRrem.refreshDevice()
                #self.updateData()
            else:
                logging.info('Unsuccessful learn of code {}'.format(code))
    


    commands = {
                'UPDATE': update,
                'LEARNCODE' : learn_IRcode,
                #'TXCODE': send_IRcode,                'LEARNCODE' : learn_IRcode,
                }





