def signed(value):
    if value & (1 << 15) > 0:
        # This is a negative number
        value -= (1 << 16)
    return value

def can_send_msg(value):
    """

    Args:
        value: Data to be written

    Returns:
        Data formatted for can Message

    """
    try:
        if value > 0x7fff:
            byte_4 = value & 0xff
            byte_5 = (value & 0xff00) >> 8
            byte_6 = (value & 0xff0000) >> 16
            byte_7 = (value & 0xff000000) >> 24
            return [byte_4, byte_5, byte_6, byte_7]  # 4 byte to write
        elif value > 0xfff:
            byte_4 = value & 0xff
            byte_5 = (value & 0xff00) >> 8
            byte_6 = (value & 0xff0000) >> 16
            return [byte_4, byte_5, byte_6, 0]  # 3 byte to write
        elif value > 0:
            byte_4 = value & 0xff
            byte_5 = (value & 0xff00) >> 8
            return [hex(byte_4), hex(byte_5), 0, 0]  # 2 byte to write
        elif value <= 0:
            value += 0x10000
            byte_4 = value & 0xff
            byte_5 = (value & 0xff00) >> 8
            return [hex(byte_4), hex(byte_5), 0, 0]  # 2 byte to write
    except TypeError:
        print(f"Invalid value {value}")
        return False


# Parameters
zero_angle_offset = 2048
direction = 1

full_forward = 0x44B
if direction == 1:
    neutral = 0x264  # direction == 1
else:
    neutral = 0x7E  # direction == 0
full_reverse = 0x7E

forward_dead_band = 0xFC
neutral_dead_band = 0xFC
reverse_dead_band = 0xFC
forward_offset = 0
neutral_offset = 0
reverse_offset = 0

