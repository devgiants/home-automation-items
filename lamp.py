#!/usr/bin/python3

import logging
import sys
import threading
from gpiozero import LED, Button
from signal import pause

class Lamp:
  
    ON = 'on'
    OFF = 'off'
    name = None
    logger = None   
    relay = None

    timeout = None
    timer = None

    mqttClient = None
    mqttTopicToListen = None
    mqttTopicToReport = None


    def registerGpio(self, relayPinNumber): 
        self.relay = LED(relayPinNumber, False)        

        self.logger.debug('Create lamp with relay ({})'.format(relayPinNumber))
        
    
    def registerMqtt(self, client, mqttTopicToListen, mqttTopicToReport):
        self.mqttClient = client
        self.mqttTopicToListen = mqttTopicToListen
        self.mqttTopicToReport = mqttTopicToReport
        self.mqttSubscribe()

        self.logger.debug('Register MQTT topic listening on topic {} (feedback {})'.format(self.mqttTopicToListen, self.mqttTopicToReport))

    def mqttSubscribe(self):
        self.mqttClient.subscribe(self.mqttTopicToListen)        
        self.mqttClient.message_callback_add(self.mqttTopicToListen, self.__handleMqttMessage)
    
    def __init__(self, name, timeout = 30):    
        self.name = name    
        self.timeout = timeout        
        self.__initLogger()
    
    def __initLogger(self):
        print(self.name)
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)         
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s] [{}] [%(name)s] %(levelname)s %(message)s'.format(__name__), datefmt='%d-%m-%Y %H:%M:%S')    
        handler.setFormatter(formatter) 
        self.logger.addHandler(handler)       
        

    # def __stopTimerAction(self):                
    #     self.logger.debug('Timer stop')
    #     self.__stop()   

    def __offMqttAction(self):                
        self.logger.debug('MQTT off')
        self.__off() 

    def __off(self):
        self.relay.off()                
        # self.timer.cancel()

    def __onMqttAction(self):
        self.logger.debug('MQTT on')
        self.__on()

    def __on(self):
        self.relay.on()                
        # self.__startTimer()        
    
    # def __startTimer(self):
    #     self.logger.debug('Start timer for {}s'.format(self.timeout))        
    #     self.timer = threading.Timer(self.timeout, self.__stopTimerAction)
    #     self.timer.start()

    def __handleMqttMessage(self, client, userdata, message):
        if message.topic == self.mqttTopicToListen:
            payloadDecoded = message.payload.decode("utf-8")
            if payloadDecoded == self.ON:
                self.__onMqttAction()            
            if payloadDecoded == self.OFF:
                self.__offMqttAction()                          