import sys
sys.path.extend(['C:\\Users\\twu\\PycharmProjects\\dyno-v2'])
from dyno_v2.Module.j1939 import *
from dyno_v2.Module.TTLcom import *

if __name__ == '__main__':
    tree = parse_etree('C:/Users/twu/PycharmProjects/dyno-v2/dyno_v2/Dictionary/8004_ASIObjectDictionary.xml')

    parameter_tree = parse_etree('C:/Users/twu/OneDrive - Accelerated Systems/Desktop/DynoController params.xml')

    indexes = {}
    previous = -1
    start = 0
    for p in parameter_tree.findall('SerializableParameter'):
        p_address = int(p.find('Address').text)
        if p_address == previous + 1:
            previous = p_address
        else:
            indexes[start] = previous - start + 1
            previous = p_address
            start = p_address
    indexes[start] = previous - start + 1
    print(indexes)
    values = {}
    for l in indexes:
        values[l] = []
        for p in parameter_tree.findall('SerializableParameter'):
            p_address = int(p.find('Address').text)
            if l <= p_address < indexes[l] + l:
                p_value = int(p.find('Value').text)
                values[l].append(p_value)
    print(values)

    com = J1939com(tree=tree, parameters='C:/Users/twu/PycharmProjects/dyno-v2/dyno_v2/Parameter Files/J1939_BAC.xml')
    com.startListening()

    for i in values:
        result = com.write(i, values[i], 239, indexes[i])
        if result:
            print(f"Write successful with length {indexes[i]} starting from {i}")

    com.__del__()