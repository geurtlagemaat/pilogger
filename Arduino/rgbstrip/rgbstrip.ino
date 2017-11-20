#define pinCONTROL 12   // de pin waarmee we de RS 485 mee besturen (pin 18 fysiek)
// #define DEBUG
byte message[] = {0x00, 0x39, 0x39, 0x39, 0x30, 0x30, 0x32, 0x06, 0x30, 0x30, 0x2b, 0x33, 0x30, 0x30, 0x31, 0x04, 0x30, 0x30, 0x30, 0x04};

char MasterNode[4] = "112";
char myNodeID[4] = "752";

const byte pirIntPin = 2;
byte pirAlert = 0;
byte pirAlertRep = 0;
byte pirAlertAck = 0;

int ledR=0;                           
int ledG=0;                           
int ledB=0;

int dyncolorschemes[][6] = {  // array with dynamic colors, refers to colorschemes array time between colorschemes is set by DynColorInterva
  {0,1,2,3,4,0},
  {0,2,4,6,8,0},
  {0,1,2,3,4,0}
};

int colorschemes[][3] = {
  {5,1,1}, // RGB
  {6,2,2},
  {7,3,3},
  {8,4,4},
  {9,5,5},
  {10,6,6},
  {11,7,7},
  {12,8,8},
  {13,9,9},
  {14,10,10},
};

int DynColorScheme = -1;
int DynColorSchemeStep = -1;
long DynColorInterval = 1500; 
long DynColorPrevUpdateMillis = 0;

String readString;

void setup() {
  message[1] = MasterNode[0];
  message[2] = MasterNode[1];
  message[3] = MasterNode[2];
  
  message[4] = myNodeID[0];
  message[5] = myNodeID[1];
  message[6] = myNodeID[2];
  // RS485 control
  pinMode(pinCONTROL,OUTPUT);
  digitalWrite(pinCONTROL,LOW);
  
  Serial.begin(9600);
  #ifdef DEBUG
    Serial.print("NodeID: ");
    Serial.write(myNodeID, sizeof(myNodeID));
    Serial.println("."); 
  #endif
  // setup PIR interrupt
  pinMode(pirIntPin, INPUT);
  attachInterrupt(digitalPinToInterrupt(pirIntPin), cbPirAlert, FALLING);
  // initial RGB strip state
  ledG = 1023; // set LED to green (init ok)
  checkRGBLED();
  // Alert();
}

