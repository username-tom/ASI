import os

import screeninfo.common

ROOT_DIR = os.getcwd()
from configparser import ConfigParser
from screeninfo import get_monitors
# from dyno_v2.Module.dyno_parameters import DYNO_SET


AUTHOR_EMAIL = 'twu@acceleratedsystems.com'
ASI_GREEN = '#5DA01D'
X_MAX = 70
X_MIN = 0
COLORS = ['blue', 'red', 'green', 'magenta', 'cyan', 'yellow', 'gray60', 'sienna',
          "orange", "gold", "lime", "teal", "sky blue", "navy", "purple", "pink"]
PARAMETER_FOREGROUND = {
    'blue': 'white',
    'red': 'white',
    'green': 'white',
    'magenta': 'white',
    'cyan': 'black', 'yellow': 'black',
    'gray60': 'black',
    'sienna': 'white',
    "orange": 'black',
    "gold": 'black',
    "lime": 'black',
    "teal": 'black',
    "sky blue": 'black',
    "navy": 'white',
    "purple": 'white',
    "pink": 'black'
}
HELP_TEXT = "<ESC> or STOP - E-STOP: Interrupts running script & Stops both driver and brake\n\n" \
            "Update YOKOGAWA IP Address:\n" \
            "  - Go to Connector tab\n" \
            "  - Update the YOKOGAWA IP Address and connect\n" \
            "  - YOKOGAWA IP Address will be updated and saved to file after establishing connection\n\n" \
            "To toggle between ABB auto and manual:\n" \
            "  - If ABB isn't connected: \n" \
            "    - Check \"ABB\" box\n" \
            "    - Check or uncheck Remote Mode for your desired mode\n" \
            "    - Connect\n" \
            "  - If ABB is connected:\n" \
            "    - Click Toggle button to change mode\n" \
            "  - Press \"LOC/REM\" button on ABB Keypad to match corresponding mode (ignore warnings on keypad)"
REMINDER_TEXT = "<ESC> or STOP - E-STOP: Interrupts running script & Stops both driver and brake"
CONTROL_PARAM_INIT = 0
CONTROL_PARAM_UPDATE = 1
CONTROL_PARAM_UPLOAD = 2
CONFIG_LIST_COL = 1
CONFIG_LIST_FONT_SIZE = 12
CONFIG_LIST_LABEL_WIDTH = 100
CONFIG_LIST_WIDTH = 500
COM_BAUD_RATE = [115200, 19200, 1200, 9600, 38400, 57600, 230400]
CAN_BAUD_RATE = [250000, 500000, 125000, 50000, 20000, 10000, 800000, 1000000]
CAN_INTERFACE_OPTIONS = ['BAC', 'Throttle', 'GCM', 'VCM', 'BAC_J1939', 'Throttle_J1939', 'VCM_J1939']
CAN_INTERFACE_DEFAULT_DICTIONARY = {
    'BAC': f'{ROOT_DIR}\dyno_v2\Dictionary\\6024_ASIObjectDictionary.xml',
    'Throttle': f'{ROOT_DIR}\dyno_v2\Dictionary\Throttle_ASIObjectDictionary.xml',
    'GCM': f'{ROOT_DIR}\dyno_v2\Dictionary\GCM_ASIObjectDictionary.xml',
    'VCM': f'{ROOT_DIR}\dyno_v2\Dictionary\VCM_ASIObjectDictionary.xml',
    'BAC_J1939': f'{ROOT_DIR}\dyno_v2\Dictionary\8004_ASIObjectDictionary.xml',
    'Throttle_J1939': f'{ROOT_DIR}\dyno_v2\Dictionary\J1939_Throttle_ASIObjectDictionary.xml',
    'VCM_J1939': f'{ROOT_DIR}\dyno_v2\Dictionary\J1939_VCM_ASIObjectDictionary.xml'
}
TOOLTIP_DELAY = 0.25

OPTION_FONT_NAME = 'TkDefaultFont'
ERROR_FONT_NAME = 'TkFixedFont'
DEFAULT_WIDTH = 1550
DEFAULT_HEIGHT = 800
HD_SIZE = '1920x1017'
LAPTOP_SIZE = '1600x817'

STATUS_MINSIZE_LIMIT = 65
STATUS_MINSIZE_DUT = 390
STATUS_MINSIZE_BRK = 400
STATUS_MINSIZE_ABB = 55
STATUS_MINSIZE_YOKO = 300
STATUS_MINSIZE_TEST = 140
MOTOR_CD = 20
CONTROLLER_CD = 15
DEFAULT_GREY = '#d9d9d9'
MOTOR_DISCOVERY_LABEL_WIDTH = 25
MOTOR_DISCOVERY_VALUE_WIDTH = 5
MAIN_SPIN_MODE = ['Speed',
                  'Torque',
                  'Torque with speed limit',
                  'Open loop current',
                  'Open loop voltage']
