import usb.core
import usb.backend.libusb1
from tkinter import messagebox

VENDOR_ID = 0x0a07 # OnTrak Control Systems Inc. vendor ID

RELAY_PARAMETER = {
    'SET_RELAY_K0': 'SK0',  # Close relay K0
    'SET_RELAY_K1': 'SK1',  # Close relay K1
    'SET_RELAY_K2': 'SK2',  # Close relay K2
    'SET_RELAY_K3': 'SK3',  # Close relay K3
    'SET_RELAY_K4': 'SK4',  # Close relay K4
    'SET_RELAY_K5': 'SK5',  # Close relay K5
    'SET_RELAY_K6': 'SK6',  # Close relay K6
    'SET_RELAY_K7': 'SK7',  # Close relay K7
    'RESET_RELAY_K0': 'RK0',  # Open relay K0
    'RESET_RELAY_K1': 'RK1',  # Open relay K1
    'RESET_RELAY_K2': 'RK2',  # Open relay K2
    'RESET_RELAY_K3': 'RK3',  # Open relay K3
    'RESET_RELAY_K4': 'RK4',  # Open relay K4
    'RESET_RELAY_K5': 'RK5',  # Open relay K5
    'RESET_RELAY_K6': 'RK6',  # Open relay K6
    'RESET_RELAY_K7': 'RK7',  # Open relay K7
    'SET_RELAY_PREFIX': 'MK',  # Prefix for controlling relay Ks with decimal number 000 (0x0000) - 255 (0x1111)
    'RESET_RELAY': 'MK000',  # Open all relay Ks
    'READ_RELAY_K_DECIMAL': 'PK',  # Read relay Ks status in decimal number 000 (0x0000) - 255 (0x1111)
    'READ_RELAY_K0': 'RPK0',  # Read relay K0 status: 0 - open, 1 - close
    'READ_RELAY_K1': 'RPK1',  # Read relay K1 status: 0 - open, 1 - close
    'READ_RELAY_K2': 'RPK2',  # Read relay K2 status: 0 - open, 1 - close
    'READ_RELAY_K3': 'RPK3',  # Read relay K3 status: 0 - open, 1 - close
    'READ_RELAY_K4': 'RPK4',  # Read relay K4 status: 0 - open, 1 - close
    'READ_RELAY_K5': 'RPK5',  # Read relay K5 status: 0 - open, 1 - close
    'READ_RELAY_K6': 'RPK6',  # Read relay K6 status: 0 - open, 1 - close
    'READ_RELAY_K7': 'RPK7',  # Read relay K7 status: 0 - open, 1 - close
    'READ_PA_BINARY': 'RPA',  # Read relay PA input port in binary form
    'READ_PB_BINARY': 'RPB',  # Read relay PB input port in binary form
    'READ_PA_DECIMAL': 'PA',  # Read relay PA input port in decimal form 00 (0x00) - 15 (0x11)
    'READ_PB_DECIMAL': 'PB',  # Read relay PB input port in decimal form 00 (0x00) - 15 (0x11)
    'READ_PAB_DECIMAL': 'PI',  # Read PAB combined status in decimal form 0 - 255: 0000 0000
                               #                                                    PB   PA
    'READ_PA0': 'RPA0',  # Read relay PA0 status: 0 - low, 1 - high
    'READ_PB0': 'RPB0',  # Read relay PB0 status: 0 - low, 1 - high
    'READ_PA1': 'RPA1',  # Read relay PA1 status: 0 - low, 1 - high
    'READ_PB1': 'RPB1',  # Read relay PB1 status: 0 - low, 1 - high
    'READ_PA2': 'RPA2',  # Read relay PA2 status: 0 - low, 1 - high
    'READ_PB2': 'RPB2',  # Read relay PB2 status: 0 - low, 1 - high
    'READ_PA3': 'RPA3',  # Read relay PA3 status: 0 - low, 1 - high
    'READ_PB3': 'RPB3',  # Read relay PB3 status: 0 - low, 1 - high

    # Event counter records low to high transitions cycling from 0 to 65535
    'READ_COUNTER_PA0': 'RE0',  # Read relay PA0 event counter
    'READ_COUNTER_PA1': 'RE1',  # Read relay PA1 event counter
    'READ_COUNTER_PA2': 'RE2',  # Read relay PA2 event counter
    'READ_COUNTER_PA3': 'RE3',  # Read relay PA3 event counter
    'READ_COUNTER_PB0': 'RE4',  # Read relay PB0 event counter
    'READ_COUNTER_PB1': 'RE5',  # Read relay PB1 event counter
    'READ_COUNTER_PB2': 'RE6',  # Read relay PB2 event counter
    'READ_COUNTER_PB3': 'RE7',  # Read relay PB3 event counter
    'READ_CLEAR_COUNTER_PA0': 'RC0',  # Read and Clear relay PA0 event counter
    'READ_CLEAR_COUNTER_PA1': 'RC1',  # Read and Clear relay PA1 event counter
    'READ_CLEAR_COUNTER_PA2': 'RC2',  # Read and Clear relay PA2 event counter
    'READ_CLEAR_COUNTER_PA3': 'RC3',  # Read and Clear relay PA3 event counter
    'READ_CLEAR_COUNTER_PB0': 'RC4',  # Read and Clear relay PB0 event counter
    'READ_CLEAR_COUNTER_PB1': 'RC5',  # Read and Clear relay PB1 event counter
    'READ_CLEAR_COUNTER_PB2': 'RC6',  # Read and Clear relay PB2 event counter
    'READ_CLEAR_COUNTER_PB3': 'RC7',  # Read and Clear relay PB3 event counter
    'SET_DEBOUNCE_SLOW': 'DB0',  # Set event counter debounce time to 10ms
    'SET_DEBOUNCE_DEFAULT': 'DB1',  # Set event counter debounce time to 1ms
    'SET_DEBOUNCE_FAST': 'DB2',  # Set event counter debounce time to 100us
    'READ_DEBOUNCE_TIME': 'DB',  # Read current debounce setting

    # Watchdog
    'WATCHDOG_OFF': 'WD0',  # Turn off watchdog
    'WATCHDOG_1S': 'WD1',  # Set watchdog interval to 1s
    'WATCHDOG_10S': 'WD2',  # Set watchdog interval to 10s
    'WATCHDOG_1M': 'WD3',  # Set watchdog interval to 1min
    'READ_WATCHDOG_SETTING': 'WD'  # Read watchdog interval
}

