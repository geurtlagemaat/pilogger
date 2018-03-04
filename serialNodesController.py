import traceback
from time import sleep
from bliknetlib.serialNodesProtocol import SerialNodesProtocol
from twisted.internet.serialport import SerialPort
from twisted.internet import reactor
import serial
import wiringpi as wiringpi

class SerialNodesController(object):
    def __init__(self, oNodeControl):
        self._NodeControl = oNodeControl
        # list all serial ports: python -m serial.tools.list_ports
        self._connectSerialPort()

    def _connectSerialPort(self):
        self.Close()
        myProtocol = SerialNodesProtocol(self._NodeControl, OnReceive=self.OnMsgReceive)
        self._serialPort = SerialPort(myProtocol, self._NodeControl.nodeProps.get('serialnodes', 'serialport'),
                                      reactor,
                                      baudrate=9600,
                                      bytesize=serial.EIGHTBITS,
                                      parity=serial.PARITY_NONE)
        self._NodeControl.log.debug('Serial port: %s open.' % self._NodeControl.nodeProps.get('serialnodes', 'serialport'))
        sleep(1)

    def OnMsgReceive(self, RecMsg):
        myNodeID = '999' # self._NodeControl.nodeProps.get('system', 'nodeId')

        if str(RecMsg.ToAdress) == myNodeID:
            # for this node
            if ( (int(RecMsg.Function)==1) and (int(RecMsg.MsgValue)==1) ):
                self._NodeControl.log.debug("Deuropen signal (keypad)")
                self.doOpenDoor()
                self._NodeControl.MQTTPublish(sTopic="deur/keyopen", sValue="ON", iQOS=0, bRetain=False)
            elif ( (int(RecMsg.Function)==2) and (int(RecMsg.MsgValue)==1) ):
                self._NodeControl.log.debug("Deuropen signal (RFID)")
                self.doOpenDoor()
                self._NodeControl.MQTTPublish(sTopic="deur/rfidopen", sValue="ON", iQOS=0, bRetain=False)
            elif ( (int(RecMsg.Function)==3) and (int(RecMsg.MsgValue)==1) ):
                self._NodeControl.log.debug("Deurbel signal.")
                self._NodeControl.MQTTPublish(sTopic="deur/ring", sValue="ON", iQOS=0, bRetain=False)
            elif ( (int(RecMsg.Function)==4) and (int(RecMsg.MsgValue)==1) ):
                self._NodeControl.log.debug("Tampering Keypad")
                self._NodeControl.MQTTPublish(sTopic="tampering/keypad", sValue="ON", iQOS=0, bRetain=False)

    def ResetState(self, topic):
        self._NodeControl.MQTTPublish(sTopic=topic, sValue="OFF", iQOS=0, bRetain=False)

    def SendMessage(self, sSerialMessage):
        try:
            self._serialPort.write(sSerialMessage)
            sleep(0.1)
            return True
        except Exception, exp:
            print traceback.format_exc()
            self._NodeControl.log.error("SendMessage error: %s." % traceback.format_exc())
            return False

    def Close(self):
        try:
            self._serialPort.loseConnection()
            self._serialPort = None
        except:
            pass

    def doOpenDoor(self):
        if self._NodeControl.nodeProps.has_option('dooropener', 'active') and\
                self._NodeControl.nodeProps.getboolean('dooropener', 'active'):
            idoorUnlockTime = 5
            if self._NodeControl.nodeProps.has_option('dooropener', 'unlockTime'):
                idoorUnlockTime = float(self._NodeControl.nodeProps.get('dooropener', 'unlockTime'))
            self._NodeControl.log.debug("Door opening")
            wiringpi.digitalWrite(17, 1)
            self._NodeControl.log.debug("Door opening done")
            reactor.callLater(idoorUnlockTime, self.releaseDoorLockEvent)

    def releaseDoorLockEvent(self):
        self._NodeControl.log.debug("releaseDoorLockEvent")
        wiringpi.digitalWrite(17, 0)
        self._NodeControl.log.debug("Deur GPIO 17 off")