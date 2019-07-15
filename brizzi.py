import logging
from smartcard.System import readers
from smartcard.util import *

'''
https://stackoverflow.com/questions/7621897/python-logging-module-globally
'''
def setup_custom_logger(name):
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger
    
'''
main logger
'''    
LOGGER_MAIN = setup_custom_logger("brizzi_root")

'''
class for brizzi transaction
'''
class ACR_Brizzi:

    '''
    pdu
    '''
    SAMCARD_SELECT = "00A4040C09A00000000000000011"
    PICC_SELECT_AID1 = "5A010000"
    PICC_GET_CARD_NUMBER = "BD00000000170000" 
    PICC_GET_CARD_STATUS = "BD01000000200000" 
    PICC_SELECT_AID3 = "5A030000" 
    PICC_REQUEST_KEY_CARD = "0A00"
    PICC_GET_CARD_UID = "FFCA000000"

    def __init__(self, logger=None):
        try:
            self._logger = logger
            
            # get connected readers
            self._readers = readers()
            self._logger and self._logger.debug(self._readers)
            
            # assign to sam and picc interface
            self._reader_picc = self._readers[0]
            self._reader_sam = self._readers[1]
            
            # create and open connection
            self._reader_picc_connection = self._reader_picc.createConnection()
            self._reader_sam_connection = self._reader_sam.createConnection()
            
            self._reader_picc_connection.connect()
            self._reader_sam_connection.connect()
            
            self._logger and self._logger.debug("Initializing picc and samcard reader OK")
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            
    def closeConnection(self):
        try:
            try:
                self._reader_picc_connection.disconnect()
            except:
                pass
                
            try:    
                self._reader_sam_connection.disconnect()
            except:
                pass
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            
    def sendAPDU(self, apdu_text=None, to_sam=True):
        try:
            if to_sam:
                self._logger and self._logger.debug("Transmit to SAMCARD = {}".format(apdu_text))
                data, sw1, sw2 = self._reader_sam_connection.transmit(toBytes(apdu_text))
            else:
                self._logger and self._logger.debug("Transmit to PICC = {}".format(apdu_text))
                data, sw1, sw2 = self._reader_picc_connection.transmit(toBytes(apdu_text))
                
            self._logger and self._logger.debug("Reply = {}\r\nSW1 SW2{}".format(toHexString(data), toHexString(sw1), toHexString(sw2)))
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            data = sw1 = sw2 = None
            
        return data, sw1, sw2

'''
# define the APDUs used in this script
SELECT = toBytes("00A4040C09A00000000000000011")
SELECT_AID1 = toBytes("5A010000")
GET_CARD_NUMBER = toBytes("BD00000000170000") 
GET_CARD_STATUS = toBytes("BD01000000200000") 
SELECT_AID3 = toBytes("5A030000") 
REQUEST_KEY_CARD = toBytes("0A00")
GET_CARD_UID = toBytes("FFCA000000" )

# get all the available readers
r = readers()
print("Available readers:", r) 

# samcard
sam_reader = r[1]
print("Using:", sam_reader)

sam_connection = sam_reader.createConnection()
sam_connection.connect()

data, sw1, sw2 = sam_connection.transmit(SELECT)
print(toHexString(data))
print("Select Applet: %02X %02X" % (sw1, sw2))

# picc
picc_reader = r[0]
print("Using:", picc_reader)

picc_connection = picc_reader.createConnection()
picc_connection.connect()

data, sw1, sw2 = picc_connection.transmit(SELECT_AID1)
print(toHexString(data))
print("Select Applet: %02X %02X" % (sw1, sw2))

data, sw1, sw2 = picc_connection.transmit(GET_CARD_NUMBER)
print(toHexString(data))
print("Select Applet: %02X %02X" % (sw1, sw2))

data, sw1, sw2 = picc_connection.transmit(GET_CARD_STATUS)
print(toHexString(data))
print("Select Applet: %02X %02X" % (sw1, sw2))

data, sw1, sw2 = picc_connection.transmit(SELECT_AID3)
print(toHexString(data))
print("Select Applet: %02X %02X" % (sw1, sw2))

data, sw1, sw2 = picc_connection.transmit(REQUEST_KEY_CARD)
print(toHexString(data))
print("Select Applet: %02X %02X" % (sw1, sw2))

data, sw1, sw2 = picc_connection.transmit(GET_CARD_UID)
print(toHexString(data))
print("Select Applet: %02X %02X" % (sw1, sw2))

sam_connection.disconnect()
picc_connection.disconnect()
'''

readerx = ACR_Brizzi(LOGGER_MAIN)
readerx.sendAPDU(readerx.SAMCARD_SELECT)
readerx.closeConnection()
