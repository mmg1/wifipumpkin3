from wifipumpkin3.core.config.globalimport import *
from collections import OrderedDict
from functools import partial
from threading import Thread
import queue
from scapy.all import *
import logging, os
import wifipumpkin3.core.utility.constants as C
from wifipumpkin3.core.servers.proxy.proxymode import *
from wifipumpkin3.core.utility.collection import SettingsINI
from wifipumpkin3.core.common.uimodel import *
from wifipumpkin3.core.widgets.docks.dock import DockableWidget
from wifipumpkin3.plugins.captivePortal import *
from ast import literal_eval

# This file is part of the wifipumpkin3 Open Source Project.
# wifipumpkin3 is licensed under the Apache 2.0.

# Copyright 2020 P0cL4bs Team - Marcos Bomfim (mh4x0f)

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class TCPProxyDock(DockableWidget):
    id = "TCPProxy"
    title = "TCPProxy"

    def __init__(self,parent=0,title="",info={}):
        super(TCPProxyDock,self).__init__(parent,title,info={})
        self.setObjectName(self.title)
        self.THeaders  = OrderedDict([ ('Plugin',[]),('Logging',[])])


    def writeModeData(self,data):
        ''' get data output and add on QtableWidgets '''
        self.THeaders['Plugin'].append(data.keys()[0])
        self.THeaders['Logging'].append(data[data.keys()[0]])
        Headers = []
        print(data)

    def stopProcess(self):
        pass

class CaptivePortal(ProxyMode):
    Name = "Captive Portal"
    Author = "Pumpkin-Dev"
    ID = "captiveflask"
    Description = "Allow block Internet access for users until they open the page login page."
    Hidden = False
    LogFile = C.LOG_CAPTIVEPO
    CONFIGINI_PATH = C.CONFIG_CP_INI
    _cmd_array = []
    ModSettings = True
    RunningPort = 80
    ModType = "proxy" 
    TypePlugin =  1 

    def __init__(self,parent=None, **kwargs):
        super(CaptivePortal,self).__init__(parent)
        self.setID(self.ID)
        self.setTypePlugin(self.TypePlugin)
        self.plugins        = []
        self.search_all_ProxyPlugins()

    @property
    def CMD_ARRAY(self):
        self.tamplate = self.getPluginActivated()
        self._cmd_array = [
        '-t',self.tamplate.TemplatePath, 
        '-r',self.conf.get('dhcp', 'router'),
        '-s',self.tamplate.StaticPath
        ]
        return self._cmd_array

    def boot(self):

        self.reactor= ProcessThread({'captiveflask': self.CMD_ARRAY})
        self.reactor._ProcssOutput.connect(self.LogOutput)
        self.reactor.setObjectName(self.ID)

        # settings iptables for add support captive portal 
        IFACE = self.conf.get('accesspoint', 'interfaceAP')
        IP_ADDRESS = self.conf.get('dhcp', 'router')
        PORT= 80
        
        self.defaults_rules[self.ID] = []
        print(display_messages('settings for captive portal:', info=True))
        print(display_messages("allow FORWARD UDP DNS", info=True))
        self.defaults_rules[self.ID].append('iptables -A FORWARD -i {iface} -p tcp --dport 53 -j ACCEPT'.format(iface=IFACE))
        print(display_messages("allow traffic to captive portal", info=True))
        self.defaults_rules[self.ID].append('iptables -A FORWARD -i {iface} -p tcp --dport {port} -d {ip} -j ACCEPT'.format(iface=IFACE, port=PORT, ip=IP_ADDRESS))
        print(display_messages("block all other traffic in access point", info=True))
        self.defaults_rules[self.ID].append('iptables -A FORWARD -i {iface} -j DROP '.format(iface=IFACE))
        print(display_messages("redirecting HTTP traffic to captive portal", info=True ))
        self.defaults_rules[self.ID].append('iptables -t nat -A PREROUTING -i {iface} -p tcp --dport 80 -j DNAT --to-destination {ip}:{port}'.format(iface=IFACE,ip=IP_ADDRESS, port=PORT))
        self.runDefaultRules()

    @property
    def getPlugins(self):
        commands = self.config.get_all_childname('plugins')
        list_commands = []
        for command in commands:
            list_commands.append(self.ID + '.' + command)
        return list_commands

    def LogOutput(self,data):
        headers_table, output_table = ["IP", "Login", "Password"], []
        if self.conf.get('accesspoint', 'statusAP', format=bool):
            self.logger.info(data)
            try:
                data = literal_eval(data)
                ip = list(data.keys())[0]
                output_table.append([
                    ip,
                    setcolor(data[ip]['login'], 'red'),
                    setcolor(data[ip]['password'], 'red')
                ])
                print(display_messages('CaptiveFlask credentials:',info=True,sublime=True))
                return display_tabulate(headers_table, output_table)
            except SyntaxError:
                pass


    def parser_set_captiveflask(self, status, plugin_name):
        try:
            # plugin_name = pumpkinproxy.no-cache 
            name_plugin,key_plugin = plugin_name.split('.')[0],plugin_name.split('.')[1]
            if key_plugin in self.config.get_all_childname('plugins'):
                self.setPluginActivated(key_plugin, status)
            else:
                print(display_messages('unknown plugin: {}'.format(key_plugin),error=True))
        except IndexError:
            print(display_messages('unknown sintax command',error=True))

    def search_all_ProxyPlugins(self):
        ''' load all plugins function '''
        plugin_classes = plugin.CaptiveTemplatePlugin.__subclasses__()
        for p in plugin_classes:
            self.plugins.append(p())

    def setPluginActivated(self, key, status):
        self.config.set('plugins',key, status)
        plugins = self.config.get_all_childname('plugins')
        for plugin in plugins:
            if plugin != key:
                self.config.set('plugins',plugin, False)

    def getPluginActivated(self):
        for plugin in self.plugins:
            if (self.config.get('plugins',plugin.Name,format=bool)):
                self.plugin_activated = plugin
        self.plugin_activated.initialize() # change language if exist
        return self.plugin_activated