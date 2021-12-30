# -*- coding: utf-8 -*-
import string
import traceback

import wiringpi
from twisted.internet import reactor

def doUpdate(NodeControl, pumpControl, ioPin):
    NodeControl.log.debug("Heatingsensors Sensor Status update")
    try:
        # DS18B20
        tempIn = None
        tempOut = None
        if NodeControl.nodeProps.has_option('heatingsensors', 'heatingtemp'):
            mySensorReading = getDS18B20Temp(NodeControl, NodeControl.nodeProps.get('heatingsensors', 'heatingtemp'))
            if mySensorReading is not None:
                tempIn = mySensorReading / float(1000)
                sTemp = '{:.1f}'.format(mySensorReading / float(1000))
                NodeControl.log.debug("Temperatuur: %s" % sTemp)
                NodeControl.MQTTPublish(sTopic="heating/heatingtemp", sValue=str(sTemp), iQOS=0, bRetain=True)
            else:
                NodeControl.log.warning("no reading: %s" % NodeControl.nodeProps.get('heatingsensors', 'heatingtemp'))
        else:
            NodeControl.log.warning("Can not read heatingtemp, no [heatingsensors] heatingtemp configured")

        if NodeControl.nodeProps.has_option('heatingsensors', 'heatingretourtemp'):
            mySensorReading = getDS18B20Temp(NodeControl, NodeControl.nodeProps.get('heatingsensors', 'heatingretourtemp'))
            if mySensorReading is not None:
                tempOut = mySensorReading / float(1000)
                sTemp = '{:.1f}'.format(mySensorReading / float(1000))
                NodeControl.log.debug("Temperatuur: %s" % sTemp)
                NodeControl.MQTTPublish(sTopic="heating/heatingretourtemp", sValue=str(sTemp), iQOS=0, bRetain=True)
            else:
                NodeControl.log.warning("no reading: %s" % NodeControl.nodeProps.get('heatingsensors', 'heatingretourtemp'))
        else:
            NodeControl.log.warning("Can not read heatingretourtemp, no [heatingsensors] heatingretourtemp configured")
        if pumpControl and tempIn is not None and tempOut is not None:
            checkPump(NodeControl, tempIn, tempOut, ioPin)
    except Exception as exp:
        NodeControl.log.warning("status update, error: %s." % (traceback.format_exc()))

def doAntiFreezeRun(NodeControl, ioPin):
    NodeControl.log.debug("check AntiFreeze Run.")
    if wiringpi.digitalRead(ioPin):
        NodeControl.log.debug("check AntiFreeze Run, start pump")
        wiringpi.digitalWrite(ioPin, 0)
        NodeControl.MQTTPublish(sTopic="heating/pump", sValue="ON", iQOS=0, bRetain=True)
    # uitschakelen doen we niet omdat bij de volgende doUpdate de pomp aan de hand van de delta vanzelf
    # wel weer aan of uit wordt geschakeld.

def checkPump(NodeControl, tempIn, tempOut, ioPin):
        deltaTemp = 2
        pumpOnTemp = 34
        if NodeControl.nodeProps.has_option('heatingsensors', 'deltatemp'):
            deltaTemp = NodeControl.nodeProps.getint('heatingsensors', 'deltatemp')
        if NodeControl.nodeProps.has_option('heatingsensors', 'pumpontemp'):
            pumpOnTemp = NodeControl.nodeProps.getint('heatingsensors', 'pumpontemp')
        # relay is NC: 0 - pump on, 1 pump off
        sensorDiffTemp = tempIn - tempOut
        NodeControl.log.debug("Pumpcontrol, delta temp: %s" % sensorDiffTemp)
        if ( (sensorDiffTemp > deltaTemp) or (tempIn > pumpOnTemp) ):
            # pump on
            if wiringpi.digitalRead(ioPin):
                # was 1, off, turn it on (0)
                wiringpi.digitalWrite(ioPin, 0)
                NodeControl.MQTTPublish(sTopic="heating/pump", sValue="ON", iQOS=0, bRetain=True)
                NodeControl.log.debug("Pump started")
        else:
            # pump off
            if not wiringpi.digitalRead(ioPin):
                wiringpi.digitalWrite(ioPin, 1)
                NodeControl.MQTTPublish(sTopic="heating/pump", sValue="OFF", iQOS=0, bRetain=True)
                NodeControl.log.debug("Pump stopped")

def getDS18B20Temp(NodeControl, sSensorPath):
    mytemp = None
    try:
        f = open(sSensorPath, 'r')
        line = f.readline() # read 1st line
        crc = line.rsplit(' ', 1)
        crc = crc[1].replace('\n', '')
        if crc == 'YES':
            line = f.readline() # read 2nd line
            mytemp = line.rsplit('t=', 1)
        else:
            NodeControl.log.warning(
                "Error reading sensor, path: %s, error: %s." % (sSensorPath, 'invalid message'))
        f.close()
        if mytemp is not None:
            return int(mytemp[1])
        else:
            return None
    except Exception as exp:
        NodeControl.log.warning("Error reading sensor, path: %s, error: %s." % (sSensorPath, traceback.format_exc()))
        return None