TIMEOUT = 200  # ms; default timeout

class RelayError(Exception):
    pass


class OntrakRelay:

    def __init__(self, adu_id=208):

        self.device = usb.core.find(idVendor=VENDOR_ID, idProduct=adu_id)

        if self.device is None:
            raise ValueError('ADU Device not found. Please ensure it is connected properly.')

        # Claim interface 0 - this interface provides IN and OUT endpoints to write to and read from
        usb.util.claim_interface(self.device, 0)

    def _write_to_adu(self, msg_str):
        # print('Writing command: {}'.format(msg_str))

        # message structure:
        #   message is an ASCII string containing the command
        #   8 bytes in length
        #   0th byte must always be 0x01 (decimal 1)
        #   bytes 1 to 7 are ASCII character values representing the command
        #   remainder of message is padded to 8 bytes with character code 0

        byte_str = chr(0x01) + msg_str + chr(0) * max(7 - len(msg_str), 0)

        num_bytes_written = 0

        try:
            # 0x01 is the OUT endpoint
            num_bytes_written = self.device.write(0x01, byte_str)
        except usb.core.USBError:
            # messagebox.showinfo("Error!", f"{e.args}")
            raise RelayError

        return num_bytes_written

    def _read_from_adu(self, timeout):
        try:
            # try to read a maximum of 64 bytes from 0x81 (IN endpoint)
            data = self.device.read(0x81, 64, timeout)
        except usb.core.USBError:
            # messagebox.showinfo("Error!", f"Error reading response: {e.args}")
            raise RelayError

        byte_str = ''.join(chr(n) for n in data[1:]) # construct a string out of the read values, starting from the 2nd byte
        result_str = byte_str.split('\x00',1)[0] # remove the trailing null '\x00' characters

        if len(result_str) == 0:
            return None

        return result_str

    def __del__(self):
        try:
            usb.util.release_interface(self.device, 0)
        # self.device.close()
        except AttributeError:
            pass

    def check_status(self, port, true_value):
        """
        Checks port or relay status against target true value.
        Returns True if status match. False if not.
        Use string for true_value (i.e. '1', '018' for decimal or '1010' for binary)

        port: 'K0-K7' - Relay K0-K7 status | true_value: '1' for close, '0' for open
              'K_DEC' - Relay status in decimal form | true_value: '000' for all open, '255' for all close
              'PA0-PA3' - Input PA0-PA3 status | true_value: '1' for high, '0' for low
              'PA_BIN' - Input PA status in binary form | true_value: '0000' for all low, '1111' for all high
              'PA_DEC' - Input PA status in decimal form | true_value: '00' for all low, '15' for all high
              'PB0-PB3' - Input PB0-PB3 status | true_value: '1' for high, '0' for low
              'PB_BIN' - Input PB status in binary form | true_value: '0000' for all low, '1111' for all high
              'PB_DEC' - Input PB status in decimal form | true_value: '00' for all low, '15' for all high
              'PAB' - Input PA & PB altogether in decimal form | true_value: '000' for all low, '255' for all high
        true_value: str
        """
        if 'K' in port:
            if 'DEC' in port:
                self._write_to_adu(RELAY_PARAMETER[f'READ_RELAY_K_DECIMAL'])

            else:
                port_num = port[1]
                self._write_to_adu(RELAY_PARAMETER[f'READ_RELAY_K{port_num}'])

        elif 'PA' in port:
            if 'BIN' in port:
                self._write_to_adu(RELAY_PARAMETER[f'READ_PA_BINARY'])

            elif 'DEC' in port:
                self._write_to_adu(RELAY_PARAMETER[f'READ_PA_DECIMAL'])

            else:
                port_num = port[2]
                self._write_to_adu(RELAY_PARAMETER[f'READ_PA{port_num}'])

        elif 'PB' in port:
            if 'BIN' in port:
                self._write_to_adu(RELAY_PARAMETER[f'READ_PB_BINARY'])

            elif 'DEC' in port:
                self._write_to_adu(RELAY_PARAMETER[f'READ_PB_DECIMAL'])

            else:
                port_num = port[2]
                self._write_to_adu(RELAY_PARAMETER[f'READ_PB{port_num}'])
        elif 'PAB' in port:
            self._write_to_adu(RELAY_PARAMETER['READ_PAB_DECIMAL'])

        ans = self._read_from_adu(TIMEOUT)
        return ans == true_value

    def check_debounce_time(self, true_value):
        self._write_to_adu(RELAY_PARAMETER['READ_DEBOUNCE_TIME'])
        ans = self._read_from_adu(TIMEOUT)
        return ans == true_value

    def check_watchdog_interval(self, true_value):
        self._write_to_adu(RELAY_PARAMETER['READ_WATCHDOG_SETTING'])
        ans = self._read_from_adu(TIMEOUT)
        return ans == true_value


    def open_relay(self, port=0, check=False):
        self._write_to_adu(RELAY_PARAMETER[f'RESET_RELAY_K{port}'])

        if check:
            return self.check_status(f'K{port}', '1')

    def close_relay(self, port=0, check=False):
        self._write_to_adu(RELAY_PARAMETER[f'SET_RELAY_K{port}'])

        if check:
            return self.check_status(f'K{port}', '0')

    def set_relay(self, num: int, check=False):
        self._write_to_adu(f"{RELAY_PARAMETER['SET_RELAY_PREFIX']}{num}")

        if check:
            return self.check_status('K_DEC', f'{num:03d}')

    def reset_relay(self, check=False):
        self._write_to_adu(RELAY_PARAMETER['RESET_RELAY'])

        if check:
            return self.check_status('K_DEC', '000')

    def set_debounce(self, mode='1', check=False):
        """
        Sets debounce time for input port event counter, which counts low to high transitions

        mode: '0' or 'slow' - 10ms
              '1' or 'default' - 1ms
              '2' or 'fast' - 100us
        check: True - Read status after sending debounce command to confirm change.
                      Returns True or False from status check
               False - Skip status check, assuming command functional. Returns nothing
        """
        if mode == '0' or mode.lower() == 'slow':
            self._write_to_adu(RELAY_PARAMETER['SET_DEBOUNCE_SLOW'])
            if check:
                return self.check_debounce_time('0')

        elif mode == '1' or mode.lower() == 'default' or mode == '':
            self._write_to_adu(RELAY_PARAMETER['SET_DEBOUNCE_DEFAULT'])
            if check:
                return self.check_debounce_time('1')

        elif mode == '2' or mode.lower() == 'fast':
            self._write_to_adu(RELAY_PARAMETER['SET_DEBOUNCE_FAST'])
            if check:
                return self.check_debounce_time('2')

    def set_watchdog(self, mode='0', check=False):
        """
        Sets debounce time for input port event counter, which counts low to high transitions

        mode: '0' or 'off' - Turns watchdog off
              '1' or '1s' - Watchdog interval is 1 second
              '2' or '10s' - Watchdog interval is 10 second
              '3' or '1m' - Watchdog interval is 1 minute
        check: True - Read status after sending watchdog command to confirm change.
                      Returns True or False from status check
               False - Skip status check, assuming command functional. Returns nothing
        """
        if mode == '0' or mode.lower() == 'off':
            self._write_to_adu(RELAY_PARAMETER['WATCHDOG_OFF'])
            if check:
                return self.check_watchdog_interval('0')

        elif mode == '1' or mode.lower() == '1s':
            self._write_to_adu(RELAY_PARAMETER['WATCHDOG_1S'])
            if check:
                return self.check_watchdog_interval('1')

        elif mode == '2' or mode.lower() == '10s':
            self._write_to_adu(RELAY_PARAMETER['WATCHDOG_10S'])
            if check:
                return self.check_watchdog_interval('2')

        elif mode == '3' or mode.lower() == '1m':
            self._write_to_adu(RELAY_PARAMETER['WATCHDOG_1M'])
            if check:
                return self.check_watchdog_interval('3')

