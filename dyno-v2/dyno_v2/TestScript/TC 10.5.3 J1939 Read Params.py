import sys
sys.path.extend(['C:\\Users\\twu\\PycharmProjects\\dyno-v2'])
from dyno_v2.Module.j1939 import *

if __name__ == '__main__':
    tree = parse_etree('C:/Users/twu/PycharmProjects/dyno-v2/dyno_v2/Dictionary/8004_ASIObjectDictionary.xml')

    com = J1939com(tree=tree, parameters='C:/Users/twu/PycharmProjects/dyno-v2/dyno_v2/Parameter Files/J1939_BAC.xml')
    com.startListening()

    # Test 1
    # print(com.read("Wheel diameter", 239, 1)[0] / 25.4)

    # Test 2
    com.write("Vehicle maximum speed (Race mode Throttle max speed)", [10], 239, 1)
    com.write("Features", [0x800], 239, 1)
    com.write("write parameters to flash", [0x7fff], 239, length=1)

    input("Power cycle and Enter")

    print(com.read("Vehicle maximum speed (Race mode PAS max speed)", 239, 1))
    print(com.read("Vehicle maximum speed (Street mode PAS max speed)", 239, 1))
    print(com.read("Vehicle maximum speed (Race mode Throttle max speed)", 239, 1))
    print(com.read("Vehicle maximum speed (Street mode Throttle max speed)", 239, 1))

    current_features = int(com.read("Features", 239, 1)[0])
    print(f'Features - {current_features:016b}')

    com.write("Vehicle maximum speed (Race mode Throttle max speed)", [10], 239, 1)
    com.write("Features", [0x8800], 239, 1)
    print(f'Features - {int(com.read("Features", 239, 1)[0]):016b}')
    com.write("write parameters to flash", [0x7fff], 239, length=1)
    print(com.read("Vehicle maximum speed (Race mode Throttle max speed)", 239, 1))

    input("Power cycle and Enter")

    print(com.read("Vehicle maximum speed (Race mode Throttle max speed)", 239, 1))

    com.__del__()