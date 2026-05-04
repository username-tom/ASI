from configparser import ConfigParser


# loading parameters from config.ini
config = ConfigParser()
config.read('config.ini')
DUT_COM_PORT = config.get('default', 'dut_com_port')
BRK_COM_PORT = config.get('default', 'brk_com_port')
SAVE_DESTINATION = config.get('default', 'save_destination')
BACKUP_DESTINATION = "C:\\Timber Production Result"
# Max. Line reactor test duration in minutes if, for some reason, controller never hit foldback and nobody is there to stop the test
TEST_DURATION = float(config.get('default', 'timeout'))  # minutes
GEOMETRY = config.get('default', 'geometry')
FONT_SIZE = int(config.get('default', 'font_size'))
MD1 = int(config.get('default', 'md1'))
MD2 = int(config.get('default', 'md2'))

PRE_RS = int(config.get('pre', 'rs').split(',')[0])
PRE_LS = int(config.get('pre', 'ls').split(',')[0])
PRE_RPM = int(config.get('pre', 'rpm'))
PRE_OFFSET = int(config.get('pre', 'offset'))
POST_RS = int(config.get('post', 'rs').split(',')[0])
POST_LS = int(config.get('post', 'ls').split(',')[0])
POST_RPM = int(config.get('post', 'rpm'))
POST_OFFSET = int(config.get('post', 'offset'))

UNLOADED_SPEED = int(config.get('unloaded', 'speed'))
UNLOADED_DURATION = int(config.get('unloaded', 'duration'))
UNLOADED_IA = [int(config.get('unloaded', 'ia').split(',')[0]),
               int(config.get('unloaded', 'ia').split(',')[1])]
UNLOADED_IC = [int(config.get('unloaded', 'ic').split(',')[0]),
               int(config.get('unloaded', 'ic').split(',')[1])]
UNLOADED_MOTOR_CURRENT = [int(config.get('unloaded', 'motor_current').split(',')[0]),
                          int(config.get('unloaded', 'motor_current').split(',')[1])]

LOADED_SPEED = int(config.get('loaded', 'speed'))
LOADED_MIN = int(config.get('loaded', 'min_torque'))
LOADED_MAX = int(config.get('loaded', 'max_torque'))
LOADED_STEP = float(config.get('loaded', 'torque_step'))
LOADED_DURATION = float(config.get('loaded', 'settle_time'))
LOADED_TARGET = int(config.get('loaded', 'target_torque'))
LOADED_TEMP = int(config.get('loaded', 'target_temperature'))

WATCHDOG_INTERVAL = 0.5  # sec
HELP_TEXT = f"Test Procedure (after pressing Start):\n" \
            f"1) Connects DUT & BRK\n" \
            f"2) Pre-test Motor Discovery Mode 1 & 2\n" \
            f"3) Unloaded Run\n" \
            f"4) Rundown\n" \
            f"5) Post-test Motor Discovery Mode 1 & 2\n" \
            f"6) Disconnect\n"

log_header = ["Result Time",
              "Serial Number",
              "Barcode",
              "Test Result",
              "Initial Motor Temperature",
              "Pre-test Faults",
              "Pre-test Rs",
              "Pre-test Ls",
              "Pre-test Hall Sectors",
              "Pre-test Rated RPM",
              "Pre-test Hall Offset",
              "Unloaded Ia RMS Avg",
              "Unloaded Ia RMS Max",
              "Unloaded Ia RMS Min",
              "Unloaded Ic RMS Avg",
              "Unloaded Ic RMS Max",
              "Unloaded Ic RMS Min",
              "Unloaded Motor Current",
              "Unloaded Result",
              "Rundown Max Torque",
              "Rundown Max Temperature",
              "Rundown Result",
              "Post-test Faults",
              "Post-test Rs",
              "Post-test Ls",
              "Post-test Hall Sectors",
              "Post-test Rated RPM",
              "Post-test Hall Offset",
              "Note"]

def index(item):
    return log_header.index(item)

OUTPUT_RESULTS = {"Connection": None,
                  "Pre-test Rs": None,
                  "Pre-test Ls": None,
                  "Pre-test Hall Sectors": None,
                  "Pre-test Motor Discovery": None,
                  "Unloaded Run": None,
                  "Max Torque": None,
                  "Rundown": None,
                  "Post-test Rs": None,
                  "Post-test Ls": None,
                  "Post-test Hall Sectors": None,
                  "Post-test Motor Discovery": None,
                  "Test Result": "Not Started"}

def check_index(item):
    return list(OUTPUT_RESULTS.keys()).index(item)
