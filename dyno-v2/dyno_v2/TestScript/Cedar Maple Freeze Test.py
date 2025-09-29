from ASIDynoModule import ASIDynoModule
from asi_controller import asi_controller
from time import sleep
from datetime import datetime
import sys

'''
# Use these COM Ports when running this test script on the BAC2BACTester,
# I suspect that one of the motors brakes better than the other,
# otherwise the test setup will shake a lot when moving, KS, 1/25/2022
#
brake_COM        = "COM6"
driver_COM       = "COM8"

#defaults for testing on the BAC2BACTester
motoring_current = 100
speed            = 30
torque           = 10
'''

# These COMs are for the freezer unit, KS, 1/25/2022
brake_COM        = "COM13"
driver_COM       = "COM14"

motoring_current = 100
speed            = 1000 # rpm
torque           = 30



def any_faults(brake, driver):
    controller1_faults = brake.check_faults()
    controller2_faults = driver.check_faults()

    if(controller1_faults
             or
       controller2_faults):
        print("brake faults: ", controller1_faults)
        print("driver faults: ", controller2_faults)
        return True
    else:
        return False


def stop_test(test_setup):
    test_setup.DUT.stop_remote_motor()
    test_setup.BRK.stop()
    test_setup.stop_logging()



# Driving controller WILL BE setup using the ASIDynoModule
# We will monitor data that's on the driving controller
# Might tell it to monitor the braking controller instead if there are I/O issues :), 
# KS, 1/11/2022

# only give this a COM for a controller

test_setup = ASIDynoModule(driver_COM, None, brake_COM)

brake  = test_setup.BRK
brake.set_torque(0.0)
driver = test_setup.DUT

test_setup.start_logging(1)

m_fldbk = driver.read("Motor foldback starting temperature")
c_fldbk = driver.read("Controller foldback starting temperature")


# controller temperature index = c_temp_i
# motor temperature index = m_temp_i
m_temp_i = -1
c_temp_i = -1

for i, param in enumerate(test_setup.DUT.log_params):
    if(param.Name == "motor temperature"):
        m_temp_i = i
    elif(param.Name == "controller temperature"):
        c_temp_i = i
    elif(param.Name == "motor rpm"):
        motor_rpm_i = i
    elif(param.Name == "warnings"):
        warnings_i = i
    elif(param.Name == "faults"):
        faults_i = i

# commented out because both controllers use the same parameter file, 
# un-comment if each controller of the two has a unique parameter file!, KS, 1/25/2022
"""for i, param in enumerate(test_setup.BRK.log_params):
    if(param.Name == "motor temperature"):
        m_temp_i_2 = i
    elif(param.Name == "controller temperature"):
        c_temp_i_2 = i"""

if(m_temp_i == -1):
    raise Exception("'motor temperature' not found, forgot to include motor temperature in log parameter file...")

if(c_temp_i == -1):
    raise Exception("'controller temperature' not found, forgot to include controller temperature in log parameter file...")




if(any_faults(brake, driver)):
    brake.clear_faults()
    driver.clear_faults()


# so that it starts braking immediately
# comment out during actual test runs!
try:
    while(1):
        print("START BRAKING...")
        brake.set_torque(0.0)
        print(datetime.now().strftime('%Y-%m-%d-%H-%M:%S'))

        # Have it gradually build speed to avoid an Instantaneous Phase Over Current fault.
        # As well, this means that we'll hear the motor briefly, KS, 2/3/2022
        driver.remote_speed_mode(speed, 0.2 * motoring_current)
        sleep(1)
        driver.remote_speed_mode(speed, 0.4 * motoring_current)
        sleep(1)
        driver.remote_speed_mode(speed, 0.6 * motoring_current)
        sleep(1)
        driver.remote_speed_mode(speed, 0.8 * motoring_current)
        sleep(1)
        driver.remote_speed_mode(speed, motoring_current)
        sleep(1)
        
        sleep(10)
        brake.set_torque(0.2 * torque)
        sleep(1)
        brake.set_torque(0.4 * torque)
        sleep(1)
        brake.set_torque(0.6 * torque)
        sleep(1)
        brake.set_torque(0.8 * torque)
        sleep(1)
        brake.set_torque(torque)
        sleep(1)
        brake.start()

        

        error = any_faults(brake, driver)

        if(error):
            print(error)
            #input("received this ^^")
            brake.clear_faults()
            driver.clear_faults()

        # Should keep heating until controller AND motor are both in foldback or while speed is more than half of the speed we requested, KS, 2/3/2022
        # 
        # we use the value read directly from the controller, to decrease the amount of IO needed
        # tried to make this better, but it would cause the test polling thread(s) to crash due to "ValueErrors" in ASIController, KS, 2/3/2022
        while(driver.in_foldback() == False):
            print("warnings: ", bin(int(driver.log_params[warnings_i].Value)).zfill(16))
            print("faults: ", bin(int(driver.log_params[faults_i].Value)).zfill(16))
            print("this is my motor temperature: ", driver.log_params[m_temp_i].Value, " this is my controller temperature: ", driver.log_params[c_temp_i].Value, " this is my motor rpm: ", driver.log_params[motor_rpm_i].Value)


        print("STOP BRAKING...")
        brake.stop()
        driver.stop_remote_motor()

        sleep(10)

        error = any_faults(brake, driver)

        if(error):
            print(error)
            #input("received this ^^")
            brake.clear_faults()
            driver.clear_faults()

        # Wait 90 minutes after controller AND motor foldback have started, KS, 2/3/2022
        print("Waiting for 90 minutes....")
        
        for i in range(60 * 90):
            print("this is my motor temperature: ", driver.log_params[m_temp_i].Value, " this is my controller temperature: ", driver.log_params[c_temp_i].Value, " this is my motor rpm: ", driver.log_params[motor_rpm_i].Value)
            print("waiting, right now it's: minute: ", i / 60, " and second: ", i)
            sleep(1)


except KeyboardInterrupt as k_e:
    print("stop logging data, close")
    brake.write("Remote maximum braking current", 0.0)
    stop_test(test_setup)
finally:
    brake.write("Remote maximum braking current", 0.0)
    stop_test(test_setup)