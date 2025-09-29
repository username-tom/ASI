import random
import can
from dyno_v2.Module.CANcom import CANcom
from dyno_v2.Module.Parameter import Parameter


def value_format(name, value):
    if len(parameters[name].Bits) >= 8:
        return f'{int(value):016b}'
    elif parameters[name].Scale == 'hex':
        return f'{hex(int(value))[2:].upper()}'
    return value

#
com = CANcom()
switch_types = ['Foot',
                'Left',
                'Right']
suffixes = {'Throttle Source': 'enum',
            'Throttle Address': 'hex',
            'Redundant Redundant Address': 'hex',
            'Throttle Voltage Reverse': 1,
            'Throttle Voltage Neutral': 1,
            'Throttle Voltage Forward': 1,
            'Throttle Redundant Voltage Reverse': 1,
            'Throttle Redundant Voltage Forward': 1}
address = 155

parameters = {"Throttle Voltage Reverse Deadband": Parameter("Throttle Voltage Reverse Deadband", 183, 1),
              "Throttle Voltage Neutral Deadband": Parameter("Throttle Voltage Neutral Deadband", 179, 1),
              "Throttle Voltage Forward Deadband": Parameter("Throttle Voltage Forward Deadband", 180, 1),
              "Throttle Reverse Range Dampener": Parameter("Throttle Reverse Range Dampener", 181, 40.96, '%'),
              "Traction Throttle Power Source": Parameter("Traction Throttle Power Source", 184, 'enum'),
              "Throttle Home Range Check Limit": Parameter("Throttle Home Range Check Limit", 185, 40.96, '%')}

for stype in switch_types:
    for suffix in suffixes:
        parameters[f"{stype} {suffix}"] = Parameter(f"{stype} {suffix}", address, suffixes[suffix])
        address += 1

address = 540
for i in range(8):
    if i == 4:
        address -= 12
    parameters[f'Average ADC Raw User{i}'] = Parameter(f'Average ADC Raw User{i}', address, 1)
    address += 1

parameters['Debounced Digital Inputs 1'] = Parameter('Debounced Digital Inputs 1', 570, 'bit vect')
parameters['Debounced Digital Inputs 2'] = Parameter('Debounced Digital Inputs 2', 571, 'bit vect')
parameters['Right Throttle Command'] = Parameter('Right Throttle Command', 582, 40.96, '%')
parameters['Left Throttle Command'] = Parameter('Left Throttle Command', 581, 40.96, '%')
parameters['Foot Throttle Command'] = Parameter('Foot Throttle Command', 580, 40.96, '%')

options = {'Disable': 0, 'Analog': 1, 'CAN': 2}
analogs = ['A1', 'A2', 'A3', 'A4', 'A5', 'B1', 'B2', 'B3']
print("Parameters loaded")

