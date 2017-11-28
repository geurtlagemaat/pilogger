from bliknetlib import nodeControl

__author__ = 'geurt'

import smartmeterUpload
import weatherUpload
import pvdataUpload
import busListner
import datetime
from twisted.web.server import Site
from twisted.internet import reactor
from twisted.internet import task
import traceback
import wiringpi as wiringpi
# from serialNodesController import SerialNodesController

def weatherUploadEvent(NodeControl):
    weatherUpload.doUpdate(NodeControl)


def pvdataUploadEvent(NodeControl):
    pvdataUpload.doUpdate(NodeControl)

if __name__ == '__main__':
    now = datetime.datetime.now()
    oNodeControl = nodeControl.nodeControl(r'settings/bliknetnode.conf')
    oNodeControl.log.info("BliknetNode: %s starting at: %s." % (oNodeControl.nodeID, now))

    # mySerialNodesController = SerialNodesController(oNodeControl)

    # the smartmeter task, triggered by to serial line event
    if oNodeControl.nodeProps.has_option('smartmeter', 'active') and oNodeControl.nodeProps.getboolean('smartmeter',
                                                                                                       'active'):
        sm_wrap = smartmeterUpload.SmartMeterWrapper(oNodeControl)
    else:
        oNodeControl.log.info("Smartmeter upload task not active.")

    # weather upload task
    if oNodeControl.nodeProps.has_option('weather', 'active') and oNodeControl.nodeProps.getboolean('weather',
                                                                                                    'active'):
        iWeatherUploadInt = 20
        if oNodeControl.nodeProps.has_option('weather', 'uploadInterval'):
            iWeatherUploadInt = oNodeControl.nodeProps.getint('weather', 'uploadInterval')
        oNodeControl.log.info("Weather upload task active, upload interval: %s" % str(iWeatherUploadInt))
        l = task.LoopingCall(weatherUploadEvent, oNodeControl)
        l.start(iWeatherUploadInt)
    else:
        oNodeControl.log.info("Weather upload task not active.")

    # pvdata upload task
    if oNodeControl.nodeProps.has_option('pvdata', 'active') and oNodeControl.nodeProps.getboolean('pvdata', 'active'):
        iPvDataUploadInt = 300
        if oNodeControl.nodeProps.has_option('pvdata', 'uploadInterval'):
            iPvDataUploadInt = oNodeControl.nodeProps.getint('pvdata', 'uploadInterval')
        oNodeControl.log.info("PVData upload task active, upload interval: %s" % str(iPvDataUploadInt))
        l = task.LoopingCall(pvdataUploadEvent, oNodeControl)
        l.start(iPvDataUploadInt)
    else:
        oNodeControl.log.info("PVData upload task not active.")

    # HTTP server resource (listner)
    if oNodeControl.nodeProps.has_option('httpBuslistner',
                                         'httpBuslistnerActive') and oNodeControl.nodeProps.getboolean('httpBuslistner',
                                                                                                       'httpBuslistnerActive'):
        ibusPort = 8880
        if oNodeControl.nodeProps.has_option('httpBuslistner', 'port'):
            ibusPort = oNodeControl.nodeProps.getint('httpBuslistner', 'port')
        oNodeControl.log.info("httpBuslistner active, port: %s" % str(ibusPort))
        root = busListner.busListner(oNodeControl)
        factory = Site(root)
        reactor.listenTCP(ibusPort, factory)
    else:
        oNodeControl.log.info("httpBuslistner NOT active.")

    if oNodeControl.nodeProps.has_option('dooropener', 'active') and oNodeControl.nodeProps.getboolean('dooropener',
                                                                                                       'active'):
        try:
            wiringpi.wiringPiSetupGpio()
            wiringpi.pinMode(17, 1)
        except Exception, exp:
            oNodeControl.log.error("Init busPage error: %s" % traceback.format_exc())

    if oNodeControl.nodeProps.has_option('watchdog', 'circusWatchDog'):
        if oNodeControl.nodeProps.getboolean('watchdog', 'circusWatchDog') == True:
            oNodeControl.circusNotifier.start()

    reactor.run()