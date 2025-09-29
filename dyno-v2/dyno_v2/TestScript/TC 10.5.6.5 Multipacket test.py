import sys
sys.path.extend(['C:\\Users\\twu\\PycharmProjects\\dyno-v2'])
from dyno_v2.Module.j1939 import *
from dyno_v2.Module.TTLcom import *

if __name__ == '__main__':
    tree = parse_etree('C:/Users/twu/PycharmProjects/dyno-v2/dyno_v2/Dictionary/8004_ASIObjectDictionary.xml')

    ttl = TTLcom('COM5', 115200, 1)
    for i in range(10):
        ttl.write(2016 + i, int(1 + i))

    for i in range(10):
        print(f"{2016 + i} - {ttl.read(2016 + i)}")

    com = J1939com(tree=tree, parameters='C:/Users/twu/PycharmProjects/dyno-v2/dyno_v2/Parameter Files/J1939_BAC.xml')
    com.startListening()

    print(com.read("Customer_param_1", 239, 10))

    value = []
    for i in range(10):
        value.append(int(10 - i))

    com.write("Customer_param_1", value, 239, 10)

    for i in range(10):
        print(f"{2016 + i} - {ttl.read(2016 + i)}")

    com.__del__()