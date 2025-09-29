import configparser
import os
ROOT_DIR = os.getcwd()
from configparser import ConfigParser
import pandas as pd

def config_reader():
    """config_reader: static method for reading dyno_config.csv"""
    file = f"{ROOT_DIR}/dyno_config.csv"
    data = pd.read_csv(file, index_col="Name")
    for i, name in enumerate(CONFIG_MAP):
        for column in data.columns[i:]:
            # print(name, column)
            if name == column:
                break
            if column.lower() == name:
                data = data.rename(columns={column:name})
                break
            try:
                data.insert(i, name, pd.Series([0] * len(data.index)))
            except ValueError:
                pass

    return data

def template_reader():
    """config_reader: static method for reading dyno_config.csv"""
    file = f"{ROOT_DIR}/dyno_config_template.csv"
    data = pd.read_csv(file, index_col="Name")
    for i, name in enumerate(CONFIG_MAP):
        for column in data.columns[i:]:
            # print(name, column)
            if name == column:
                break
            try:
                data.insert(i, name, pd.Series([0] * len(data.index)))
            except ValueError:
                pass

    return data


STYLES = ["b", "r", "g", "m", "c", "y", "gray", "sienna", "orange", "gold", "lime", "teal",
          "skyblue", "navy", "purple", "pink"]
DUT_MOTOR_SELECTION = ['Oak',
                       'Cedar',
                       'Spindle',
                       'Timber',
                       'Bike',
                       'Other',
                       'NaN']
BRK_MOTOR_SELECTION = ['ABB',
                       'HiSpeed',
                       'Oak',
                       'Cedar',
                       'Spindle',
                       'Timber',
                       'Bike',
                       'Other',
                       'NaN']
DUT_CONTROLLER_SELECTION = ['BAC2000',
                            'BAC4000',
                            'BAC3000',
                            'BAC8000',
                            'BAC355',
                            'BAC555',
                            'BAC855',
                            '2B',
                            'Cedar',
                            'Other',
                            'NaN']
BRK_CONTROLLER_SELECTION = ['ABB',
                            'BAC2000',
                            'BAC4000',
                            'BAC3000',
                            'BAC8000',
                            'BAC355',
                            'BAC555',
                            'BAC855',
                            '2B',
                            'Cedar',
                            'Other',
                            'NaN']
ASI_CONTROLLERS = ['BAC2000',
                   'BAC4000',
                   'BAC3000',
                   'BAC8000',
                   'BAC355',
                   'BAC555',
                   'BAC855',
                   '2B',
                   'Cedar']
MOTOR_MAIN_PARAMETERS = [['Rs', 'm\u03A9'],
                         ['Ls', '\u03BCH'],
                         ['Rated motor speed', 'RPM'],
                         ['Rated motor current', 'A'],
                         ['# of motor pole pairs', ''],
                         ['Gear ratio', ''],
                         ['Motor position sensor type', '']]
MOTOR_HALLS = ['Hall sector[0]',
               'Hall sector[1]',
               'Hall sector[2]',
               'Hall sector[3]',
               'Hall sector[4]',
               'Hall sector[5]',
               'Hall sector[6]',
               'Hall sector[7]',
               'Hall offset']
CONTROLLER_MAIN_PARAMETERS = [['Motor position sensor type', ''],
                              ['Remote Speed Command in RPM', 'RPM'],
                              ['Remote maximum braking current', '%'],
                              ['Remote maximum motoring current', '%'],
                              ['Remote speed command', '%'],
                              ['Remote state command', '']]
EFFICIENCY_MAP_LEVELS = [10, 20, 30, 40, 50,
                         60, 65, 66, 67, 68,
                         69, 70, 71, 72, 73,
                         74, 75, 76, 77, 78,
                         79, 80, 81, 82, 83,
                         84, 85, 86, 87, 88,
                         89, 90, 91, 92, 93,
                         94, 95, 96, 97, 98]
YOKO_PARAMETER_FILE = f'{ROOT_DIR}/dyno_v2/yoko_parameter_information.csv'
ABB_PARAMETER_FILE = f"{ROOT_DIR}/dyno_v2/ABB Parameters.xml"

# loading parameters from config.ini
config = ConfigParser()
config.read(f'config.ini')
# Parameters
try:
    TEST_SCRIPTS = config.get('test scripts', 'all').split(',\n')
    OPERATIONAL_TESTS = config.get('test scripts', 'operational').split(',\n')
    TEST_FILTERS = {}
    TEST_MODULES = {}
    TEST_CLASSES = {}
    for f in OPERATIONAL_TESTS:
        TEST_FILTERS[f] = config.get(f, 'not_startswith').split(', ')
        TEST_MODULES[f] = config.get('modules', f)
        TEST_CLASSES[f] = config.get('classes', f)
    CONFIG_MAP = {}
    for key in config.options('config map'):
        CONFIG_MAP[key] = config.get('config map', key, raw=True)
    TEST_KW = config.options('test kw')
    ASI_FOLDBACKS = {}
    for key in config.options('foldbacks'):
        ASI_FOLDBACKS[key] = config.get('foldbacks', key)
except configparser.NoSectionError:
    pass

def get_efficiency_levels(cutout=(0, 100)):
    start_index = 0
    end_index = 0
    for i in EFFICIENCY_MAP_LEVELS:
        if i < cutout[0]:
            start_index += 1
        else:
            break

    for i in reversed(EFFICIENCY_MAP_LEVELS):
        if i > cutout[1]:
            end_index -= 1
        else:
            break

    return EFFICIENCY_MAP_LEVELS[start_index:end_index + 1]