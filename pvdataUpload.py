__author__ = 'geurt'
import sqlite3
import time
import traceback


"""
Read's PV data from SBFSpot database and publish it to MQTT 
"""

def doUpdate(NodeControl):
    if NodeControl.nodeProps.has_option('pvdata', 'smaDBPath'):
        sDBPath = NodeControl.nodeProps.get('pvdata', 'smaDBPath')
        UploadPVData(NodeControl, sDBPath)
    else:
        NodeControl.log.warning("[pvdata] smaDBPath not found, no PVData Upload!")


def UploadPVData(NodeControl, sDBPath):
    curdatetime = time.time()
    try:
        NodeControl.log.debug("trying to read PV data from %s" % sDBPath)
        con = sqlite3.connect(sDBPath, detect_types=sqlite3.PARSE_DECLTYPES)
        cur = con.cursor()
        # eerst het vermogen
        cur.execute("SELECT TimeStamp, Power FROM DayData ORDER BY TimeStamp DESC LIMIT 1")
        rows = cur.fetchall()
        readTime = 0
        readPower = 0
        for row in rows:
            print row
            readTime = row[0]
            readPower = row[1]
        if ( readTime > (curdatetime - 600)):
            # waarde mag max 600 sec. oud zijn anders sturen we 0 om aan te geven dat de omvormer uit staat
            NodeControl.log.debug(
                "Read power: %s is from %s, current time is %s. Less dan 600 sec.old, publish to MQTT" % (
                    readPower, readTime, curdatetime))
            NodeControl.MQTTPublish(sTopic="pvdata/power", sValue=str(readPower), iQOS=0, bRetain=True)
        else:
            NodeControl.log.debug(
                "Read power: %s is from %s, current time is %s. Older dan 600 sec., publish 0 to MQTT" % (
                    readPower, readTime, curdatetime))
            NodeControl.MQTTPublish(sTopic="pvdata/power", sValue="0", iQOS=0, bRetain=True)
            # nu de energy
        cur.execute("SELECT TimeStamp, EToday, Temperature FROM SpotData ORDER BY TimeStamp DESC LIMIT 1")
        rows = cur.fetchall()
        for row in rows:
            # TODO at 0:00 start at zero
            # TODO temp waarde mag niet oude dan 600 sec zijn anders 0
            NodeControl.MQTTPublish(sTopic="pvdata/energy", sValue=str(row[1]), iQOS=0, bRetain=True)
            NodeControl.MQTTPublish(sTopic="pvdata/temp", sValue=str(row[2]), iQOS=0, bRetain=True)
        con.close()
        NodeControl.log.debug("Read from PVoutput DB: %s and upload succes" % sDBPath)
    except Exception, exp:
        NodeControl.log.warning("Can not upload pvdata. DBPath: %s, error: %s." % (sDBPath, traceback.format_exc()))