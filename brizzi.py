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
                
            self._logger and self._logger.debug("Reply = %s\r\nSW1 SW2 = %02X%02X" % (toHexString(data), sw1, sw2))
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            data = sw1 = sw2 = None
            
        return data, sw1, sw2
        
    def SAM_select(self):
        try:
            _, sw1, sw2 = self.sendAPDU(self.SAMCARD_SELECT)
            select_result = sw1 == 0x90 and sw2 == 0
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            select_result = False
        return select_result
        
    def cardSelectAID1(self):
        try:
            data, sw1, sw2 = self.sendAPDU(self.PICC_SELECT_AID1, False)
            select_result = sw1 == 0x90 and sw2 == 0 and data[0] == 0
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            select_result = False
        return select_result

readerx = ACR_Brizzi(LOGGER_MAIN)
readerx.SAM_select()
readerx.cardSelectAID1()
readerx.closeConnection()
