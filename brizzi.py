import logging
import binascii
import time
# from smartcard.System import readers
from smartcard.CardConnectionObserver import ConsoleCardConnectionObserver
from smartcard.CardConnection import CardConnection
from smartcard.CardMonitoring import CardMonitor, CardObserver
from smartcard.util import *
# from smartcard.scard import *

# gpio
import RPi.GPIO as GPIO

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
GPIO_CONTROL_MAIN = None


class GPIOControl:
    # pin definition
    pin_buzzer = 21
    pin_gate = 20

    def __init__(self):
        try:
            self.initialize = False

            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)

            # setup pin
            GPIO.setup(self.pin_buzzer, GPIO.OUT)
            GPIO.output(self.pin_buzzer, GPIO.LOW)
            GPIO.setup(self.pin_gate, GPIO.OUT)
            GPIO.output(self.pin_gate, GPIO.LOW)

            self.initialize = True
        except Exception as err:
            pass
            self.initialize = False

    # cleanup gpio
    def gpio_cleanup(self):
        try:
            GPIO.cleanup()
        except:
            pass

    # buzzer on off
    def buzzer_on_off(self, isOn=False):
        GPIO.output(self.pin_buzzer, isOn * GPIO.HIGH)

    # gate on off
    def gate_on_off(self, isOn=False):
        GPIO.output(self.pin_gate, isOn * GPIO.HIGH)

    def buzzer_beep(self, repeat_num=1, delay_ms=200):
        for i in range(0, repeat_num):
            self.buzzer_on_off()
            time.sleep(delay_ms / 1000)
            self.buzzer_on_off(True)
            time.sleep(delay_ms / 1000)

    def gate_open(self, delay_close_ms=6000):
        self.gate_open(True)
        time.sleep(delay_close_ms / 1000)
        self.gate_open()

    def gate_close(self):
        self.gate_on_off()


