# -*- coding: utf-8 -*-
import csv
import datetime
import os
import traceback
import time
import configparser

"""
Parses PYWWS weather data (https://pywws.readthedocs.io/en/latest/) and publishes in to MQTT 
"""

def doUpdate(NodeControl):
    if NodeControl.nodeProps.has_option('weather', 'csvPath'):
        sBasePath = NodeControl.nodeProps.get('weather', 'csvPath')
        now = datetime.datetime.now()
        sPath = os.path.join(sBasePath, str(now.year), str(now.year) + "-" + str(now.month).zfill(2),
                             str(now.year) + "-" + str(now.month).zfill(2) + "-" + str(now.day).zfill(2) + '.txt')
        """
        idx, delay, hum_in, temp_in, hum_out, temp_out, abs_pressure, wind_ave, wind_gust, wind_dir, rain, status.
         0      1      2       3          4        5         6            7          8          9      10     11
        """
        try:
            csvRow = get_last_row(sPath)
            fnameDayStart = NodeControl.datadir + "daystart-%s.log" % time.strftime("%Y%m%d")
            NodeControl.log.debug("Daystart file location: %s." % fnameDayStart)
            if (os.path.isfile(fnameDayStart)):
                cHour = str(now.hour)
                dayStartRain = 0
                hStartRain = 0
                NodeControl.log.debug("Daystart file location: %s does exists, read zero readings." % fnameDayStart)
                configParser = ConfigParser.RawConfigParser()
                configFilePath = fnameDayStart
                configParser.read(fnameDayStart)
                if configParser.has_option('dayreadings', 'rainzerousereading'):
                    dayStartRain = float(configParser.get('dayreadings', 'rainzerousereading'))
                    if configParser.has_option('hourRainReadings', cHour):
                        hStartRain = float(configParser.get('hourRainReadings', cHour))
                    else:
                        # no hour reading, write it
                        try:
                            if not configParser.has_section('hourRainReadings'):
                                configParser.add_section('hourRainReadings') # monkey proofing
                            configParser.set('hourRainReadings', cHour, str(csvRow[10]))
                            f = open(fnameDayStart, 'w')
                            configParser.write(f)
                            f.close()
                        except Exception as exp:
                            NodeControl.log.warning("Can not write day start rain value to: %s, error: %s." % (
                                fnameDayStart, traceback.format_exc()))
                else:
                    # first reading this day, write zero reading
                    try:
                        configParser.add_section('hourRainReadings')
                        configParser.set('hourRainReadings', cHour, str(csvRow[10]))
                        configParser.set('dayreadings', 'rainzerousereading', str(csvRow[10]))
                        f = open(fnameDayStart, 'w')
                        configParser.write(f)
                        f.close()
                    except Exception as exp:
                        NodeControl.log.warning("Can not write day start rain value to: %s, error: %s." % (
                            fnameDayStart, traceback.format_exc()))

                Rain24H = float(csvRow[10]) - dayStartRain
                Rain1H = float(csvRow[10]) - hStartRain

                NodeControl.MQTTPublish(sTopic="washok/hum", sValue=str(csvRow[2]), iQOS=0, bRetain=True)
                NodeControl.MQTTPublish(sTopic="washok/temp", sValue=str(csvRow[3]), iQOS=0, bRetain=True)
                NodeControl.MQTTPublish(sTopic="weer/hum", sValue=str(csvRow[4]), iQOS=0, bRetain=True)
                NodeControl.MQTTPublish(sTopic="weer/temp", sValue=str(csvRow[5]), iQOS=0, bRetain=True)
                NodeControl.MQTTPublish(sTopic="weer/luchtdruk", sValue=str(csvRow[6]), iQOS=0, bRetain=True)
                NodeControl.MQTTPublish(sTopic="weer/wind-gem", sValue=str(csvRow[7]), iQOS=0, bRetain=True)
                NodeControl.MQTTPublish(sTopic="weer/wind-max", sValue=str(csvRow[8]), iQOS=0, bRetain=True)
                NodeControl.MQTTPublish(sTopic="weer/wind-richt", sValue=str(csvRow[9]), iQOS=0, bRetain=True)
                NodeControl.MQTTPublish(sTopic="weer/rain", sValue=str(csvRow[10]), iQOS=0, bRetain=True)
                NodeControl.MQTTPublish(sTopic="weer/rain-24h", sValue=str(Rain24H), iQOS=0, bRetain=True)
                NodeControl.MQTTPublish(sTopic="weer/rain-1h", sValue=str(Rain1H), iQOS=0, bRetain=True)
            else:
                pass # we wachten op de volgende ronde, toeval dat het bestand nu niet bestaat de smartmeter checked dit elke 10 sec. dus de volgende keer is ie er wel
        except Exception as exp:
            NodeControl.log.warning(
                "Can not read raw weather data. Path: %s, error: %s." % (sPath, traceback.format_exc()))
    else:
        NodeControl.log.warning("No [weather] csvPath found, can not read raw weather data!")


def get_last_row(csv_filename):
    with open(csv_filename, 'rb') as f:
        reader = csv.reader(f)
        lastline = reader.next()
        for line in reader:
            lastline = line
        return lastline