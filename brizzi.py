import logging
import binascii
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
    SAMCARD_AUTH_KEY = "80B0000020{card_number:0<16.16}{card_uid:0<14.14}FF0000030080000000{key_card:0<16.16}"
    PICC_SELECT_AID1 = "5A010000"
    PICC_GET_CARD_NUMBER = "BD00000000170000" 
    PICC_GET_CARD_STATUS = "BD01000000200000" 
    PICC_SELECT_AID3 = "5A030000" 
    PICC_REQUEST_KEY_CARD = "0A00"
    PICC_GET_CARD_UID = "FFCA000000"
    PICC_CARD_AUTH = "AF{:0<32.32}"
    PICC_GET_LAST_TRANSACTION_DATE = "BD03000000070000"
    PICC_GET_BALANCE = "6C00"
    PICC_DEBET_BALANCE = "DC00{:0<6.6}00"
    PICC_COMMIT_TRANSACTION = "C7"
    PICC_ABORT_TRANSACTION = "A7"

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
            
            # connect to picc only to check the card present or not
            # self._reader_picc_connection.connect()
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
                
            self._logger and self._logger.debug("[SW1SW2] : DATA = [%02X%02X] : %s" % (sw1, sw2, toHexString(data)))
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            data = sw1 = sw2 = None
            
        return data, sw1, sw2
        
    def SAMSelect(self):
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
        
    def cardGetCardNumber(self):
        try:
            data, sw1, sw2 = self.sendAPDU(self.PICC_GET_CARD_NUMBER, False)
            return data[4:12]
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return None
            
    def cardGetCardStatus(self):
        try:
            data, sw1, sw2 = self.sendAPDU(self.PICC_GET_CARD_STATUS, False)
            return data[4:6] == [0x61, 0x61]
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return False
            
    def cardSelectAID3(self):
        try:
            data, sw1, sw2 = self.sendAPDU(self.PICC_SELECT_AID3, False)
        except Exception as err:
            pass
            self._logger and self._logger.error(err)   

    def cardRequestKeyCard(self):
        try:
            data, sw1, sw2 = self.sendAPDU(self.PICC_REQUEST_KEY_CARD, False)
            return data[1:].extend([sw1,sw2])
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return None
                      
    def cardGetUID(self):
        try:
            data, sw1, sw2 = self.sendAPDU(self.PICC_GET_CARD_UID, False)
            return data
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return None
            
    def SAMAuthenticateKey(self, card_number_in, card_uid_in, key_card_in):
        try:
            data, sw1, sw2 = self.sendAPDU(self.SAMCARD_AUTH_KEY.format(card_number=card_number_in, card_uid=card_uid_in, key_card=key_card_in))
            return data
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return None
            
    def cardAuthenticate(self, random_key_in):
        try:
            data, sw1, sw2 = self.sendAPDU(self.PICC_CARD_AUTH.format(random_key=random_key_in), False)
            return data
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return None
            
    def cardGetLastTransactionDate(self):
        try:
            data, sw1, sw2 = self.sendAPDU(self.PICC_GET_LAST_TRANSACTION_DATE, False)
            return data
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return None
            
    def cardGetBalance(self):
        try:
            data, sw1, sw2 = self.sendAPDU(self.PICC_GET_BALANCE, False)
            return int.from_bytes(data[1:5],'big')
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return -1
            
    def cardDebetBalance(self, debet_value=0):
        try:
            data, sw1, sw2 = self.sendAPDU(self.PICC_DEBET_BALANCE.format(binascii.hexlify((debet_value).to_bytes(3,'little')).decode()), False)
            return int.from_bytes(data[1:5],'big')
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return -1
            
    def cardCommitTransaction(self):
        try:
            data, sw1, sw2 = self.sendAPDU(self.PICC_COMMIT_TRANSACTION, False)
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return False
            
    def cardAbortTransaction(self):
        try:
            data, sw1, sw2 = self.sendAPDU(self.PICC_ABORT_TRANSACTION, False)
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return False

if __name__ == "__main__":
    readerx = ACR_Brizzi(LOGGER_MAIN)
    readerx.SAMSelect()
    readerx.cardSelectAID1()
    readerx.cardGetCardNumber()
    readerx.cardGetCardStatus()
    readerx.cardSelectAID3()
    readerx.cardRequestKeyCard()
    readerx.cardGetUID()
    readerx.cardGetLastTransactionDate()
    readerx.cardGetBalance()
    readerx.closeConnection()
