import ConfigParser
import os
import time
import os.path
import traceback
import requests

from twisted.protocols import basic
from twisted.internet import reactor
from twisted.internet.serialport import SerialPort
from serial import PARITY_EVEN, SEVENBITS


"""
Parses P1 Smart Meter protocol and publish it tot MQTT (http://domoticx.com/p1-poort-slimme-meter-hardware/) 
"""

class SmartMeterReadings(object):
    '''
    This class represents smartmeter readings.
    '''

    def __init__(self, low_tariff, normal_tariff, low_tariff_produced, normal_tariff_produced, actual_usage, gas_usage):
        self.low_tariff = low_tariff
        self.normal_tariff = normal_tariff
        self.low_tariff_produced = low_tariff_produced
        self.normal_tariff_produced = normal_tariff_produced
        self.actual_usage = actual_usage
        self.gas_usage = gas_usage

    def __repr__(self):
        return '[SmartMeterReadings] Low tariff: %7.3fkWh, normal tariff: %7.3fkWh, low tariff produced: %7.3fkWh, ' \
               'normal tariff produced: %7.3fkWh, actual usage: %rW, gas usage: %7.3fM3' % (
                   self.low_tariff, self.normal_tariff,
                   self.low_tariff_produced,
                   self.normal_tariff_produced,
                   self.actual_usage, self.gas_usage)