def result():
    # Calculations
    forward_dead_band_upper = full_forward / 10 + (forward_dead_band / 40.96 / 2 / 100) * (1 + forward_offset / 40.96 / 100) * 409.6
    forward_dead_band_lower = full_forward / 10 - (forward_dead_band / 40.96 / 2 / 100) * (1 - forward_offset / 40.96 / 100) * 409.6
    neutral_dead_band_upper = neutral / 10 + (neutral_dead_band / 40.96 / 2 / 100) * (1 + neutral_offset / 40.96 / 100) * 409.6
    neutral_dead_band_lower = neutral / 10 - (neutral_dead_band / 40.96 / 2 / 100) * (1 - neutral_offset / 40.96 / 100) * 409.6
    reverse_dead_band_upper = full_reverse / 10 + (reverse_dead_band / 40.96 / 2 / 100) * (1 + reverse_offset / 40.96 / 100) * 409.6
    reverse_dead_band_lower = full_reverse / 10 - (reverse_dead_band / 40.96 / 2 / 100) * (1 - reverse_offset / 40.96 / 100) * 409.6

    if direction == 1:
        order = [zero_angle_offset / 10, (zero_angle_offset - 3600) / 10, (zero_angle_offset + 3600) / 10, full_forward / 10, neutral / 10, full_reverse / 10]
        order.sort()
        print(f"Zero Offset: {zero_angle_offset / 10}\nFull Forward: {full_forward / 10}\n"
              f"Neutral: {neutral / 10}\nFull Reverse: {full_reverse / 10}")
        print(f"{order}")
        if ((reverse_dead_band_lower < zero_angle_offset / 10 < forward_dead_band_upper or
             reverse_dead_band_lower < zero_angle_offset / 10 - 360 < forward_dead_band_upper) or
                (reverse_dead_band_lower < zero_angle_offset / 10 + 360 < forward_dead_band_upper or
                 reverse_dead_band_lower < zero_angle_offset / 10 < forward_dead_band_upper)):
            print("Zero crossing within full range")
        else:
            print("Zero crossing GOOD")
        print(f"-----FAULT-----\n"
              f"|\n"
              f"| POS Dead Band - {(forward_dead_band / 40.96 / 2) * (1 + forward_offset / 40.96 / 100):.2f}% - {forward_dead_band_upper:.2f}\u00B0\n"
              f"| POS Calibration - {full_forward / 10}\u00B0 - {hex(full_forward)} - {can_send_msg(full_forward)}\n"
              f"| POS Dead Band - {(forward_dead_band / 40.96 / 2) * (1 - forward_offset / 40.96 / 100):.2f}% - {forward_dead_band_lower:.2f}\u00B0\n"
              f"|\n"
              f"| Forward 100% - {forward_dead_band_lower:.2f}\u00B0 - {can_send_msg(int(forward_dead_band_lower))}\n"
              f"| Forward Range - {forward_dead_band_lower - neutral_dead_band_upper:.2f}\u00B0\n"
              f"| Forward 0% - {neutral_dead_band_upper:.2f}\u00B0 - {can_send_msg(int(neutral_dead_band_upper))}\n"
              f"|\n"
              f"| Neutral Dead Band - {(neutral_dead_band / 40.96 / 2) * (1 + neutral_offset / 40.96 / 100):.2f}% - {neutral_dead_band_upper:.2f}\u00B0\n"
              f"| Neutral Calibration - {neutral / 10}\u00B0 - {hex(neutral)} - {can_send_msg(neutral)}\n"
              f"| Neutral Dead Band - {(neutral_dead_band / 40.96 / 2) * (1 - neutral_offset / 40.96 / 100):.2f}% - {neutral_dead_band_lower:.2f}\u00B0\n"
              f"|\n"
              f"| Reverse 0% - {neutral_dead_band_lower:.2f}\u00B0 - {can_send_msg(int(neutral_dead_band_lower))}\n"
              f"| Reverse Range - {neutral_dead_band_lower - reverse_dead_band_upper:.2f}\u00B0\n"
              f"| Reverse 100% - {reverse_dead_band_upper:.2f}\u00B0 - {can_send_msg(int(reverse_dead_band_upper))}\n"
              f"|\n"
              f"| NEG Dead Band - {(reverse_dead_band / 40.96 / 2) * (1 + reverse_offset / 40.96 / 100):.2f}% - {reverse_dead_band_upper:.2f}\u00B0\n"
              f"| NEG Calibration - {full_reverse / 10}\u00B0 - {hex(full_reverse)} - {can_send_msg(full_reverse)}\n"
              f"| NEG Dead Band - {(reverse_dead_band / 40.96 / 2) * (1 - reverse_offset / 40.96 / 100):.2f}% - {reverse_dead_band_lower:.2f}\u00B0\n"
              f"|\n"
              f"-----FAULT-----")
    else:
        order = [zero_angle_offset / 10, (zero_angle_offset - 3600) / 10, (zero_angle_offset + 3600) / 10, full_forward / 10, neutral / 10]
        order.sort()
        print(f"Zero Offset: {zero_angle_offset / 10}\nFull Forward: {full_forward / 10}\n"
              f"Neutral: {neutral / 10}\nFull Reverse: {full_reverse / 10}")
        print(f"{order}")
        if ((neutral_dead_band_lower < zero_angle_offset / 10 < forward_dead_band_upper or
             neutral_dead_band_lower < zero_angle_offset / 10 - 360 < forward_dead_band_upper) or
                (neutral_dead_band_lower < zero_angle_offset / 10 + 360 < forward_dead_band_upper or
                 neutral_dead_band_lower < zero_angle_offset / 10 < forward_dead_band_upper)):
            print("Zero crossing within full range")
        else:
            print("Zero crossing GOOD")
        print(f"-----FAULT-----\n"
              f"|\n"
              f"| POS Dead Band - {(forward_dead_band / 40.96 / 2) * (1 + forward_offset / 40.96):.2f}% - {forward_dead_band_upper:.2f}\u00B0\n"
              f"| POS Calibration - {full_forward / 10}\u00B0 - {hex(full_forward)} - {can_send_msg(full_forward)}\n"
              f"| POS Dead Band - {(forward_dead_band / 40.96 / 2) * (1 - forward_offset / 40.96):.2f}% - {forward_dead_band_lower:.2f}\u00B0\n"
              f"|\n"
              f"| Forward 100% - {forward_dead_band_lower:.2f}\u00B0 - {can_send_msg(int(forward_dead_band_lower))}\n"
              f"| Forward Range - {forward_dead_band_lower - neutral_dead_band_upper:.2f}\u00B0\n"
              f"| Forward 0% - {neutral_dead_band_upper:.2f}\u00B0 - {can_send_msg(int(neutral_dead_band_upper))}\n"
              f"|\n"
              f"| Neutral Dead Band - {(neutral_dead_band / 40.96 / 2) * (1 + neutral_offset / 40.96):.2f}% - {neutral_dead_band_upper:.2f}\u00B0\n"
              f"| Neutral Calibration - {neutral / 10}\u00B0 - {hex(neutral)} - {can_send_msg(neutral)}\n"
              f"| Neutral Dead Band - {(neutral_dead_band / 40.96 / 2) * (1 - neutral_offset / 40.96):.2f}% - {neutral_dead_band_lower:.2f}\u00B0\n"
              f"|\n"
              f"-----FAULT-----")