class BrizziProcessor:
    '''
    pdu
    '''
    SAMCARD_SELECT = "00A4040C09A00000000000000011"
    SAMCARD_AUTH_KEY = "80B0000020{card_number:0<16.16}{card_uid:0<14.14}FF0000030080000000{key_card:0<16.16}"
    SAMCARD_CREATE_HASH = "80B4000058{:0<16.16}{:0<14.14}FF0000030080000000{:0<16.16}{:0<32.32}{:0<20.20}{:0<12.12}{:0<12.12}{:0<12.12}{:0>12.12}{:0<4.4}FFFFFFFF"
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
    PDU_GET_MORE_DATA = "00C00000{:0>2X}"
    PICC_WRITE_LOG = "3B01000000200000{:0<16.16}{:0<16.16}{:0<6.6}{:0<6.6}EB{:0<6.6}{:0<6.6}{:0<6.6}"
    PICC_WRITE_LAST_TRANSACTION = "3D03000000070000{:0<6.6}{:0<8.8}"

    def __init__(self, logger=None, sam_connection=None, picc_connection=None, mid="1122334455667788",
                 tid="aabbccddeeff0000", debug_mode=True):
        try:
            # get setting
            self._logger = logger
            self._mid = mid
            self._tid = tid
            self.initialize = False

            # check sam and picc connection object
            if sam_connection is None or picc_connection is None:
                self._logger and self._logger.error("SAM and or PICC connection is unavailable")
            else:
                # assign to sam and picc interface
                self._reader_picc_connection = picc_connection
                self._reader_sam_connection = sam_connection

                # add observer
                if debug_mode:
                    self._reader_observer = ConsoleCardConnectionObserver()
                    self._reader_picc_connection.addObserver(self._reader_observer)
                    self._reader_sam_connection.addObserver(self._reader_observer)

                # connect to picc only to check the card present or not
                self.card_open_connection()
                self.sam_open_connection()

                self._logger and self._logger.debug("Initializing picc and samcard reader OK")

                self.initialize = True
        except Exception as err:
            pass
            self._logger and self._logger.error(err)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # self.close_all_connection()
        return True

    def close_all_connection(self):
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

    def card_close_connection(self):
        try:
            self._reader_picc_connection.disconnect()
        except Exception as err:
            pass
            self._logger and self._logger.error(err)

    def card_open_connection(self):
        try:
            self._reader_picc_connection.connect(CardConnection.T1_protocol)
            return True
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return False

    def sam_close_connection(self):
        try:
            self._reader_sam_connection.disconnect()
        except Exception as err:
            pass
            self._logger and self._logger.error(err)

    def sam_open_connection(self):
        try:
            self._reader_sam_connection.connect()
            return True
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return False

    def send_apdu(self, apdu_text=None, to_sam=True):
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

    def sam_select(self):
        try:
            _, sw1, sw2 = self.send_apdu(self.SAMCARD_SELECT)
            select_result = sw1 == 0x90 and sw2 == 0
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            select_result = False
        return select_result

    def card_select_aid1(self):
        try:
            data, sw1, sw2 = self.send_apdu(self.PICC_SELECT_AID1, False)
            select_result = sw1 == 0x90 and sw2 == 0 and data[0] == 0
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            select_result = False
        return select_result

    def card_get_number(self):
        try:
            data, sw1, sw2 = self.send_apdu(self.PICC_GET_CARD_NUMBER, False)
            return toHexString(data[4:12], PACK)
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return None

    def card_get_status(self):
        try:
            data, sw1, sw2 = self.send_apdu(self.PICC_GET_CARD_STATUS, False)
            return data[4:6] == [0x61, 0x61]
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return False

    def card_select_aid3(self):
        try:
            data, sw1, sw2 = self.send_apdu(self.PICC_SELECT_AID3, False)
            select_result = sw1 == 0x90 and sw2 == 0 and data[0] == 0
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            select_result = False

        return select_result

    def card_request_key_card(self):
        try:
            data, sw1, sw2 = self.send_apdu(self.PICC_REQUEST_KEY_CARD, False)
            card_key = data[1:] + [sw1, sw2]
            return toHexString(card_key, PACK)
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return None

    def card_get_uid(self):
        try:
            data, sw1, sw2 = self.send_apdu(self.PICC_GET_CARD_UID, False)
            return toHexString(data, PACK)
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return None

    def pdu_get_more_data(self, data_len=0, to_sam=True):
        try:
            return self.send_apdu(self.PDU_GET_MORE_DATA.format(data_len), to_sam)
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            return None

    def sam_authenticate_key(self, card_number_in, card_uid_in, key_card_in):
        try:
            random_key = None
            data, sw1, sw2 = self.send_apdu(
                self.SAMCARD_AUTH_KEY.format(card_number=card_number_in, card_uid=card_uid_in, key_card=key_card_in))
            if sw1 == 0x61:
                data, sw1, sw2 = self.pdu_get_more_data(sw2)
                if sw1 == 0x90 and sw2 == 0x00:
                    random_key = toHexString(data[-16:], PACK)
            else:
                random_key = None
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            random_key = None

        return random_key

    def sam_create_hash(self, card_number_in, card_uid_in, card_random_number_in, debet_value, proc_code=808117,
                        ref_number=36, batch_num=3):
        try:
            pdu_txt = self.SAMCARD_CREATE_HASH.format(card_number_in,
                                                      card_uid_in,
                                                      card_random_number_in,
                                                      toHexString(toASCIIBytes(card_number_in), PACK),
                                                      toHexString(
                                                          toASCIIBytes("{:0<10}".format(int(float(debet_value) * 100))),
                                                          PACK),
                                                      toHexString(
                                                          toASCIIBytes("{:0<12}".format(time.strftime("%d%m%y"))),
                                                          PACK),
                                                      toHexString(
                                                          toASCIIBytes("{:0<12}".format(time.strftime("%H%M%I"))),
                                                          PACK),
                                                      toHexString(toASCIIBytes("{:0>6d}".format(proc_code)), PACK),
                                                      toHexString(toASCIIBytes("{:0>6d}".format(ref_number)), PACK),
                                                      toHexString(toASCIIBytes("{:0>2d}".format(batch_num)), PACK)
                                                      )
            # print(pdu_txt)

            data, sw1, sw2 = self.send_apdu(pdu_txt)
            hash_value = None
            if sw1 == 0x61:
                data, sw1, sw2 = self.pdu_get_more_data(sw2)
                if sw1 == 0x90 and sw2 == 0x00:
                    hash_value = toHexString(data, PACK)
            else:
                hash_value = None

        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            hash_value = None

        return hash_value

    def card_authenticate(self, random_key_in):
        try:
            card_random_number = None
            data, sw1, sw2 = self.send_apdu(self.PICC_CARD_AUTH.format(random_key_in), False)
            if data[0] == 0x00:
                card_random_number = toHexString(data[1:9] + [sw1, sw2], PACK)
            else:
                card_random_number = None
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            card_random_number = None

        return card_random_number

    def card_get_last_transaction_date(self):
        try:
            last_trans_data = None, None
            data, sw1, sw2 = self.send_apdu(self.PICC_GET_LAST_TRANSACTION_DATE, False)
            if data[0] != 0x00:
                last_trans_data = None, None
            else:
                last_trans_data = time.strptime("{:02X}{:02X}{:02X}".format(data[1], data[2], data[3]),
                                                "%y%m%d"), int.from_bytes(data[4:] + [sw1, sw2], 'big')

        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            last_trans_data = None, None

        return last_trans_data

    def card_get_balance(self):
        try:
            data, sw1, sw2 = self.send_apdu(self.PICC_GET_BALANCE, False)
            balance = -2
            if data[0] == 0x00:
                balance = int.from_bytes(data[1:] + [sw1, sw2], 'little')
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            balance = -1

        return balance

    def card_debet_balance(self, debet_value=0):
        try:
            data, sw1, sw2 = self.send_apdu(
                self.PICC_DEBET_BALANCE.format(binascii.hexlify((debet_value).to_bytes(3, 'little')).decode()), False)
            debet_status = data[0] == 0x00 and sw1 == 0x90 and sw2 == 0x00
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            debet_status = False

        return debet_status

    def card_commit_transaction(self):
        try:
            data, sw1, sw2 = self.send_apdu(self.PICC_COMMIT_TRANSACTION, False)
            commit_result = data[0] == 0x00 and sw1 == 0x90 and sw2 == 0x00
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            commit_result = False

        return commit_result

    def cardAbortTransaction(self):
        try:
            data, sw1, sw2 = self.send_apdu(self.PICC_ABORT_TRANSACTION, False)
            abort_result = data[0] == 0x00 and sw1 == 0x90 and sw2 == 0x00
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            abort_result = False

        return abort_result

    def card_write_log(self, debet_value=0, balance_before=0, balance_after=0, mid=None, tid=None):
        try:
            pdu = self.PICC_WRITE_LOG.format(
                mid and mid or self._mid,
                tid and tid or self._tid,
                time.strftime("%y%m%d"),
                time.strftime("%H%M%I"),
                binascii.hexlify(debet_value.to_bytes(3, 'little')).decode(),
                binascii.hexlify(balance_before.to_bytes(3, 'little')).decode(),
                binascii.hexlify(balance_after.to_bytes(3, 'little')).decode()
            )
            # print(pdu)
            data, sw1, sw2 = self.send_apdu(pdu, False)
            result = data[0] == 0x00 and sw1 == 0x90 and sw2 == 0x00
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            result = False

        return result

    def card_write_last_transaction(self, last_trans_date, last_akum_debet, debet_value=0):
        try:
            akum_debet_total = debet_value
            if last_trans_date.tm_mon == int(time.strftime("%m")):
                akum_debet_total += last_akum_debet
            data, sw1, sw2 = self.send_apdu(self.PICC_WRITE_LAST_TRANSACTION.format(
                time.strftime("%y%m%d"),
                binascii.hexlify((akum_debet_total).to_bytes(4, 'big')).decode()
            ), False)
            result = data[0] == 0x00 and sw1 == 0x90 and sw2 == 0x00
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            result = False

        return result

    def transaction_debet_card(self, debet_amount=0, mid=None, tid=None, proc_code=808117, ref_number=1,
                               batch_number=1):
        global transaction_result
        try:
            transaction_result = {
                'status': False,
                'card_number': "",
                'transaction_date': "0000-00-00",
                'transaction_time': "00:00:00",
                'balance': 0,
                'amount': 0,
                'ref_number': 0,
                'batch_number': 0,
                'mid': '',
                'tid': '',
                'hash': '00000000'
            }

            # step 1
            transaction_result.update(
                {
                    'transaction_date': time.strftime("%Y-%m-%d"),
                    'transaction_time': time.strftime("%H:%M:%I"),
                    'amount': debet_amount,
                    'mid': mid and mid or self._mid,
                    'tid': tid and tid or self._tid,
                    'ref_number': ref_number,
                    'batch_number': batch_number
                }
            )

            # open connection
            if self.card_open_connection():
                if self.sam_select():
                    # step 2
                    if self.card_select_aid1():
                        # step 3
                        card_number = self.card_get_number()
                        transaction_result['card_number'] = card_number
                        if card_number is not None:
                            # step 4
                            if self.card_get_status():
                                # step 5
                                if self.card_select_aid3():
                                    # step 6
                                    card_key = self.card_request_key_card()
                                    if card_key is not None:
                                        # step 7
                                        card_uid = self.card_get_uid()
                                        if card_uid is not None:

                                            # step 8
                                            sam_random_key = self.sam_authenticate_key(card_number, card_uid, card_key)
                                            if sam_random_key is not None:
                                                # step 9
                                                card_random_number = self.card_authenticate(sam_random_key)
                                                if card_random_number is not None:
                                                    # step 10
                                                    last_trans_date, last_trans_akum_debet = self.card_get_last_transaction_date()
                                                    if last_trans_date is not None and last_trans_akum_debet is not None:
                                                        # step 11
                                                        card_balance = self.card_get_balance()
                                                        transaction_result['balance'] = card_balance
                                                        if card_balance >= 0:
                                                            # step 12
                                                            if self.card_debet_balance(debet_amount):
                                                                # step 13
                                                                sam_hash = self.sam_create_hash(card_number, card_uid,
                                                                                                card_random_number,
                                                                                                debet_amount, proc_code,
                                                                                                ref_number,
                                                                                                batch_number)
                                                                transaction_result['hash'] = sam_hash
                                                                if sam_hash is not None:
                                                                    # step 14
                                                                    if self.card_write_log(debet_amount, card_balance,
                                                                                           card_balance - debet_amount,
                                                                                           transaction_result['mid'],
                                                                                           transaction_result['tid']):
                                                                        # step 15
                                                                        if self.card_write_last_transaction(
                                                                                last_trans_date, last_trans_akum_debet,
                                                                                debet_amount):
                                                                            # step 16
                                                                            if self.card_commit_transaction():
                                                                                transaction_result['status'] = True
                                                                            else:
                                                                                self.cardAbortTransaction()
                                                                        else:
                                                                            self.cardAbortTransaction()
                                                                    else:
                                                                        self.cardAbortTransaction()
                                                                else:
                                                                    self.cardAbortTransaction()
                                                            else:
                                                                self.cardAbortTransaction()
            # self.card_close_connection()
        except Exception as err:
            pass
            self._logger and self._logger.error(err)
            transaction_result['status'] = False
            # self.card_close_connection()

        return transaction_result


