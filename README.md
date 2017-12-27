# bliknet PiLogger
Raspberry Pi Logger application based on Python Twisted and MQTT.
Provides logging and publishing of:
* PVData (SBFSpot data from PV SMA);
* P1 Smartmeter.

Interfaces with Arduino nodes (PIR events and RGB Lights)

Work in progess

Todo:
* Remove pywws (moved to Bliknet weatherstation)
* Rewrite buslistner (serial), Remove Arduino Mega
* Remove SBFspotUpload zie https://pvoutput.org/help.html#api-addoutput
* Cleanup code
* Minimal Docs
* Fabric installation
* Koppel circulatiepomp