# Case 1
print('Case 1')
zero_angle_offset = 1500
full_forward = 0x44B
if direction == 1:
    neutral = 0x264  # direction == 1
else:
    neutral = 0x7E  # direction == 0
full_reverse = 0x7E
forward_dead_band = 0xFC
neutral_dead_band = 0xFC
reverse_dead_band = 0xFC
forward_offset = 0
neutral_offset = 0
reverse_offset = 0
result()


# Case 2
print('Case 2')
full_forward = 0x44B
neutral = 0x7E
full_reverse = 0x264
result()

# Case 3
print('Case 3')
full_forward = 0x264
neutral = 0x44B
full_reverse = 0x7E
result()

# Case 4
print('Case 4')
full_forward = 0x44B
if direction == 1:
    neutral = 0x264  # direction == 1
else:
    neutral = 0x7E  # direction == 0
full_reverse = 0x7E
forward_dead_band = 0x7FF
neutral_dead_band = 0x7FF
reverse_dead_band = 0x7FF
result()

# Case 5
print('Case 5')
zero_angle_offset = 100
full_forward = 0x44B
if direction == 1:
    neutral = 0x264  # direction == 1
else:
    neutral = 0x7E  # direction == 0
full_reverse = 0x7E
forward_dead_band = 0xFF
neutral_dead_band = 0xFF
reverse_dead_band = 0xFF
result()

# Case 6
print('Case 6')
zero_angle_offset = 2000
full_forward = 4000
if direction == 1:
    neutral = 3200  # direction == 1
else:
    neutral = 0x7E  # direction == 0
full_reverse = 2400
forward_dead_band = 0xFC
neutral_dead_band = 0xFC
reverse_dead_band = 0xFC
result()

# Case 7
print('Case 7')
zero_angle_offset = 2048
full_forward = 0x44B
if direction == 1:
    neutral = 0x264  # direction == 1
else:
    neutral = 0x7E  # direction == 0
full_reverse = signed(0xFE64)
forward_dead_band = 0xFC
neutral_dead_band = 0xFC
reverse_dead_band = 0xFC
result()

# Case 8
print('Case 8')
zero_angle_offset = 2048
full_forward = 0x44B
if direction == 1:
    neutral = 0x264  # direction == 1
else:
    neutral = 0x7E  # direction == 0
full_reverse = 0x7E
forward_dead_band = 0x6FF
neutral_dead_band = 0x6FF
reverse_dead_band = signed(0xFE64)
result()

# Case 9
print('Case 9')
zero_angle_offset = 2048
full_forward = 0x3E5
if direction == 1:
    neutral = 0x264  # direction == 1
else:
    neutral = 0x7E  # direction == 0
full_reverse = 0x14d
forward_dead_band = 0x1FF
neutral_dead_band = 0xFF
reverse_dead_band = 0xFF
forward_offset = 0
neutral_offset = 0
reverse_offset = 450
result()

# Case 10
print('Case 10')
zero_angle_offset = 3600
full_forward = 3600 - 204
if direction == 1:
    neutral = 1800  # direction == 1
else:
    neutral = 0x7E  # direction == 0
full_reverse = 205
forward_dead_band = 410
neutral_dead_band = 410
reverse_dead_band = 410
forward_offset = 0
neutral_offset = 0
reverse_offset = 0
result()

# Case 11
print('Case 11')
full_forward = 0x44B
neutral = 0x264
full_reverse = 0x264
result()