class BrizziCardObserver(CardObserver):
    """Card observer for brizzi
    """

    # sam card
    sam_connection = None
    sam_uid = "3B6800000073C84013009000"

    def update(self, observable, actions):
        """
        When card is insert or removed, it goes here
        :param observable:
        :param actions:
        """
        (addedcards, removedcards) = actions
        '''
        for card in addedcards:
            print(card.createConnection().getReader())
            print("+Inserted: ", toHexString(card.atr))
        for card in removedcards:
            print("-Removed: ", toHexString(card.atr))
        '''

        # get sam connection
        for card in addedcards:
            atrx = toHexString(card.atr, PACK)
            LOGGER_MAIN.debug(atrx)
            if atrx == self.sam_uid:
                if self.sam_connection is None:
                    self.sam_connection = card.createConnection()
            else:
                picc_connection = card.createConnection()
                # picc_connection.connect()
                # data, sw1, sw2 = picc_connection.transmit(toBytes("FF00480000"))
                # data, sw1, sw2 = picc_connection.transmit(toBytes("E0000028010F"))
                # firmware = toBytes("E000002900")
                # retx = picc_connection.control(SCARD_CTL_CODE(3500), firmware)
                # LOGGER_MAIN.debug(retx)
                with BrizziProcessor(sam_connection=self.sam_connection, picc_connection=picc_connection,
                                     debug_mode=False) as conn_obj:
                    if conn_obj.initialize:
                        resultx = conn_obj.transaction_debet_card(1)
                        LOGGER_MAIN.debug(resultx)
                        if resultx['status']:
                            GPIO_CONTROL_MAIN.buzzer_beep(1)
                            GPIO_CONTROL_MAIN.gate_open()
                        else:
                            GPIO_CONTROL_MAIN.buzzer_beep(3)
                            GPIO_CONTROL_MAIN.gate_close()


def main():
    try:
        # initial screen
        LOGGER_MAIN.info("System ready....")

        global GPIO_CONTROL_MAIN
        GPIO_CONTROL_MAIN = GPIOControl()

        # card monitor
        cardmonitor = CardMonitor()
        cardobserver = BrizziCardObserver()
        cardmonitor.addObserver(cardobserver)

        # eternal loop
        try:
            while True:
                time.sleep(1)
        except Exception as err:
            pass

        # delete observer
        cardmonitor.deleteObserver(cardobserver)

        import sys

        if 'win32' == sys.platform:
            print('press Enter to continue')
            sys.stdin.read(1)
    except Exception as err:
        pass

    GPIO_CONTROL_MAIN.gpio_cleanup()


if __name__ == '__main__':
    main()
