__author__ = 'geurt'
import cgi
import datetime
import ftplib
import os
import os.path
import traceback

import wiringpi as wiringpi
from twisted.internet import reactor
from twisted.web.resource import Resource


class busPage(Resource):
    def __init__(self, NodeControl):
        Resource.__init__(self)
        self._NodeControl = NodeControl

    def render_GET(self, request):
        # Quick GET handler to get IP Cam events
        self._NodeControl.log.debug("Bus GET action, request: %s" % request)
        sCamRaw = None
        if "cam" in request.args:
            sCamRaw = request.args.get('cam')[0]
            self._NodeControl.log.debug("Found cam param in request: %s" % sCamRaw)
            # check cam events
        if ( (sCamRaw != None) and (sCamRaw.upper() == "CAMVOOR") ):
            self._NodeControl.log.debug("CAMVOOR event.")
            self._NodeControl.MQTTPublish(sTopic="buitencams/cam1lastevent", sValue=str(datetime.datetime.now()),
                                          iQOS=0, bRetain=False)
            self.uploadCamImg('OrianaCam1')
            return '<html><body><p>Welcome to BliknetNode: %s. Event is processed.</p></body></html>' % self._NodeControl.nodeID
        elif ( (sCamRaw != None) and (sCamRaw.upper() == "CAMACHTER") ):
            self._NodeControl.log.debug("CAMACHTER event.")
            self._NodeControl.MQTTPublish(sTopic="buitencams/cam2lastevent", sValue=str(datetime.datetime.now()),
                                          iQOS=0, bRetain=False)
            self.uploadCamImg('OrianaCam2')
            return '<html><body><p>Welcome to BliknetNode: %s. Event is processed.</p></body></html>' % self._NodeControl.nodeID
        else:
            return '<html><body><p>Welcome to BliknetNode:%s</p><form method="POST">Who are you: <input name="ipFromNodeID" type="text" />, function: <input name="ipFunction" type="text" />, function value: <input name="ipFunctionValue" type="text" /><input type="submit" value="Submit"></form></body></html>' % self._NodeControl.nodeID

    def render_POST(self, request):
        # Quick and dirty POST handler to provide communication with Arduino serial nodes via Ethernet Shield
        # return '<html><body><p>You submitted function: %s</p><p>Function value: %s</p></body></html>' % (cgi.escape(request.args["ipFunction"][0]),cgi.escape(request.args["ipFunctionValue"][0]))
        # print "ipFromNodeID: %s: ipFunction: %s, ipFunctionValue: %s" % (cgi.escape(request.args["ipFromNodeID"][0]),cgi.escape(request.args["ipFunction"][0]),cgi.escape(request.args["ipFunctionValue"][0]))
        sFromNodeID = None
        sFunction = None
        fFunctionValueValueSign = None
        fFunctionValueDecPos = None
        sFunctionValue = None

        if "ipFromNodeID" in request.args:
            sFromNodeID = cgi.escape(request.args["ipFromNodeID"][0]).lstrip("0")
        if "ipFunction" in request.args:
            sFunction = cgi.escape(request.args["ipFunction"][0]).lstrip("0")
        if "ipFunctionValueSign" in request.args:
            fFunctionValueValueSign = cgi.escape(request.args["ipFunctionValueSign"][0]).lstrip("0")
        if "ipFunctionValueDecPos" in request.args:
            fFunctionValueDecPos = cgi.escape(request.args["ipFunctionValueDecPos"][0]).lstrip("0")
        if "ipFunctionValue" in request.args:
            sFunctionValue = cgi.escape(request.args["ipFunctionValue"][0]).lstrip("0")

        self._NodeControl.log.debug(
            "Bus POST action. ipFromNodeID: %s, ipFunction: %s, ipFunctionValueSign: %s, ipFunctionValueDecPos: %s, ipFunctionValue: %s." % (
                sFromNodeID, sFunction, fFunctionValueValueSign, fFunctionValueDecPos, sFunctionValue))

        # check data from deur keypad node 1
        """
        FromNodeID 001
            sFunction 001: deurcode
            sFunction 002: RFID
            sFunction 003: deurbel
            sFunction 004: tamper """
        if ( (sFromNodeID == "1") and (sFunction == "1") and (sFunctionValue == "1") ):
            self._NodeControl.log.debug("Deuropen signal (keypad)")
            self._NodeControl.MQTTPublish(sTopic="deur/lastkeyopen", sValue=str(datetime.datetime.now()), iQOS=0,
                                          bRetain=False)
            if self._NodeControl.nodeProps.has_option('dooropener',
                                                      'active') and self._NodeControl.nodeProps.getboolean('dooropener',
                                                                                                           'active'):
                self._NodeControl.log.debug("Deuropen signal (keypad), GPIO 17 on, deuropener")
                idoorUnlockTime = 5
                if self._NodeControl.nodeProps.has_option('dooropener', 'unlockTime'):
                    idoorUnlockTime = float(self._NodeControl.nodeProps.get('dooropener', 'unlockTime'))
                wiringpi.digitalWrite(17, 1)
                reactor.callLater(idoorUnlockTime, self.releaseDoorLockEvent)
            else:
                self._NodeControl.log.debug("NOT opening the door (function not active)")
        if ( (sFromNodeID == "1") and (sFunction == "2") and (sFunctionValue == "1") ):
            self._NodeControl.log.debug("Deuropen signal (RFID)")
            self._NodeControl.MQTTPublish(sTopic="deur/lastrfidopen", sValue=str(datetime.datetime.now()), iQOS=0,
                                          bRetain=False)
            if self._NodeControl.nodeProps.has_option('dooropener',
                                                      'active') and self._NodeControl.nodeProps.getboolean('dooropener',
                                                                                                           'active'):
                self._NodeControl.log.debug("Deuropen signal (RFID), GPIO 17 on, deuropener")
                idoorUnlockTime = 5
                if self._NodeControl.nodeProps.has_option('dooropener', 'unlockTime'):
                    idoorUnlockTime = float(self._NodeControl.nodeProps.get('dooropener', 'unlockTime'))
                wiringpi.digitalWrite(17, 1)
                reactor.callLater(idoorUnlockTime, self.releaseDoorLockEvent)
            else:
                self._NodeControl.log.debug("NOT opening the door (function not active)")
        if ( (sFromNodeID == "1") and (sFunction == "3") and (sFunctionValue == "1") ):
            self._NodeControl.log.debug("Deurbel signal.")
            self._NodeControl.MQTTPublish(sTopic="deur/lastring", sValue=str(datetime.datetime.now()), iQOS=0,
                                          bRetain=False)

    def releaseDoorLockEvent(self):
        self._NodeControl.log.debug("releaseDoorLockEvent")
        wiringpi.digitalWrite(17, 0)
        self._NodeControl.log.debug("Deur GPIO 17 off")

    def uploadCamImg(self, sCAMID):
        # Tester to send IP Cam image to MQTT when motion is detected
        if ((self._NodeControl.nodeProps.has_option('camUploader', 'active')) and (
            self._NodeControl.nodeProps.getboolean('camUploader', 'active')) ):
            self._NodeControl.log.debug("uploadCamImg event, camUploader is active")
            sFTPServer = self._NodeControl.nodeProps.get('camUploader', 'NASServerURL')
            sFTPServerUser = self._NodeControl.nodeProps.get('camUploader', 'NASServerUser')
            sFTPServerPwd = self._NodeControl.nodeProps.get('camUploader', 'NASServerPassword')
            ftp = None
            try:
                try:
                    ftp = ftplib.FTP(sFTPServer, sFTPServerUser, sFTPServerPwd)
                    self._NodeControl.log.debug("NAS Login succes")
                    if (self._NodeControl.nodeProps.has_option('camUploader', 'NASDir')):
                        ftp.cwd(self._NodeControl.nodeProps.get('camUploader', 'NASDir'))
                    iNewestStamp = 0
                    sNewestFile = None
                    data = []
                    ftp.dir(data.append)
                    for line in data:
                        col = line.split()
                        sFileName = col[8]
                        if sCAMID in sFileName:
                            sDateTimePart = sFileName[27:41]
                            if int(sDateTimePart) > int(iNewestStamp):
                                sNewestFile = sFileName
                                iNewestStamp = int(sDateTimePart)
                    self._NodeControl.log.debug("Newest file for camera: %s, is: %s because of its date time: %s." % (
                        sCAMID, sNewestFile, str(iNewestStamp)))
                    try:
                        ftp.retrbinary('RETR %s' % sNewestFile,
                                       open(self._NodeControl.datadir + sNewestFile, 'wb').write)
                        f = open(self._NodeControl.datadir + sNewestFile)
                        imagestring = f.read()
                        byteArray = bytearray(imagestring)
                        self._NodeControl.MQTTPublish(sTopic="buitencams/" + sCAMID, sValue=byteArray, iQOS=0,
                                                      bRetain=True)
                        self._NodeControl.log.debug("***Downloaded*** %s and send to MQTT " % sNewestFile)
                    except ftplib.err_perm:
                        self._NodeControl.log.warning("Error: cannot read file %s" % sNewestFile)
                        os.unlink(sNewestFile)
                except Exception, exp:
                    self._NodeControl.log.warning(
                        "Unable to connect to Cam NAS server at: %s, error: %s." % (sFTPServer, traceback.format_exc()))
            finally:
                if ftp != None:
                    ftp.quit()

class busListner(Resource):
    def __init__(self, NodeControl):
        Resource.__init__(self)
        self._NodeControl = NodeControl
        pass

    def getChild(self, name, request):
        return busPage(self._NodeControl)