MAIN_SPIN_PLACE = {
    'dut_main_speed_rpm_label': [0.02, 0.33],
    'dut_main_speed_rpm': [0.15, 0.33],
    'dut_main_speed_command_label': [0.35, 0.33],
    'dut_main_speed_command': [0.65, 0.33],
    'dut_main_motoring_label': [0.02, 0.66],
    'dut_main_motoring': [0.2, 0.66],
    'dut_main_braking_label': [0.45, 0.66],
    'dut_main_braking': [0.65, 0.66],
    'dut_main_torque_label': [0.02, 0.33],
    'dut_main_torque': [0.2, 0.33],
    'dut_main_current_label': [0.02, 0.33],
    'dut_main_current': [0.2, 0.33],
    'dut_main_modulation_label': [0.02, 0.33],
    'dut_main_modulation': [0.25, 0.33],
    'dut_main_frequency_label': [0.45, 0.33],
    'dut_main_frequency': [0.65, 0.33],
    'dut_main_angle_label': [0.02, 0.66],
    'dut_main_angle': [0.2, 0.66]
}
MAIN_SPIN_PARAMETERS = {
    'dut_main_speed_rpm': 'Remote Speed Command in RPM',
    'dut_main_speed_command': 'Remote speed command',
    'dut_main_motoring': 'Remote maximum motoring current',
    'dut_main_braking': 'Remote maximum braking current',
    'dut_main_torque': 'Remote torque command',
    'dut_main_current': 'Open loop current',
    'dut_main_modulation': 'Open loop modulation',
    'dut_main_frequency': 'Open loop frequency',
    'dut_main_angle': 'Open loop angle'
}
PLOT_LIST = {
    'RPMTorque': 'single',
    'temp': 'grid',
    'mech': 'single',
    'elec': 'grid',
    'effi': 'grid',
    'mb': 'grid',
}

# loading parameters from config.ini
config = ConfigParser()
config.read('gui.ini')
DYNO_SET = config.get('dyno_module', 'dyno_set')
# Parameters
try:
    LAST_GEOMETRY = config.get('GUI', 'geometry')
except IndexError:
    LAST_GEOMETRY = f'{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}+1+1'
try:
    OUT_GEOMETRY = config.get('GUI', 'out_geometry')
except IndexError:
    OUT_GEOMETRY = '700x300+10+10'

LAST_WIDTH = int(LAST_GEOMETRY.split('x')[0])
LAST_HEIGHT = int(LAST_GEOMETRY.split('+')[0].split('x')[1])

try:
    monitors = get_monitors()
except screeninfo.common.ScreenInfoError:
    monitors = [screeninfo.Monitor(x=0, y=0, width=1600, height=900, width_mm=382, height_mm=214,
                                   name='\\\\.\\DISPLAY1', is_primary=True)]
if len(monitors) == 1 and monitors[0].width <= 1920 and monitors[0].height <= 1080:
    # laptop monitor only
    MIN_WIDTH = 1600
    MIN_HEIGHT = 700
    OPTION_FONT_SIZE = 10
    YOKO_FONT_SIZE = 8
    LIST_FONT_SIZE = 10
elif len(monitors) > 1:
    for monitor in monitors:
        if monitor.width >= 1920 and monitor.height >= 1080:
            # HD monitor
            MIN_WIDTH = 1920
            MIN_HEIGHT = 900
            if DYNO_SET != 'DYNO':
                OPTION_FONT_SIZE = 12
                YOKO_FONT_SIZE = 10
                LIST_FONT_SIZE = 12
            else:
                OPTION_FONT_SIZE = 10
                YOKO_FONT_SIZE = 8
                LIST_FONT_SIZE = 10
            break
        MIN_WIDTH = 1600
        MIN_HEIGHT = 700
        OPTION_FONT_SIZE = 10
        YOKO_FONT_SIZE = 8
        LIST_FONT_SIZE = 10

new_monitor = False
if LAST_WIDTH != MIN_WIDTH:
    LAST_WIDTH = MIN_WIDTH
    LAST_HEIGHT = MIN_HEIGHT
    new_monitor = True
if new_monitor:
    if len(monitors) == 1:
        LAST_GEOMETRY = f'{LAST_WIDTH}x{LAST_HEIGHT}+1+1'
    elif len(monitors) > 1:
        bigger_monitor = 0
        for i, monitor in enumerate(monitors):
            if monitor.width > monitors[bigger_monitor].width and \
                    monitor.height > monitors[bigger_monitor].height:
                bigger_monitor = i
        LAST_GEOMETRY = f'{LAST_WIDTH}x{LAST_HEIGHT}+{monitors[bigger_monitor].x + 1}+{monitors[bigger_monitor].y + 1}'
    OUT_GEOMETRY = '700x500+10+10'
print(LAST_GEOMETRY)