for stype in switch_types:
    for option in options:
        print(f"\n---------Testing {stype} | Source {option}----------")
        com.write(f"{stype} Switch Source", options[option])
        if options[option] == 0:
            print("Address set to 0x0000")
            com.write(f"{stype} Switch Address", 0)
            com.write(f"{stype} Redundant Switch Address", 0)
            status = com.read('VCM Status #1')
            if status & (1 << switch_types.index(stype)) == 0:
                print("PASS: Status is off")
            else:
                print("Failed: Status is on")

            print("Address set to 0x0001")
            com.write(f"{stype} Switch Address", 1)
            status = com.read('VCM Status #1')
            if status & (1 << switch_types.index(stype)) == 1:
                print("PASS: Status is on")
            else:
                print("Failed: Status is off")

            com.write(f"{stype} Switch Address", 0)

        elif options[option] == 1:
            switch = random.choices(analogs, k=2)
            if switch[0] == switch[1]:
                print(f"Using {switch[0]} to validate without Redundant address")
                com.write(f"{stype} Redundant Switch Address", 0)
                raw = []
                for i in range(8):
                    raw.append(com.read(f'Average ADC Raw User{i}'))
                input(f"Turn {switch[0]} to max and press Enter...")
                diff = []
                for i in range(8):
                    diff.append(com.read(f'Average ADC Raw User{i}') - raw[i])
                index = diff.index(max(diff))
                print(f"Analog for {switch[0]} identified...")

                com.write(f"{stype} Switch Address", index)
                status = com.read('VCM Status #1')
                if status & (1 << switch_types.index(stype)) == 1:
                    print("PASS: Status is on")
                else:
                    print("Failed: Status is off")

                input(f"Turn off {switch[0]} and press Enter...")
                status = com.read('VCM Status #1')
                if status & (1 << switch_types.index(stype)) == 0:
                    print("PASS: Status is off")
                else:
                    print("Failed: Status is on")

            else:
                print(f"Using {switch[0]} to validate | {switch[1]} as Redundant address")
                raw = []
                for i in range(8):
                    raw.append(com.read(f'Average ADC Raw User{i}'))
                input(f"Turn {switch[0]} to max and press Enter...")
                diff = []
                for i in range(8):
                    diff.append(com.read(f'Average ADC Raw User{i}') - raw[i])
                index = diff.index(max(diff))
                print(f"Analog for {switch[0]} identified...")

                input(f"Turn off {switch[0]}, turn on {switch[1]} and press Enter...")
                raw = []
                for i in range(8):
                    raw.append(com.read(f'Average ADC Raw User{i}'))
                input(f"Turn {switch[1]} to max and press Enter...")
                diff = []
                for i in range(8):
                    diff.append(com.read(f'Average ADC Raw User{i}') - raw[i])
                index = diff.index(max(diff))
                print(f"Analog for {switch[1]} identified...")
                com.write(f"{stype} Redundant Switch Address", index)

                com.write("Switch Off Voltage", 0.4 * diff[index])
                com.write("Switch On Voltage", 0.6 * diff[index])

                input(f"Turn {switch[0]} and {switch[1]} to maximum. And then press Enter...")
                status = com.read('VCM Status #1')
                if status & (1 << switch_types.index(stype)) == 1:
                    print("PASS: Status is on")
                else:
                    print("Failed: Status is off")

                input(f"Turn {switch[0]} and {switch[1]} to minimum. And then press Enter...")
                status = com.read('VCM Status #1')
                if status & (1 << switch_types.index(stype)) == 0:
                    print("PASS: Status is off")
                else:
                    print("Failed: Status is on")

                input(f"Turn {switch[0]} only to maximum and press Enter...")
                status = com.read('VCM Status #1')
                if status & (1 << (switch_types.index(stype) + 8)) == 0:
                    print("PASS: Error status is triggered")
                else:
                    print("Failed: Error status failed to trigger")

            com.write(f"{stype} Switch Source", 0)
            com.write(f"{stype} Switch Address", 0)
            com.write(f"{stype} Redundant Switch Address", 0)

        else:
            on_msg = can.Message(arbitration_id=0x301, data=[0x40])
            off_msg = can.Message(arbitration_id=0x301, data=[0x80])
            print("Testing OFF state")
            com.write(f"{stype} Switch Address", 6)
            com.write(f"{stype} Redundant Switch Address", 0)

            com.msg_buffer.put(off_msg)

            status = com.read('VCM Status #1')
            if status & (1 << switch_types.index(stype)) == 0:
                print("PASS: Status is off")
            else:
                print("Failed: Status is on")

            print("Testing ON state")

            com.msg_buffer.put(on_msg)

            status = com.read('VCM Status #1')
            if status & (1 << switch_types.index(stype)) == 1:
                print("PASS: Status is on")
            else:
                print("Failed: Status is off")

            com.write(f"{stype} Switch Source", 0)
            com.write(f"{stype} Switch Address", 0)
            com.write(f"{stype} Redundant Switch Address", 0)

print("Test over")