from dyno_v2.Module.asi_controller import ASIController
import can
from can.interfaces.pcan.pcan import PcanBus
from dyno_v2.Module.util import signed


can_messages = {"1_1_1": can.Message(arbitration_id=0x123, data=[0x01, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_1_2": can.Message(arbitration_id=0x124, data=[0x02, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_1_3": can.Message(arbitration_id=0x125, data=[0x03, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_1_4": can.Message(arbitration_id=0x126, data=[0x04, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_1_5": can.Message(arbitration_id=0x127, data=[0x05, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_1_6": can.Message(arbitration_id=0x128, data=[0x06, 0x07, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_1_7": can.Message(arbitration_id=0x129, data=[0x07, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_1_8": can.Message(arbitration_id=0x12A, data=[0x08, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_1_9": can.Message(arbitration_id=0x12B, data=[0x09, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_1_10": can.Message(arbitration_id=0x12C, data=[0x0A, 0x0B, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_1_11": can.Message(arbitration_id=0x12D, data=[0x0B, 0x0C, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_1_12": can.Message(arbitration_id=0x12E, data=[0x0C, 0x0D, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_2_1": can.Message(arbitration_id=0x122, data=[0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_2_2": can.Message(arbitration_id=0x124, data=[0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_2_3": can.Message(arbitration_id=0x135, data=[0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_2_4": can.Message(arbitration_id=0x116, data=[0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_2_5": can.Message(arbitration_id=0x227, data=[0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_2_6": can.Message(arbitration_id=0x27, data=[0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_2_7": can.Message(arbitration_id=0x129, data=[0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_2_8": can.Message(arbitration_id=0x128, data=[0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_2_9": can.Message(arbitration_id=0x13A, data=[0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_2_10": can.Message(arbitration_id=0x11B, data=[0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_2_11": can.Message(arbitration_id=0x22C, data=[0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_2_12": can.Message(arbitration_id=0x2D, data=[0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_2_13": can.Message(arbitration_id=0x12F, data=[0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_3_1": can.Message(arbitration_id=0x123, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_3_2": can.Message(arbitration_id=0x124, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_3_3": can.Message(arbitration_id=0x125, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_3_4": can.Message(arbitration_id=0x126, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_3_5": can.Message(arbitration_id=0x127, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_3_6": can.Message(arbitration_id=0x128, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "1_3_7": can.Message(arbitration_id=0x129, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_3_8": can.Message(arbitration_id=0x12A, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_3_9": can.Message(arbitration_id=0x12B, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_3_10": can.Message(arbitration_id=0x12C, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_3_11": can.Message(arbitration_id=0x12D, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "1_3_12": can.Message(arbitration_id=0x12E, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "2_1_1": can.Message(arbitration_id=0x180, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=True),
                "2_1_2": can.Message(arbitration_id=0x181, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=True),
                "2_1_3": can.Message(arbitration_id=0x182, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=True),
                "2_1_4": can.Message(arbitration_id=0x183, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=True),
                "2_1_5": can.Message(arbitration_id=0x184, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=True),
                "2_1_6": can.Message(arbitration_id=0x185, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=True),
                "2_1_7": can.Message(arbitration_id=0x186, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=True),
                "2_1_8": can.Message(arbitration_id=0x187, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=True),
                "2_1_9": can.Message(arbitration_id=0x188, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=True),
                "2_1_10": can.Message(arbitration_id=0x189, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                      is_extended_id=False, is_remote_frame=True),
                "2_1_11": can.Message(arbitration_id=0x18A, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                      is_extended_id=False, is_remote_frame=True),
                "2_1_12": can.Message(arbitration_id=0x18B, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                      is_extended_id=False, is_remote_frame=True),
                "3_2_1": can.Message(arbitration_id=0x22A, data=[0x01, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "3_2_2": can.Message(arbitration_id=0x32A, data=[0x02, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "3_2_3": can.Message(arbitration_id=0x42A, data=[0x03, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "3_2_4": can.Message(arbitration_id=0x52A, data=[0x04, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "3_3_1": can.Message(arbitration_id=0x22A, data=[0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "3_3_2": can.Message(arbitration_id=0x32A, data=[0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "3_3_3": can.Message(arbitration_id=0x42A, data=[0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "3_3_4": can.Message(arbitration_id=0x52A, data=[0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "3_3_5": can.Message(arbitration_id=0x127, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "3_3_6": can.Message(arbitration_id=0x128, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=False, is_remote_frame=False),
                "3_3_7": can.Message(arbitration_id=0x129, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "3_3_8": can.Message(arbitration_id=0x12A, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "3_3_9": can.Message(arbitration_id=0x12B, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "3_3_10": can.Message(arbitration_id=0x12C, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                      is_extended_id=True, is_remote_frame=False),
                "3_3_11": can.Message(arbitration_id=0x12D, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                      is_extended_id=True, is_remote_frame=False),
                "3_3_12": can.Message(arbitration_id=0x12E, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                      is_extended_id=True, is_remote_frame=False),
                "3_3_13": can.Message(arbitration_id=0x23A, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                      is_extended_id=False, is_remote_frame=False),
                "3_3_14": can.Message(arbitration_id=0x33A, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                      is_extended_id=False, is_remote_frame=False),
                "3_3_15": can.Message(arbitration_id=0x43A, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                      is_extended_id=False, is_remote_frame=False),
                "3_3_16": can.Message(arbitration_id=0x53A, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                      is_extended_id=False, is_remote_frame=False),
                "4_1_1": can.Message(arbitration_id=0x23A, data=[0x01, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "4_1_2": can.Message(arbitration_id=0x33A, data=[0x02, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "4_1_3": can.Message(arbitration_id=0x43A, data=[0x03, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "4_1_4": can.Message(arbitration_id=0x53A, data=[0x04, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "4_2_1": can.Message(arbitration_id=0x23A, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "4_2_2": can.Message(arbitration_id=0x33A, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "4_2_3": can.Message(arbitration_id=0x43A, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "4_2_4": can.Message(arbitration_id=0x53A, data=[0x0, 0x0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "4_3_1": can.Message(arbitration_id=0x63A, data=[0x2B, 0x1F, 0x20, 0x21, 0x34, 0x12, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "4_3_2": can.Message(arbitration_id=0x63A, data=[0x40, 0x1F, 0x20, 0x21, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "4_3_3": can.Message(arbitration_id=0x63A, data=[0x2B, 0x1F, 0x20, 0x21, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False),
                "4_3_4": can.Message(arbitration_id=0x63A, data=[0x40, 0x1F, 0x20, 0x21, 0x00, 0x00, 0x00, 0x00],
                                     is_extended_id=True, is_remote_frame=False)
                }

def load_params():
    ################## Load Parameter ###################
    dut.load_parameters("C:\\Users\\twu\\PycharmProjects\\dyno-v2\\dyno_v2\\Parameter Files\\92-000236 can Firmware Validation Params.xml")
    # for i in range(12):
    #     dut.write(f"TPDO{i + 1} event time", 0)

    dut.save_to_flash()
    input("Power cycle and Enter")

    print('\nTC 5.5.1 Custom PDO Mapping\nLoading parameter')

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '180h       | 2      | 00 00              | 100\n'
          '181h       | 2      | 00 00              | 100\n'
          '182h       | 2      | 00 00              | 100\n'
          '183h       | 2      | 00 00              | 100\n'
          '184h       | 2      | 00 00              | 100\n'
          '185h       | 2      | 00 00              | 100\n'
          '00000186h  | 2      | 00 00              | 100\n'
          '00000187h  | 2      | 00 00              | 100\n'
          '00000188h  | 2      | 00 00              | 100\n'
          '00000189h  | 2      | 00 00              | 100\n'
          '0000018Ah  | 2      | 00 00              | 100\n'
          '0000018Bh  | 2      | 00 00              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.1 Loading parameter Failed')
    else:
        print('5.5.1 Parameters loaded')

def tc_5_5_1_1():
    ########### 5.5.1 Test 1 #############
    for i in range(12):
        msg = can_messages[f"1_1_{i + 1}"]
        dut_can.send(msg)

    print('\nTC 5.5.1 Custom PDO Mapping\nTest 1')

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '180h       | 2      | 01 02              | 100\n'
          '181h       | 2      | 02 03              | 100\n'
          '182h       | 2      | 03 04              | 100\n'
          '183h       | 2      | 04 05              | 100\n'
          '184h       | 2      | 05 06              | 100\n'
          '185h       | 2      | 06 07              | 100\n'
          '00000186h  | 2      | 07 08              | 100\n'
          '00000187h  | 2      | 08 09              | 100\n'
          '00000188h  | 2      | 09 0A              | 100\n'
          '00000189h  | 2      | 0A 0B              | 100\n'
          '0000018Ah  | 2      | 0B 0C              | 100\n'
          '0000018Bh  | 2      | 0C 0D              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.1 Test 1 Failed')
    else:
        print('5.5.1 Test 1 Pass')

def tc_5_5_1_2():
    ########## 5.5.1 Test 2 #############
    for i in range(13):
        msg = can_messages[f"1_2_{i + 1}"]
        dut_can.send(msg)

    print('\nTC 5.5.1 Custom PDO Mapping\nTest 2')

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '180h       | 2      | 01 02              | 100\n'
          '181h       | 2      | 02 03              | 100\n'
          '182h       | 2      | 03 04              | 100\n'
          '183h       | 2      | 04 05              | 100\n'
          '184h       | 2      | 05 06              | 100\n'
          '185h       | 2      | 06 07              | 100\n'
          '00000186h  | 2      | 07 08              | 100\n'
          '00000187h  | 2      | 08 09              | 100\n'
          '00000188h  | 2      | 09 0A              | 100\n'
          '00000189h  | 2      | 0A 0B              | 100\n'
          '0000018Ah  | 2      | 0B 0C              | 100\n'
          '0000018Bh  | 2      | 0C 0D              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.1 Test 2 Failed')
    else:
        print('5.5.1 Test 2 Pass')

def tc_5_5_1_3():
    ########## 5.5.1 Test 3 #############
    for i in range(12):
        msg = can_messages[f"1_3_{i + 1}"]
        dut_can.send(msg)

    print('\nTC 5.5.1 Custom PDO Mapping\nTest 3')

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '180h       | 2      | 00 00              | 100\n'
          '181h       | 2      | 00 00              | 100\n'
          '182h       | 2      | 00 00              | 100\n'
          '183h       | 2      | 00 00              | 100\n'
          '184h       | 2      | 00 00              | 100\n'
          '185h       | 2      | 00 00              | 100\n'
          '00000186h  | 2      | 00 00              | 100\n'
          '00000187h  | 2      | 00 00              | 100\n'
          '00000188h  | 2      | 00 00              | 100\n'
          '00000189h  | 2      | 00 00              | 100\n'
          '0000018Ah  | 2      | 00 00              | 100\n'
          '0000018Bh  | 2      | 00 00              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.1 Test 3 Failed')
    else:
        print('5.5.1 Test 3 Pass')

    print('TC 5.5.1 Passed')

def tc_5_5_2_setup():
    ########## 5.5.2 Set up #############
    print('\nTC 5.5.2 CAN RTR Functionality\nSet up')

    dut.write(58, (1 << 14) + (1 << 7) + (1 << 4))
    dut.save_to_flash()
    input("Power cycle and Enter")

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.2 Set up Failed')
    else:
        print('5.5.2 Set up Successful')

def tc_5_5_2_1():
    ########### 5.5.2 Test 1 #############
    for i in range(12):
        msg = can_messages[f"1_1_{i + 1}"]
        dut_can.send(msg)
    for i in range(12):
        msg = can_messages[f"2_1_{i + 1}"]
        dut_can.send(msg)

    print('\nTC 5.5.2 CAN RTR Functionality\nTest 1')

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time | Count\n'
          '123h       | 2      | 01 02              |            | 1\n'
          '124h       | 2      | 02 03              |            | 1\n'
          '125h       | 2      | 03 04              |            | 1\n'
          '126h       | 2      | 04 05              |            | 1\n'
          '127h       | 2      | 05 06              |            | 1\n'
          '128h       | 2      | 06 07              |            | 1\n'
          '00000129h  | 2      | 07 08              |            | 1\n'
          '0000012Ah  | 2      | 08 09              |            | 1\n'
          '0000012Bh  | 2      | 09 0A              |            | 1\n'
          '0000012Ch  | 2      | 0A 0B              |            | 1\n'
          '0000012Dh  | 2      | 0B 0C              |            | 1\n'
          '0000012Eh  | 2      | 0C 0D              |            | 1\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.2 Test 1 Failed')
    else:
        print('5.5.2 Test 1 Pass')

def tc_5_5_2_2():
    ########### 5.5.2 Test 2 #############
    for i in range(12):
        msg = can_messages[f"1_3_{i + 1}"]
        dut_can.send(msg)
    for i in range(12):
        msg = can_messages[f"2_1_{i + 1}"]
        dut_can.send(msg)

    print('\nTC 5.5.2 CAN RTR Functionality\nTest 1')

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time | Count\n'
          '123h       | 2      | 00 00              |            | 1\n'
          '124h       | 2      | 00 00              |            | 1\n'
          '125h       | 2      | 00 00              |            | 1\n'
          '126h       | 2      | 00 00              |            | 1\n'
          '127h       | 2      | 00 00              |            | 1\n'
          '128h       | 2      | 00 00              |            | 1\n'
          '00000129h  | 2      | 00 00              |            | 1\n'
          '0000012Ah  | 2      | 00 00              |            | 1\n'
          '0000012Bh  | 2      | 00 00              |            | 1\n'
          '0000012Ch  | 2      | 00 00              |            | 1\n'
          '0000012Dh  | 2      | 00 00              |            | 1\n'
          '0000012Eh  | 2      | 00 00              |            | 1\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.2 Test 2 Failed')
    else:
        print('5.5.2 Test 2 Pass')

    print('TC 5.5.2 Passed')

def tc_5_5_3_setup():
    ########## 5.5.3 Set up #############
    print('\nTC 5.5.3 Autoset CANopen COBIDs\nSet up')

    dut.write(58, (1 << 5) + (1 << 6) + (1 << 7) + (1 << 4))
    dut.save_to_flash()
    input("Power cycle and Enter")

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '184h       | 2      | 00 00              | 100\n'
          '185h       | 2      | 00 00              | 100\n'
          '00000186h  | 2      | 00 00              | 100\n'
          '00000187h  | 2      | 00 00              | 100\n'
          '00000188h  | 2      | 00 00              | 100\n'
          '00000189h  | 2      | 00 00              | 100\n'
          '0000018Ah  | 2      | 00 00              | 100\n'
          '0000018Bh  | 2      | 00 00              | 100\n'
          '1AAh       | 2      | 00 00              | 100\n'
          '2AAh       | 2      | 00 00              | 100\n'
          '3AAh       | 2      | 00 00              | 100\n'
          '4AAh       | 2      | 00 00              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.3 Set up Failed')
    else:
        print('5.5.3 Set up Pass')

def tc_5_5_3_1():
    ########### 5.5.3 Test 1 #############
    for i in range(12):
        msg = can_messages[f"1_1_{i + 1}"]
        dut_can.send(msg)

    print('\nTC 5.5.3 Autoset CANopen COBIDs\nTest 1')

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '184h       | 2      | 05 06              | 100\n'
          '185h       | 2      | 06 07              | 100\n'
          '00000186h  | 2      | 07 08              | 100\n'
          '00000187h  | 2      | 08 09              | 100\n'
          '00000188h  | 2      | 09 0A              | 100\n'
          '00000189h  | 2      | 0A 0B              | 100\n'
          '0000018Ah  | 2      | 0B 0C              | 100\n'
          '0000018Bh  | 2      | 0C 0D              | 100\n'
          '1AAh       | 2      | 00 00              | 100\n'
          '2AAh       | 2      | 00 00              | 100\n'
          '3AAh       | 2      | 00 00              | 100\n'
          '4AAh       | 2      | 00 00              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.3 Test 1 Failed')
    else:
        print('5.5.3 Test 1 Pass')

def tc_5_5_3_2():
    ########### 5.5.3 Test 2 #############
    for i in range(4):
        msg = can_messages[f"3_2_{i + 1}"]
        dut_can.send(msg)

    print('\nTC 5.5.3 Autoset CANopen COBIDs\nTest 2')

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '184h       | 2      | 05 06              | 100\n'
          '185h       | 2      | 06 07              | 100\n'
          '00000186h  | 2      | 07 08              | 100\n'
          '00000187h  | 2      | 08 09              | 100\n'
          '00000188h  | 2      | 09 0A              | 100\n'
          '00000189h  | 2      | 0A 0B              | 100\n'
          '0000018Ah  | 2      | 0B 0C              | 100\n'
          '0000018Bh  | 2      | 0C 0D              | 100\n'
          '1AAh       | 2      | 01 02              | 100\n'
          '2AAh       | 2      | 02 03              | 100\n'
          '3AAh       | 2      | 03 04              | 100\n'
          '4AAh       | 2      | 04 05              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.3 Test 2 Failed')
    else:
        print('5.5.3 Test 2 Pass')

def tc_5_5_3_3():
    ########### 5.5.3 Test 3 #############
    dut.write(57, 58)
    dut.save_to_flash()
    input("Power cycle and Enter")

    for i in range(12):
        msg = can_messages[f"3_3_{i + 1}"]
        dut_can.send(msg)

    print('\nTC 5.5.3 Autoset CANopen COBIDs\nTest 3 Part 1')

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '184h       | 2      | 00 00              | 100\n'
          '185h       | 2      | 00 00              | 100\n'
          '00000186h  | 2      | 00 00              | 100\n'
          '00000187h  | 2      | 00 00              | 100\n'
          '00000188h  | 2      | 00 00              | 100\n'
          '00000189h  | 2      | 00 00              | 100\n'
          '0000018Ah  | 2      | 00 00              | 100\n'
          '0000018Bh  | 2      | 00 00              | 100\n'
          '1BAh       | 2      | 01 02              | 100\n'
          '2BAh       | 2      | 02 03              | 100\n'
          '3BAh       | 2      | 03 04              | 100\n'
          '4BAh       | 2      | 04 05              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.3 Test 3 Part 1 Failed')
    else:
        print('5.5.3 Test 3 Part 1 Pass')

    for i in range(4):
        msg = can_messages[f"3_3_{i + 13}"]
        dut_can.send(msg)

    print('\nTC 5.5.3 Autoset CANopen COBIDs\nTest 2 Part 2')

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '184h       | 2      | 00 00              | 100\n'
          '185h       | 2      | 00 00              | 100\n'
          '00000186h  | 2      | 00 00              | 100\n'
          '00000187h  | 2      | 00 00              | 100\n'
          '00000188h  | 2      | 00 00              | 100\n'
          '00000189h  | 2      | 00 00              | 100\n'
          '0000018Ah  | 2      | 00 00              | 100\n'
          '0000018Bh  | 2      | 00 00              | 100\n'
          '1BAh       | 2      | 00 00              | 100\n'
          '2BAh       | 2      | 00 00              | 100\n'
          '3BAh       | 2      | 00 00              | 100\n'
          '4BAh       | 2      | 00 00              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.3 Test 3 Part 2 Failed')
    else:
        print('5.5.3 Test 3 Part 2 Pass')

    print('TC 5.5.3 Passed')

def tc_5_5_4_setup():
    ########## 5.5.4 Set up #############
    print('\nTC 5.5.4 Extended 29-bit ID\nSet up')

    dut.write(58, (1 << 5) + (1 << 6) + (1 << 7) + (1 << 4) + 1)
    dut.save_to_flash()
    input("Power cycle and Enter")

    print('\nTC 5.5.4 Extended 29-bit ID\nSet up')

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '184h       | 2      | 00 00              | 100\n'
          '185h       | 2      | 00 00              | 100\n'
          '00000186h  | 2      | 00 00              | 100\n'
          '00000187h  | 2      | 00 00              | 100\n'
          '00000188h  | 2      | 00 00              | 100\n'
          '00000189h  | 2      | 00 00              | 100\n'
          '0000018Ah  | 2      | 00 00              | 100\n'
          '0000018Bh  | 2      | 00 00              | 100\n'
          '000001BAh  | 2      | 00 00              | 100\n'
          '000002BAh  | 2      | 00 00              | 100\n'
          '000003BAh  | 2      | 00 00              | 100\n'
          '000004BAh  | 2      | 00 00              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.4 Set up Failed')
    else:
        print('5.5.4 Set up Pass')

def tc_5_5_4_1():
    ########### 5.5.4 Test 1 #############
    for i in range(4):
        msg = can_messages[f"4_1_{i + 1}"]
        dut_can.send(msg)

    print('\nTC 5.5.4 Extended 29-bit ID\nTest 1')

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '184h       | 2      | 00 00              | 100\n'
          '185h       | 2      | 00 00              | 100\n'
          '00000186h  | 2      | 00 00              | 100\n'
          '00000187h  | 2      | 00 00              | 100\n'
          '00000188h  | 2      | 00 00              | 100\n'
          '00000189h  | 2      | 00 00              | 100\n'
          '0000018Ah  | 2      | 00 00              | 100\n'
          '0000018Bh  | 2      | 00 00              | 100\n'
          '000001BAh  | 2      | 01 02              | 100\n'
          '000002BAh  | 2      | 02 03              | 100\n'
          '000003BAh  | 2      | 03 04              | 100\n'
          '000004BAh  | 2      | 04 05              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.4 Test 1 Failed')
    else:
        print('5.5.4 Test 1 Pass')

def tc_5_5_4_2():
    ########### 5.5.4 Test 2 #############
    for i in range(4):
        msg = can_messages[f"4_2_{i + 1}"]
        dut_can.send(msg)

    print('\nTC 5.5.4 Extended 29-bit ID\nTest 2')

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '184h       | 2      | 00 00              | 100\n'
          '185h       | 2      | 00 00              | 100\n'
          '00000186h  | 2      | 00 00              | 100\n'
          '00000187h  | 2      | 00 00              | 100\n'
          '00000188h  | 2      | 00 00              | 100\n'
          '00000189h  | 2      | 00 00              | 100\n'
          '0000018Ah  | 2      | 00 00              | 100\n'
          '0000018Bh  | 2      | 00 00              | 100\n'
          '000001BAh  | 2      | 00 00              | 100\n'
          '000002BAh  | 2      | 00 00              | 100\n'
          '000003BAh  | 2      | 00 00              | 100\n'
          '000004BAh  | 2      | 00 00              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.4 Test 2 Failed')
    else:
        print('5.5.4 Test 2 Pass')

def tc_5_5_4_3():
    ########### 5.5.4 Test 3 #############
    print('\nTC 5.5.4 Extended 29-bit ID\nTest 3')
    ans = [['0x60', '0x1F', '0x20', '0x21', 0, 0, 0, 0],
           ['0x4B', '0x1F', '0x20', '0x21', '0x34', '0x12', 0, 0],
           ['0x60', '0x1F', '0x20', '0x21', '0x34', '0x12', 0, 0],
           ['0x4B', '0x1F', '0x20', '0x21', 0, 0, 0, 0]]
    for i in range(4):
        msg = can_messages[f"4_3_{i + 1}"]
        dut_can.send(msg)
        response = dut_can.recv()

        print(f'000005BAh | 8  | {ans[i]}')
        match = input("Y/N")
        if match.lower() == 'n':
            exit(f'5.5.4 Test 3 Message {i + 1} Failed')
        else:
            print(f'5.5.4 Test 3 Message {i + 1} Pass')

    print('TC 5.5.4 Passed')

def tc_5_5_5_setup():
    ########## 5.5.5 Set up #############
    print('\nTC 5.5.5 Auto CAN ID adjustments\nSet up')

    dut.write(58, (1 << 5) + (1 << 6) + (1 << 7) + (1 << 4) + (1 << 13))
    dut.save_to_flash()
    input("Disconnect Pedal, Power cycle and Enter")

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '184h       | 2      | 00 00              | 100\n'
          '185h       | 2      | 00 00              | 100\n'
          '00000186h  | 2      | 00 00              | 100\n'
          '00000187h  | 2      | 00 00              | 100\n'
          '00000188h  | 2      | 00 00              | 100\n'
          '00000189h  | 2      | 00 00              | 100\n'
          '0000018Ah  | 2      | 00 00              | 100\n'
          '0000018Bh  | 2      | 00 00              | 100\n'
          '1BAh       | 2      | 00 00              | 100\n'
          '2BAh       | 2      | 00 00              | 100\n'
          '3BAh       | 2      | 00 00              | 100\n'
          '4BAh       | 2      | 00 00              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.5 Set up Failed')
    else:
        print('5.5.5 Set up Pass')

def tc_5_5_5_1():
    ########### 5.5.5 Test 1 #############
    print('\nTC 5.5.5 Auto CAN ID adjustments\nTest 1')

    if signed(int(dut.modbus.modbus.read_register(1676))) != signed(int(dut.modbus.modbus.read_register(57))):
        exit('5.5.5 Test 1 Failed')
    else:
        print('5.5.5 Test 1 Pass')

def tc_5_5_5_2():
    ########### 5.5.5 Test 2 #############
    print('\nTC 5.5.5 Auto CAN ID adjustments\nTest 2')

    dut.write(1919, 1 << 4)
    dut.save_to_flash()
    input("Power cycle and Enter")

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '184h       | 2      | 00 00              | 100\n'
          '185h       | 2      | 00 00              | 100\n'
          '00000186h  | 2      | 00 00              | 100\n'
          '00000187h  | 2      | 00 00              | 100\n'
          '00000188h  | 2      | 00 00              | 100\n'
          '00000189h  | 2      | 00 00              | 100\n'
          '0000018Ah  | 2      | 00 00              | 100\n'
          '0000018Bh  | 2      | 00 00              | 100\n'
          '1BBh       | 2      | 00 00              | 100\n'
          '2BBh       | 2      | 00 00              | 100\n'
          '3BBh       | 2      | 00 00              | 100\n'
          '4BBh       | 2      | 00 00              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.5 Test 2 Failed')
    else:
        if signed(int(dut.modbus.modbus.read_register(1676))) != signed(int(dut.modbus.modbus.read_register(57)) + 1):
            exit('5.5.5 Test 2 Failed')
        else:
            print('5.5.5 Test 2 Pass')

def tc_5_5_5_3():
    ########### 5.5.5 Test 3 #############
    print('\nTC 5.5.5 Auto CAN ID adjustments\nTest 3')

    dut.write(1919, (1 << 4) + (1 << 3))
    dut.save_to_flash()
    input("Power cycle and Enter")

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '184h       | 2      | 00 00              | 100\n'
          '185h       | 2      | 00 00              | 100\n'
          '00000186h  | 2      | 00 00              | 100\n'
          '00000187h  | 2      | 00 00              | 100\n'
          '00000188h  | 2      | 00 00              | 100\n'
          '00000189h  | 2      | 00 00              | 100\n'
          '0000018Ah  | 2      | 00 00              | 100\n'
          '0000018Bh  | 2      | 00 00              | 100\n'
          '1BDh       | 2      | 00 00              | 100\n'
          '2BDh       | 2      | 00 00              | 100\n'
          '3BDh       | 2      | 00 00              | 100\n'
          '4BDh       | 2      | 00 00              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.5 Test 3 Failed')
    else:
        if signed(int(dut.modbus.modbus.read_register(1676))) != signed(int(dut.modbus.modbus.read_register(57)) + 3):
            exit('5.5.5 Test 3 Failed')
        else:
            print('5.5.5 Test 3 Pass')

def tc_5_5_5_4():
    ########### 5.5.5 Test 4 #############
    print('\nTC 5.5.5 Auto CAN ID adjustments\nTest 4')

    dut.write(1919, (1 << 3))
    dut.save_to_flash()
    input("Power cycle and Enter")

    print('Reset PCAN-View -> Confirm PCAN-View Messages as follow\n'
          'CAN-ID     | Length | Data               | Cycle Time\n'
          '184h       | 2      | 00 00              | 100\n'
          '185h       | 2      | 00 00              | 100\n'
          '00000186h  | 2      | 00 00              | 100\n'
          '00000187h  | 2      | 00 00              | 100\n'
          '00000188h  | 2      | 00 00              | 100\n'
          '00000189h  | 2      | 00 00              | 100\n'
          '0000018Ah  | 2      | 00 00              | 100\n'
          '0000018Bh  | 2      | 00 00              | 100\n'
          '1BCh       | 2      | 00 00              | 100\n'
          '2BCh       | 2      | 00 00              | 100\n'
          '3BCh       | 2      | 00 00              | 100\n'
          '4BCh       | 2      | 00 00              | 100\n')

    match = input("Y/N")
    if match.lower() == 'n':
        exit('5.5.5 Test 4 Failed')
    else:
        if signed(int(dut.modbus.modbus.read_register(1676))) != signed(int(dut.modbus.modbus.read_register(57)) + 2):
            exit('5.5.5 Test 4 Failed')
        else:
            print('5.5.5 Test 4 Pass')


if __name__ == "__main__":
    dut = ASIController("COM25", baud_rate=115200, mb_address=1,
                        root="C:\\Users\\twu\\PycharmProjects\\dyno-v2", all_params=True)

    dut_can = PcanBus(channel='PCAN_USBBUS1', bitrate=250000)

    load_params()
    tc_5_5_1_1()
    tc_5_5_1_2()
    tc_5_5_1_3()

    tc_5_5_2_setup()
    tc_5_5_2_1()
    tc_5_5_2_2()

    tc_5_5_3_setup()
    tc_5_5_3_1()
    tc_5_5_3_2()
    tc_5_5_3_3()

    tc_5_5_4_setup()
    tc_5_5_4_1()
    tc_5_5_4_2()
    tc_5_5_4_3()

    tc_5_5_5_setup()
    tc_5_5_5_1()
    tc_5_5_5_2()
    tc_5_5_5_3()
    tc_5_5_5_4()

    print('TC 5.5.1 Passed\n'
          'TC 5.5.2 Passed\n'
          'TC 5.5.3 Passed\n'
          'TC 5.5.4 Passed\n'
          'TC 5.5.5 Passed\n'
          'Please carry out TC 5.5.6 on PCAN-View')
