#!/usr/bin/env python3
"""
ISY profile handler 
MIT License
"""
import os
import json
import xml.etree.ElementTree as ET

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)

testMessages = ['Mes1', 'Mess2','Messa3','Messag4','Message 5', 'mes77']



def udiTssProfileUpdate( messages):
    '''
        if (os.path.exists('./profile/editor/editor.xml')):
            #logging.debug('reading /devices.json')
            editor =  minidom.parse('./profile/editor/editor.xml')
        if (os.path.exists('./profile/nls/en_us.txt')):
            #logging.debug('reading /devices.json')
            nls = open(''./profile/nls/en_us.txt')
    '''
    if (os.path.exists('./profile/editor/editors.xml')):
        Tree = ET.parse('./profile/editor/editors.xml')
        #efile.close()
        editorRoot = Tree.getroot()
        indx = 0
        found = False

        while not found and indx < len(editorRoot):
            if editorRoot[indx].attrib['id'] == 'messages':
                found = True
                editorRoot[indx][0].attrib['subset'] = "0-"+str(len(messages)-1)
                NLSstr = editorRoot[indx][0].attrib['nls']
                
            else:
                indx = indx + 1

        Tree.write('./profile/editor/editors.xml')
    else:
        logging.error('./profile/editor/editors.xml NOT FOUND ')

    if (os.path.exists('./profile/nls/en_us.txt')):
        nfile = open('./profile/nls/en_us.txt', 'r')
        nls = nfile.readlines()
        nfile.close()
        #remove existing defines
        removeLines = []
        for line in range(len(nls)-1, 0, -1):
            if nls[line].find(NLSstr, 0, len(NLSstr)) != -1:
                nls.pop(line)
        
        #add new ones
        nls.append('\n')
        for line in range(0,len(messages)):
            nls.append('{}-{} = {}\n'.format(NLSstr, line, messages[line]))
        
        nfile = open('./profile/nls/en_us.txt', 'w')
        nfile.writelines(nls)
        nfile.close()
    else:
        logging.error('./profile/nls/en_us.txt NOT FOUND ')