class SmartMeterProtocol(basic.LineReceiver):
    '''
    This class handles the smartmeter protocol.
    Extends Twisted LineReceiver to receive serial packets
    '''
    """ def on_connect(self, client, userdata, flags, rc):
        print("CONNACK (ENERGY) received with code %d." % (rc)) """

    def __init__(self, NodeControl):
        self._NodeControl = NodeControl
        self._telegram = []

    def lineReceived(self, line):
        if line.startswith('!'):
            try:
                readings = self._parse_telegram(self._telegram)

                totalEnergyUse = readings.normal_tariff + readings.low_tariff
                totalEnergyGen = readings.normal_tariff_produced + readings.low_tariff_produced

                fnameDayStart = self._NodeControl.datadir + "daystart-%s.log" % time.strftime("%Y%m%d")
                self._NodeControl.log.debug("Daystart file location: %s." % fnameDayStart)
                dayEnergyUse = 0
                dayGasUse = 0
                dayEnergyGen = 0
                if not (os.path.isfile(fnameDayStart)):
                    # use a temp file to record start of the day readings
                    self._NodeControl.log.debug(
                        "Daystart file location: %s does not exists, create one." % fnameDayStart)
                    fo = open(fnameDayStart, "wb")
                    fo.write("[dayreadings]\n")
                    fo.write("gaszeroreading=%s\n" % readings.gas_usage)
                    fo.write("eleczerousereading=%s\n" % totalEnergyUse)
                    fo.write("eleczerogenreading=%s\n" % totalEnergyGen)
                    totalRainFile = self._NodeControl.datadir + "totalRain.dat"
                    if (os.path.isfile(totalRainFile)):
                        configParser = ConfigParser.RawConfigParser()
                        configParser.read(totalRainFile)
                        dayStartTotalRain = configParser.get('raindata', 'totalrain')
                        fo.write("rainzeroreading=%s\n" % dayStartTotalRain)
                    else:
                        fo.write("rainzeroreading=0\n")
                    fo.close()
                else:
                    try:
                        self._NodeControl.log.debug(
                            "Daystart file location: %s does exists, read zero readings." % fnameDayStart)
                        configParser = ConfigParser.RawConfigParser()
                        configParser.read(fnameDayStart)
                        dayStartEnergyUse = float(configParser.get('dayreadings', 'eleczerousereading'))
                        dayStartEnergyGen = float(configParser.get('dayreadings', 'eleczerogenreading'))
                        dayStartGasUse = float(configParser.get('dayreadings', 'gaszeroreading'))
                        dayEnergyUse = ( (totalEnergyUse - dayStartEnergyUse) * 1000) # watt per uur, geen Kwh
                        dayEnergyGen = ( (totalEnergyGen - dayStartEnergyGen) * 1000) # watt per uur, geen Kwh
                        dayGasUse = ( (readings.gas_usage - dayStartGasUse) * 1000)
                    except Exception, exp:
                        self._NodeControl.log.warning(
                            "error reading daystart config: %s. Error: %s" % (fnameDayStart, traceback.format_exc()))
                print "readings: "
                print readings

                self._NodeControl.log.debug(
                    "Calculation results: day gas use: %s liter, day net energy use: %s wh, teruggeleverd: %s wh and current power: %s watt." % (
                        dayGasUse, dayEnergyUse, dayEnergyGen, readings.actual_usage))
                self._NodeControl.MQTTPublish(sTopic="smartmeter/power", sValue=str(readings.actual_usage), iQOS=0,
                                              bRetain=True)
                self._NodeControl.MQTTPublish(sTopic="smartmeter/energyuse", sValue=str(dayEnergyUse), iQOS=0,
                                              bRetain=True)
                self._NodeControl.MQTTPublish(sTopic="smartmeter/energygen", sValue=str(dayEnergyGen), iQOS=0,
                                              bRetain=True)
                self._NodeControl.MQTTPublish(sTopic="smartmeter/gas", sValue=str(dayGasUse), iQOS=0, bRetain=True)
                self._telegram = []

                if self._NodeControl.nodeProps.has_option('domoticz', 'active') and \
                        self._NodeControl.nodeProps.getboolean('domoticz', 'active'):
                    domP1String = "http://%s:%s/json.htm?type=command&param=udevice&idx=%s&nvalue=0&svalue=%s;%s;%s;%s;%s;0" % \
                                                  (self._NodeControl.nodeProps.get('domoticz', 'url'),\
                                                   self._NodeControl.nodeProps.get('domoticz', 'port'),\
                                                   self._NodeControl.nodeProps.get('domoticz', 'P1Indx'), \
                                                   str(readings.low_tariff * 1000), \
                                                   str(readings.normal_tariff * 1000), \
                                                   str(readings.low_tariff_produced * 1000), \
                                                   str(readings.normal_tariff_produced * 1000), \
                                                   str(readings.actual_usage) )
                    self._NodeControl.log.debug("Publish: [%s]" % domP1String)
                    domoticzResult = requests.get(domP1String, \
                                                  auth=(self._NodeControl.nodeProps.get('domoticz', 'user'), \
                                                        self._NodeControl.nodeProps.get('domoticz', 'pw')))
                    self._NodeControl.log.debug("Result: %s." % domoticzResult)
                    domGasString = "http://%s:%s/json.htm?type=command&param=udevice&idx=%s&nvalue=0&svalue=%s" % \
                                                  (self._NodeControl.nodeProps.get('domoticz', 'url'),\
                                                   self._NodeControl.nodeProps.get('domoticz', 'port'),\
                                                   self._NodeControl.nodeProps.get('domoticz', 'GASIndx'), \
                                                   str(readings.gas_usage) )
                    self._NodeControl.log.debug("Publish: [%s]" % domGasString)
                    domoticzGasResult = requests.get(domGasString, \
                                                        auth=(self._NodeControl.nodeProps.get('domoticz', 'user'), \
                                                              self._NodeControl.nodeProps.get('domoticz', 'pw')))
                    self._NodeControl.log.debug("Result: %s." % domoticzGasResult)

            except Exception, exp:
                self._NodeControl.log.warning("Can not read or upload smartmeter data: %s" % traceback.format_exc())
        else:
            self._telegram.append(line)

    def _parse_telegram(self, telegram):
        '''
        This function parses a B101 smartmeter telegram.
        More information about this telegram can be found here:
        http://www.energiened.nl/_upload/bestellingen/publicaties/284_P1Smart%20Meter%20v2.1%20final%20P1.pdf

        @param telegram: the telegram to parse
        '''

        low_tariff = 0
        normal_tariff = 0
        low_tariff_produced = 0
        normal_tariff_produced = 0
        actual_usage = 0
        gas_usage = 0
        next_is_gas = False

        for tg in telegram:
            print tg
            if tg.startswith('1-0:1.8.1'):
                low_tariff = float(tg[tg.index('(') + 1:tg.index('*')])
            if tg.startswith('1-0:1.8.2'):
                normal_tariff = float(tg[tg.index('(') + 1:tg.index('*')])
            if tg.startswith('1-0:2.8.1'):
                low_tariff_produced = float(tg[tg.index('(') + 1:tg.index('*')])
            if tg.startswith('1-0:2.8.2'):
                normal_tariff_produced = float(tg[tg.index('(') + 1:tg.index('*')])
            if tg.startswith('1-0:1.7.0'):
                actual_usage = float(tg[tg.index('(') + 1:tg.index('*')]) * 1000.0

            if next_is_gas and tg.startswith('('):
                gas_usage = float(tg[tg.index('(') + 1:tg.index(')')])
            next_is_gas = False
            if tg.startswith('0-1:24.3.0'):
                next_is_gas = True
        return SmartMeterReadings(low_tariff, normal_tariff, low_tariff_produced, normal_tariff_produced, actual_usage,
                                  gas_usage)

    def postData(self, energy, pwr, gas):
        pass
        # http://solar.tridgell.net/webbox/
        # http://pvoutput.org/help.html#api-addoutput
        # dit is het stuk wat de gegevens in de sqllite db plaats (van smadata appl)

        """
        try:
            dbFilePath = self._wrapper.dbpath
            print "trying to post to %s" % dbFilePath
            if os.path.isfile(dbFilePath):
                curdatetime=time.time()  #datetime.datetime.now()
                print curdatetime
                con = sqlite3.connect(dbFilePath,detect_types=sqlite3.PARSE_DECLTYPES)
                cur = con.cursor()
                cur.execute("INSERT INTO Consumption VALUES (?,?,?,?)", (curdatetime,pwr,energy,gas))
                a=cur.fetchone()
                con.commit()
                con.close()
                print "trying to post to %s succes" % dbFilePath
        except Exception, exp:
            print traceback.format_exc()  """

class SmartMeterWrapper(object):
    def __init__(self, oNodeControl):
        if oNodeControl.nodeProps.has_option('smartmeter', 'serialport'):
            SerialPort(SmartMeterProtocol(oNodeControl),
                       oNodeControl.nodeProps.get('smartmeter', 'serialport'),
                       reactor,
                       bytesize=SEVENBITS,
                       parity=PARITY_EVEN)
        else:
            oNodeControl.log.warning("missing config param: smartmeter | serialport.")
