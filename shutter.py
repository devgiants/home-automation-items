#!/usr/bin/python3

import logging
import sys
import threading
from gpiozero import LED, Button
from signal import pause

class Shutter:
    UP = 'open'
    DOWN = 'close'
    STOP = 'stop'

    name = None
    logger = None
    buttonUp = None
    buttonDown = None
    relayUp = None
    relayDown = None

    timeout = None
    timer = None

    mqttClient = None
    mqttTopicToListen = None
    mqttTopicToReport = None


    def registerGpi(self, buttonUpPinNumber, buttonDownPinNumber):
        self.buttonUp = Button(buttonUpPinNumber)
        self.buttonDown = Button(buttonDownPinNumber)       

        self.logger.debug(
            'Link GPI {}:{}, {}:{}'.format(                                
                'button up', buttonUpPinNumber,
                'button down', buttonDownPinNumber
                )
        )
       
        self.buttonUp.when_pressed = lambda button: self.__upManualAction(button)
        self.buttonDown.when_pressed = lambda button: self.__downManualAction(button)
        self.buttonUp.when_released = lambda button: self.__stopManualAction(button)
        self.buttonDown.when_released = lambda button: self.__stopManualAction(button)

    def registerMqtt(self, client, mqttTopicToListen, mqttTopicToReport):
        self.mqttClient = client
        self.mqttTopicToListen = mqttTopicToListen
        self.mqttTopicToReport = mqttTopicToReport   
        self.mqttSubscribe()     

        self.logger.debug('Register MQTT topic listening on topic {} (feedback {})'.format(self.mqttTopicToListen, self.mqttTopicToReport))

    def mqttSubscribe(self):
        self.mqttClient.subscribe(self.mqttTopicToListen)        
        self.mqttClient.message_callback_add(self.mqttTopicToListen, self.__handleMqttMessage)
    
    def __init__(self, name, relayUpPinNumber, relayDownPinNumber, timeout = 30):    
        self.name = name 
        self.relayUp = LED(relayUpPinNumber, False)
        self.relayDown = LED(relayDownPinNumber, False)   
        self.timeout = timeout        
        self.__initLogger()

        self.logger.debug(
            'Create shutter with {}:{}, {}:{}'.format(                                
                'relay up', relayUpPinNumber,
                'relay down', relayDownPinNumber
                )
        )
    
    def __initLogger(self):
        print(self.name)
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)         
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('[%(asctime)s] [{}] [%(name)s] %(levelname)s %(message)s'.format(__name__), datefmt='%d-%m-%Y %H:%M:%S')    
        handler.setFormatter(formatter) 
        self.logger.addHandler(handler)       
        

    def __stopManualAction(self, buttonReleased):
        self.__stop()        
        self.logger.debug('Manual stop (pin {})'.format(buttonReleased.pin))

    def __stopTimerAction(self):                
        self.logger.debug('Timer stop')
        self.__stop()   

    def __stopMqttAction(self):                
        self.logger.debug('MQTT stop')
        self.__stop() 

    def __stop(self):
        self.relayDown.off()
        self.relayUp.off()
        self.__sendFeedback(self.STOP)
        if type(self.timer) == threading.Timer:
            self.timer.cancel()

    def __upManualAction(self, buttonUp):
        self.logger.debug('Manual up (pin {})'.format(buttonUp.pin))
        self.__up()

    def __upMqttAction(self):
        self.logger.debug('MQTT up')
        self.__up()

    def __up(self):
        self.relayUp.on()
        self.relayDown.off()
        self.__sendFeedback(self.UP)
        self.__startTimer()

    def __downManualAction(self, buttonDown):
        self.logger.debug('Manual down (pin {})'.format(buttonDown.pin))
        self.__down()   

    def __downMqttAction(self):
        self.logger.debug('MQTT down')
        self.__down()

    def __down(self):
        self.relayUp.off()
        self.relayDown.on()        
        self.__sendFeedback(self.DOWN)
        self.__startTimer()        
    
    def __startTimer(self):
        self.logger.debug('Start timer for {}s'.format(self.timeout))        
        self.timer = threading.Timer(self.timeout, self.__stopTimerAction)
        self.timer.start()

    def __handleMqttMessage(self, client, userdata, message):
        if message.topic == self.mqttTopicToListen:
            payloadDecoded = message.payload.decode("utf-8")
            if payloadDecoded == self.UP:
                self.__upMqttAction()
            if payloadDecoded == self.DOWN:
                self.__downMqttAction()
            if payloadDecoded == self.STOP:
                self.__stopMqttAction()

    def __sendFeedback(self, message):
        self.logger.debug('Send feedback on {}:{}'.format(self.mqttTopicToReport, message))    
        self.mqttClient.publish(self.mqttTopicToReport, message)