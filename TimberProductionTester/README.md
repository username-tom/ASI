# Timber Production Tester

*Version 1.0*

*Author T.W.*

---

## Release Note
**Timber Production Tester** program is written to automate Timber Motor Production Validation. 
This program only supports TTL communications with 2 ASI Controllers (DUT and BRK). 
It does not support GCMs, VCMs, throttles or other hardware. 

Test results are logged in `Timber Production Summary [Date].csv`, which can be found at the indicated destination in `config.ini`.
The result logs are separated by date. 
If there is permission error when writing to the file, the result will be saved to local address `C:/Timber Production Result`

The program does not save any parameters to flash. 
Power cycling the DUT will bring the controller to its original state before the test.

The program has a configureale 5-minute limit on the test duration. 
Program will notify timeout if the test runs longer than the limit and will stop the test automatically. 

Currently, the program supports firmware 6.014 - 6.026.
But new firmware dictionaries can be added to Dictionary folder for future cases. 

COM port can be configured in the program. 
However, to change other test parameters (i.e. test speed, pass criteria, etc.), 
it will require restarting the program after changing the values in `config.ini`.

---

## Settings
Test settings can be changed in the `config.ini` file. 
Change the values, save and restart the tester software. 

Settings:
- default: Default settings
	1. dut_com_port: Default DUT TTL port
	2. brk_com_port: Default BRK TTL port
	3. save_destination: File directory to save test results
	4. geometry: Last opened location
	5. font_size: Program font size
	6. timeout: Test timeout limit in minutes

- pre: Pre-test Motor Discovery passing windows
	1. rs: Autotune Rs value passing window
	2. ls: Autotune Ls value passing window
	3. rpm: Autotune Rated RPM passing window
	4. offset: Autotune Hall Offset passing window

- post: Post-test Motor Discovery passing windows
	1. rs: Autotune Rs value passing window
	2. ls: Autotune Ls value passing window
	3. rpm: Autotune Rated RPM passing window
	4. offset: Autotune Hall Offset passing window

- unloaded: Unloaded Run settings and passing windows
	1. speed: Motor speed command in % of rated motor speed
	2. duration: Unloaded Run duration
	3. ia: Ia RMS current passing window
	4. ic: Ic RMS current passing window
	5. motor_current: Motor current passing window

- loaded: Loaded Rundown test settings and passing windows
	1. speed: Motor speed command in % of rated motor speed
	2. min_torque: Brake load starting point in % of torque command
	3. max_torque: Brake load ending point in % of torque command
	4. torque_step: Brake load increments in % of torque command
	5. settle_time: Brake load increment duration in seconds
	6. target_torque: Loaded Rundown test passing torque in % of torque command 
	7. target_temperature: Loaded Rundown test passing motor temperature at the end

---

## Test Procedure
See GUI output section
1. Connect to controllers (DUT & BRK)
2. Motor discovery mode 1 & 2
3. Unloaded run
4. Rundown
5. Motor discovery mode 1 & 2
6. Disconnect

---

## Result

PASSED
: DUT has passed Line Reactor Test

FAILED
: DUT has failed Line Reactor Test

TESTING
: Current DUT is under testing.

INTERRUPTED
: Test was interrupted. 
The interruption was also logged. 

---
## Status

DISCONNECTED
: Program is not connected to any device right now. 
It is ready to start a new test if the DUT is properly connected and powered.

CONNECTING
: Program is attempting to connect to DUT, please wait for response.

DISCONNECTING
: Program is at step 7 of the test procedure.
It is attempting to disconnect the DUT. 
"Disconnected" will be printed when program finishes the disconnection. 

CONNECTED
: Program is connected to the DUT. 
Program is at the end of step 1 of the test procedure.
Status will change to ***TESTING*** very quickly.

TESTING
: Program is running the test. 
This can be step 2-6 of the test procedure

---

## Results Logged

At the end of a complete Line Reactor Test, the following data are logged:
1. Result Time
2. Serial Number
3. Barcode
4. Test Result
5. Initial Motor Temperature
6. Pre-test Faults
7. Pre-test Rs
8. Pre-test Ls
9. Pre-test Hall Sectors
10. Pre-test Rated RPM
11. Pre-test Hall Offset
12. Unloaded Ia RMS Avg
13. Unloaded Ia RMS Max
14. Unloaded Ia RMS Min
15. Unloaded Ic RMS Avg
16. Unloaded Ic RMS Max
17. Unloaded Ic RMS Min
18. Unloaded Motor Current
19. Unloaded Result
20. Rundown Max Torque
21. Rundown Max Temperature
22. Rundown Result
23. Post-test Faults
24. Post-test Rs
25. Post-test Ls
26. Post-test Hall Sectors
27. Post-test Rated RPM
28. Post-test Hall Offset
29. Note

---

## Result

The pass and fail of a Timber Production Test is determined by: 
1. Pre-test motor discovery 
2. Unloaded test
3. Rundown
4. Post-test motor discovery

And the results are logged at the end of the test procedure. 
If a DUT has failed before then, the program will still carry on with the rest of the test.
