from time import sleep

from bliknetlib import serialMsg
"""
Helper module for various RGB Strip colors and effects.
-sendRGBValue is sending R G and B color values in the values 0-9 (Arduino function 53)
-sendColorScheme (Arduino function 54) is used to send predefined color scheme's
-sendDynColorScheme (Arduino function 55) is used to send predefined dynamic color scheme's
-sendEffectScheme (Arduino function 56) is used to send predefined effects
"""

# RGBValue
QUITNIGHT = "211"
ALERT = "900"
ALLOK = "090"
CONTROLLERREADY="009"
FULLWHITE = "999"
ALLOFF ="000"
FRIENDLYHELLO = "141"

# ColorScheme
COLORSCHEME_QUITNIGHT_01 = 1
COLORSCHEME_QUITNIGHT_02 = 2
COLORSCHEME_QUITNIGHT_03 = 3
COLORSCHEME_QUITNIGHT_04 = 4
COLORSCHEME_QUITNIGHT_05 = 5

# DynColorScheme
DYN_COLORSCHEME_QUITNIGHT_01 = 1
DYN_COLORSCHEME_QUITNIGHT_02 = 2

# Effects
EFFECT_SILENT_NIGHT_WAVE = 1
EFFECT_ALERT = 2

# 50 = RED, 51 = GREEN, 52 = BLUE, 53 SHORTCUT RGB em 54 Preset Silent Night
def sendRGBValue(SerialNodesController, oNodeControl, ToNode, RGBValues):
    myNodeID = oNodeControl.nodeProps.get('system', 'nodeId')
    setRGBMsg = serialMsg.serialMsg(FromAdress=int(myNodeID),
                                    ToAdress=int(ToNode),
                                    Function=int(53),
                                    MsgType=serialMsg.serialMessageType.ENQ)

    if isinstance( RGBValues, ( int, long, str ) ):
        setRGBMsg.MsgValue = RGBValues
        SerialNodesController.SendMessage(setRGBMsg.serialMsgToString())

def sendColorScheme(SerialNodesController, oNodeControl, ToNode, colorSchemeName):
    myNodeID = oNodeControl.nodeProps.get('system', 'nodeId')

    myRGBMsg = serialMsg.serialMsg(FromAdress=int(myNodeID),
                                    ToAdress=int(ToNode),
                                    Function=int(54),
                                    MsgType=serialMsg.serialMessageType.ENQ)
    myRGBMsg.MsgValue=colorSchemeName
    SerialNodesController.SendMessage(myRGBMsg.serialMsgToString())

def sendDynColorScheme(SerialNodesController, oNodeControl, ToNode, dynColorSchemeName):
    myNodeID = oNodeControl.nodeProps.get('system', 'nodeId')

    myRGBMsg = serialMsg.serialMsg(FromAdress=int(myNodeID),
                                    ToAdress=int(ToNode),
                                    Function=int(55),
                                    MsgType=serialMsg.serialMessageType.ENQ)
    myRGBMsg.MsgValue=dynColorSchemeName
    SerialNodesController.SendMessage(myRGBMsg.serialMsgToString())

def sendEffectScheme(SerialNodesController, oNodeControl, ToNode, effectSchemeName):
    myNodeID = oNodeControl.nodeProps.get('system', 'nodeId')

    myRGBMsg = serialMsg.serialMsg(FromAdress=int(myNodeID),
                                    ToAdress=int(ToNode),
                                    Function=int(56),
                                    MsgType=serialMsg.serialMessageType.ENQ)
    myRGBMsg.MsgValue=effectSchemeName
    SerialNodesController.SendMessage(myRGBMsg.serialMsgToString())