void loop() {
  char str[19];   // de hele inkomende message
  byte byte_receive;
  int iCalcChecksum;
  byte state = 0;
  char toNodeID[4];
  char readChecksum[4];

  // check for incoming messages
  int i = 0;
  if (Serial.available()) {
    state = 0;
    iCalcChecksum = 0;
    delay(50); // allows all serial sent to be received together
    while (Serial.available()) {
      byte_receive = Serial.read();
      readString += byte_receive;
      if (byte_receive == 00) {
        state = 1;
      }
      if ( (state == 1) && (i < 20) ) {
        str[i++] = byte_receive; 
        if (i < 17) {
          iCalcChecksum = iCalcChecksum + byte_receive;
        }
      }
    }
    str[i++] = '\0';
  }
  // Do Pull Messages 
  if (i > 19) {  // some hope for a incoming message...
    readChecksum[0] = str[16];
    readChecksum[1] = str[17];
    readChecksum[2] = str[18];
    readChecksum[3] = '\0';
    String sReadChar (readChecksum);
    
    toNodeID[0] = str[1];
    toNodeID[1] = str[2];
    toNodeID[2] = str[3];
    toNodeID[3] = '\0';

#ifdef DEBUG
    Serial.print("read Checksum: ");
    Serial.println(readChecksum);

    Serial.print("calculated checksum: ");
    Serial.println(iCalcChecksum);
    
    Serial.print("toNodeID: ");
    Serial.println(toNodeID);
#endif
    String sToNodeID(toNodeID);
    String sMyNodeID(myNodeID);
    if (sReadChar.toInt() == iCalcChecksum) {
      // valid checksum
      if ( (sToNodeID == sMyNodeID) ) {
        // voor onze node
        char nodeFunc[3];
        nodeFunc[0]=str[8];
        nodeFunc[1]=str[9];
        nodeFunc[2]='\0';
        String sNodeFunc(nodeFunc);
    
        char nodeValue[4];
        nodeValue[0]=str[12];
        nodeValue[1]=str[13];
        nodeValue[2]=str[14];
        nodeValue[3]='\0';
        String sNodeValue(nodeValue);
        if (str[7] == 5) {  
#ifdef DEBUG
          Serial.println("message ENQ!");
          Serial.print("functie: ");
          Serial.println(sNodeFunc);
#endif          
          if (sNodeFunc=="01"){
            message[7] = 0x05;  // QoS=1, need ack
            message[8] = 0x30;
            message[9] = 0x31;  // pirState is function 01 
            BoolValueToMessage(!digitalRead(pirIntPin));
            SendMessage();
            pirAlertRep=1;
          }else if ( (sNodeFunc=="50") || (sNodeFunc=="51") or (sNodeFunc=="52") ){  
            // individual colors 50 = RED, 51 = GREEN, 52 = BLUE
            SetRGBValue(sNodeFunc, sNodeValue.toInt());
            //message[7] = 0x06;  // ACK
            //message[8] = str[8];
            //message[9] = str[9];
            //SendMessage();
          }
          else if (sNodeFunc=="53"){
            // shortcut notation 000 to 999 0e position R, 1e position G, 2e position B
            SetRGBValues(nodeValue[0]-'0', nodeValue[1]-'0', nodeValue[2]-'0');
            // no ack's
          }
          else if (sNodeFunc=="54"){
            // Preset colors 000 to 999 defined color schemes
            SetColorScheme(sNodeValue.toInt());
          }
          else if (sNodeFunc=="55"){
            // Preset colors 000 to 999 Dynamic Color Schemes
            DynColorScheme = sNodeValue.toInt();
            DynColorSchemeStep = -1;
          }
          else if (sNodeFunc=="56"){
            if (sNodeValue.toInt()==1){
              SilentNightWave();
            }
            else if (sNodeValue.toInt()==2){
              Alert();   
            }
          }
        }
        else if (str[7] == 6) {
#ifdef DEBUG
          Serial.println("message ACK!");
#endif
          if (sNodeFunc=="01"){
            pirAlertAck=1; // TODO time out retry
          }
        } // msg ACK
        else if (str[7] == 0x15) {
#ifdef DEBUG
          Serial.println("message NACK!");
#endif
          // resend
          SendMessage();
        }; // if NACK
      }; // if this node
    }; // if checksum
  }; // if i > 19

  // Checking states & Push messages
  if (pirAlert){
    if (!pirAlertRep){
      message[7] = 0x05;  // QoS=1, need ack
      message[8] = 0x30;
      message[9] = 0x31;  // pirState is function 01 
      BoolValueToMessage(true);
      SendMessage();
      pirAlertRep=1;
    }
    if (digitalRead(pirIntPin)){ // nc PIR switch dus high is geen alarm
      pirAlert=0;
      pirAlertRep=0;
    }
  }
  CheckDynColorSchemes();
}

void cbPirAlert(){
  pirAlert = 1;
}

void SendMessage() {
  InsertMessageChecksum();
  UCSR0A=UCSR0A |(1 << TXC0);
  digitalWrite(pinCONTROL,HIGH);
  delay(1);
  Serial.write(message, sizeof(message));
  while (!(UCSR0A & (1 << TXC0)));
  digitalWrite(pinCONTROL,LOW);
  delay(10);
}

void InsertMessageChecksum() {
  // bereken checksum door message array pos 1 t/m. 15 op te tellen. Plaats het checksum getal in de message
  int iChecksum = 0;
  for (int i = 1; i < 16; i++) {
    iChecksum = iChecksum + message[i];
  } // for i

  char newChecksum[4];
  sprintf (newChecksum, "%03i", iChecksum);

  message[16] = newChecksum[0];
  message[17] = newChecksum[1];
  message[18] = newChecksum[2];
} // CalcMessageChecksum

