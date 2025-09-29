import sys
sys.path.extend(['C:\\Users\\twu\\PycharmProjects\\dyno-v2'])
from dyno_v2.Module.j1939 import *

if __name__ == '__main__':
    tree = parse_etree('C:/Users/twu/PycharmProjects/dyno-v2/dyno_v2/Dictionary/8004_ASIObjectDictionary.xml')

    com = J1939com(tree=tree, parameters='C:/Users/twu/PycharmProjects/dyno-v2/dyno_v2/Parameter Files/J1939_BAC.xml')
    com.startListening()

    print(com.read("assist level", 239, 1))
    print(com.read("assist speed limit", 239, 1))

    # value = []
    # for i in range(10):
    #     value.append(int(10 - i))
    #
    # com.write("Customer_param_1", value, 239, 10)

    com.__del__()