void BoolValueToMessage(boolean Value) {
  message[10] = 0x2B;
  message[11] = 0x33;
  if (Value){
    message[12] = 0x30;
    message[13] = 0x30;
    message[14] = 0x31;
  }
  else{
    message[12] = 0x30;
    message[13] = 0x30;
    message[14] = 0x30;   
  }
}

void SetRGBValue(String sNodeFunc, int iNodeValue){
  if (sNodeFunc=="50"){
    // max value in msg is 999, full LED brightness = 1023
    ledR = round(iNodeValue * 1.024);
  }
  else if (sNodeFunc=="51"){
    ledG = round(iNodeValue * 1.024);
  }
  else if (sNodeFunc=="52"){
    ledB = round(iNodeValue * 1.024); 
  }
  checkRGBLED();
}

void SetRGBValues(int iRValue, int iGValue, int iBValue){
#ifdef DEBUG
  Serial.println("SetRGBValues");
  Serial.print("RValue: ");
  Serial.print(iRValue);
  Serial.print(", GValue: ");
  Serial.print(iGValue);
  Serial.print(", BValue: ");
  Serial.println(iBValue);
#endif
  // NodeFunc 53 set all three values in 1 messages, value range 0 - 9
  ledR = round(iRValue * 113.7);
  ledG = round(iGValue * 113.7);
  ledB = round(iBValue * 113.7); 
  checkRGBLED();
}

void CheckDynColorSchemes(){
  /* a dynamic color schema has max 5 ColorSchema's. Interval between ColorScheme is 1 sec. */
  if (DynColorScheme!=-1){
    if (DynColorSchemeStep < 5){
#ifdef DEBUG
  Serial.println("CheckDynColorSchemes");
  Serial.print(", DynColorScheme: ");
  Serial.print(DynColorScheme);
  Serial.print(", DynColorSchemeStep: ");
  Serial.println(DynColorSchemeStep);
#endif  
      unsigned long currentMillis = millis();
      if(currentMillis - DynColorPrevUpdateMillis > DynColorInterval) {
        // next step
        DynColorPrevUpdateMillis = currentMillis;
        DynColorSchemeStep=DynColorSchemeStep+1;
        SetColorScheme(dyncolorschemes[DynColorScheme][DynColorSchemeStep]);
#ifdef DEBUG
  Serial.print("CheckDynColorSchemes NEXT, nr: ");
  Serial.println(DynColorSchemeStep);
#endif 
      }
    }
  }
}

void SetColorScheme(int iSchemeNr){
#ifdef DEBUG
  Serial.print("SetColorScheme, nr: ");
  Serial.println(iSchemeNr);
#endif 
  ledR = colorschemes[iSchemeNr][0];
  ledG = colorschemes[iSchemeNr][1];
  ledB = colorschemes[iSchemeNr][2];
  checkRGBLED();
}

void checkRGBLED(){
#ifdef DEBUG
  Serial.println("checkRGBLED");
  Serial.print("RValue: ");
  Serial.print(ledR);
  Serial.print(", GValue: ");
  Serial.print(ledG);
  Serial.print(", BValue: ");
  Serial.println(ledB);
#endif
  analogWrite(10,ledR);
  analogWrite(9,ledG);
  analogWrite(11,ledB);
}

// effects
// use delay in dynamic RGB functions for the best effects
void SilentNightWave(){
  for (int i = 0; i < 175 - 1; i++){ 
    ledR = i;
    ledG = round(i/5);
    ledB = round(i/5);
    checkRGBLED();
    delay(20);
  }
  for (int i = 175; i > 5; i--){ 
    ledR = i;
    ledG = round(i/5);
    ledB = round(i/5);
    checkRGBLED();
    delay(20);
  }
}

void Alert(){
  for (int i = 0; i < 175 - 1; i++){ 
    ledR = 255;
    ledG = 0;
    ledB = 0;
    checkRGBLED();
    delay(100);
    ledR = 0;
    ledG = 0;
    ledB = 255;
    checkRGBLED();
    delay(100);
    ledR = 255;
    ledG = 255;
    ledB = 255;
  }
}
