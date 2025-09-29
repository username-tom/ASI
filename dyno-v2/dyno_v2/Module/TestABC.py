from abc import ABC, abstractmethod
from time import sleep
from threading import Thread
from dyno_v2.Module.exceptions import *
from dyno_v2.Module.dyno_parameters import TEST_KW
from datetime import datetime
import pandas as pd
import logging


class TestABC(ABC):

    def __init__(self, dyno, *args, **kwargs): # use_barcode=False, motor_type=None, barcode=None, sn=None):
        """TestABC

        Keyword arguments:
            dyno : ASIDynoModule, required
            use_barcode : bool, optional
            note : str, optional
            barcode1 : dict, required if use_barcode is True
            sn1 : str, optional
            note : str, optional
            barcode2 : dict, optional
            sn2 : str, optional
        """
        self.dyno = dyno

        self.args = {}
        for key, val in zip(TEST_KW, args):
            self.args[key] = val
        for kw in kwargs:
            self.args[kw] = kwargs[kw]

        self.testing = True
        self.watchdog_enabled = False
        self.watchdog = None
        self.watchdog_interval = 0.5
        self.startTime = None

    @abstractmethod
    def parse_test_args(self):
        ...

    def rundown_args(self):
        self.args['settleTime'] = float(self.dyno.config["pt_settle"])
        self.args['target_efficiency'] = float(self.dyno.config["pt_effi"])
        self.args['target_efficiency_window'] = float(self.dyno.config["pt_effi_win"])
        self.args['MinTorque'] = float(self.dyno.config["pt_mintorque"])
        self.args['MaxTorque'] = float(self.dyno.config["pt_maxtorque"])
        self.args['TorqueStep'] = float(self.dyno.config["pt_step"])
        self.args['speed'] = self.dyno.config["pt_speed"]
        self.args['motoring'] = int(self.dyno.config["pt_motoring"])
        self.args['torque_target'] = 0
        self.dyno.test_outputs['max_efficiency'] = 0
        self.dyno.test_outputs['max_torque'] = 0
        # self.zoom = zoom
        if self.args['zoom']:
            self.args['zoom_lo'] = float(self.args['zoom_lo']) if self.args['zoom_lo'] != '' else 0
            self.args['zoom_hi'] = float(self.args['zoom_hi']) if self.args['zoom_hi'] != '' else 0
        self.args['motor_type'] = self.args['note']

    def ctm_args(self):
        self.args['peakCurrent'] = float(self.dyno.config["ctm_current"])
        self.args['opSpeed'] = float(self.dyno.config["ctm_rpm"])
        self.args['coarse_speed'] = bool(self.dyno.config["ctm_coarse"])
        self.dyno.update(float(self.dyno.config["pid_sstime"]),
                         float(self.dyno.config["pid_sstol"]),
                         float(self.dyno.config["basic_testtime"]),
                         float(self.dyno.config["pid_tpid"]),
                         float(self.dyno.config["pid_ss"]))
        self.dyno.test_outputs['foldback_time'] = None
        self.dyno.test_outputs['ninety'] = None
        self.dyno.test_outputs['start_temp'] = -99

    def validation_args(self):
        self.dyno.test_outputs['RsLs'] = []
        self.dyno.test_outputs['avgRsLs'] = []
        self.args['windowRsLs'] = [self.dyno.config["pv_rsWin"],
                                   self.dyno.config["pv_lsWin"]]
        self.dyno.test_outputs['double_test'] = False
        self.args['offsetRef'] = self.dyno.config["pv_offsetwin"]
        self.dyno.test_outputs['hallRef'] = []
        self.dyno.test_outputs['hallTableRef'] = []
        self.dyno.test_outputs['offset'] = 0.
        self.dyno.test_outputs['ratedRPM'] = 0
        self.args['windowRPM'] = self.dyno.config["pv_rpmwin"]
        self.args['targetEfficiency'] = self.dyno.config["pv_mineffi"]
        self.args['targetTorque'] = self.dyno.config["pv_mint"]
        self.dyno.test_outputs['torqueConstant'] = 0.
        self.args['torqueConstantRef'] = self.dyno.config["pv_tqcref"]
        self.args['windowTorqueConstant'] = self.dyno.config["pv_tqcwin"]

    def cyclic_args(self):
        try:
            cycles = int(self.dyno.config['jw_cyclic_cycle'])
        except TypeError:
            print('Bad value for total total_cycles')
            return
        else:
            self.args['total_cycles'] = cycles

        try:
            steps = self.dyno.config['jw_cyclic_step']
        except (AttributeError, TypeError) as e:
            logging.error(f"{e}\nWhen loading cyclic test hold times (jw_cyclic_step)")
        else:
            if steps.startswith('[') and steps.endswith(']'):
                self.args['steps'] = steps.strip('[]').split(', ')
            elif float(steps):
                self.args['steps'] = [float(steps)]
            else:
                logging.error("Bad total_steps format")
                return

        self.args['total_steps'] = len(self.args['steps'])

        # watchdog = self.dyno.config['watchdog']
        # if pd.isna(watchdog):
        #     self.watchdog = None
        # else:
        #     if bool(watchdog):
        #         self.watchdog = Thread(target=self._watchdog_thread)
        #     else:
        #         self.watchdog = None

        ramp = self.dyno.config['jw_cyclic_ramp']
        self.args['ramps'] = self.parse_param(ramp)

        speeds_a = self.dyno.config['jw_cyclic_speed_a']
        self.args['a'] = self.parse_param(speeds_a)
        speeds_b = self.dyno.config['jw_cyclic_speed_b']
        self.args['b'] = self.parse_param(speeds_b)
        motoring_a = self.dyno.config['jw_cyclic_motoring_a']
        self.args['motoring_a'] = self.parse_param(motoring_a)
        motoring_b = self.dyno.config['jw_cyclic_motoring_b']
        self.args['motoring_b'] = self.parse_param(motoring_b)
        regen_a = self.dyno.config['jw_cyclic_regen_a']
        self.args['regen_a'] = self.parse_param(regen_a)
        regen_b = self.dyno.config['jw_cyclic_regen_b']
        self.args['regen_b'] = self.parse_param(regen_b)
        # a_b_lo = self.dyno.config['jw_cyclic_a_b_low']
        # a_b_lo = self.parse_param(a_b_lo)
        # a_b_hi = self.dyno.config['jw_cyclic_a_b_hi']
        # a_b_hi = self.parse_param(a_b_hi)
        # b_a_lo = self.dyno.config['jw_cyclic_b_a_low']
        # b_a_lo = self.parse_param(b_a_lo)
        # b_a_hi = self.dyno.config['jw_cyclic_b_a_hi']
        # b_a_hi = self.parse_param(b_a_hi)

        # set up PID if requested
        kp = self.dyno.config['jw_cyclic_kp']
        ki = self.dyno.config['jw_cyclic_ki']
        limits = self.dyno.config['jw_cyclic_bounds']
        if pd.isna(kp) or pd.isna(ki):
            self.args['kp'] = False
            self.args['ki'] = False
        else:
            self.args['kp'] = self.parse_param(kp)
            self.args['ki'] = self.parse_param(ki)
        try:
            self.args['limits'] = tuple(map(int, limits.split(',')))
        except AttributeError:
            if isinstance(ki, list) and isinstance(kp, list):
                raise TestError("Bad PID limits")
            else:
                self.args['limits'] = (0, 0)

        # self.current_cycle = 0
        # self.current_step = 0
        # self.a_fdbk_coeff = 1
        # self.b_fdbk_coeff = 1
        # self.cooldown_type = None
        # self.cooldown = 0
        # self.driver = ''
        if pd.isna(self.dyno.config['cycle_cd_driver']):
            self.args['cd_on_driver'] = False
        else:
            self.args['cd_on_driver'] = bool(self.dyno.config['cycle_cd_driver'])
        if pd.isna(self.dyno.config['jw_cyclic_foldback']):
            self.args['foldback_overwrite'] = False
        else:
            self.args['foldback_overwrite'] = bool(self.dyno.config['jw_cyclic_foldback'])
        if pd.isna(self.dyno.config['jw_cyclic_foldback_driver']):
            self.args['foldback_driver'] = False
        else:
            self.args['foldback_driver'] = bool(self.dyno.config['jw_cyclic_foldback_driver'])
        if pd.isna(self.dyno.config['jw_cyclic_cd_in_step']):
            self.args['cd_in_step'] = False
        else:
            self.args['cd_in_step'] = bool(self.dyno.config['jw_cyclic_cd_in_step'])

    def open_loop_args(self):
        self.args['rated_motor_current'] = self.dyno.devices[1].read('Rated motor current')
        self.args['total_cycles'] = int(self.dyno.config["line_count"])
        self.args['total_steps'] = 1
        self.args['target'] = float(self.dyno.config["line_modulation"])
        self.args['frequency'] = int(self.dyno.config["line_freq"])
        self.args['mode'] = int(self.dyno.config["line_mode"])
        if self.args['mode'] < 2:
            logging.error("Bad test mode")
            raise TestInterrupt
        self.args['steps'] = [0]
        self.args['ramps'] = int(self.dyno.config["line_ramp"])
        self.args['ultimate_temperature'] = int(self.dyno.config["line_ult"])
        self.args['upper_limit'] = int(self.dyno.config["line_max"])
        self.args['lower_limit'] = int(self.dyno.config["cycle_dut_temp"])
        self.args['hold_condition_driver'] = 1,
        self.args['hold_condition_param'] = 'controller temperature',
        self.args['raise_error'] = True

        self.dyno.devices[1].set_access_level(2)

        # Check and update Heatsink over temperature trip threshold
        self.dyno.devices[1].add_run_parameter('Heatsink over temperature trip threshold')
        onboard_ult_temp = self.dyno.devices[1].read('Heatsink over temperature trip threshold')
        if self.args['ultimate_temperature'] > onboard_ult_temp:
            self.dyno.devices[1].write('Heatsink over temperature trip threshold',
                                       self.args['ultimate_temperature'])

    def efficiency_map_args(self):
        self.args['settleTime'] = float(self.dyno.config["pt_settle"])
        self.args['ratio'] = float(self.dyno.config['ratio'])
        # self.rated_motor_current = self.dyno.DUT.read('Rated motor current')
        # self.max_efficiency = 0
        # self.max_torque = 0
        self.args['foldback_overwrite'] = False
        self.args['foldback_driver'] = False
        self.args['cd_in_step'] = True
        self.args['cd_on_driver'] = False
        speeds = self.dyno.config["effm_rpm"]
        self.args['speeds'] = self.parse_param(speeds)
        self.args['total_cycles'] = 1
        self.args['steps'] = [0] * len(self.args['speeds'])
        self.args['total_steps'] = len(self.args['steps'])
        # LoadCellLimit = self.dyno.config["max_torque"]
        # LoadCellLimit = self.parse_param(LoadCellLimit)
        MinTorque = self.dyno.config["pt_mintorque"]
        self.args['MinTorque'] = self.parse_param(MinTorque)
        MaxTorque = self.dyno.config["pt_maxtorque"]
        self.args['MaxTorque'] = self.parse_param(MaxTorque)
        TorqueStep = self.dyno.config["pt_step"]
        self.args['TorqueStep'] = self.parse_param(TorqueStep)
        motoring = self.dyno.config["pt_motoring"]
        self.args['motoring'] = self.parse_param(motoring)

        if 'effi_target' not in self.args.keys():
            self.args['effi_target'] = True

    def efficiency_table_abb_args(self):
        self.args['settleTime'] = float(self.dyno.config["pt_settle"])
        self.args['ratio'] = float(self.dyno.config['ratio'])
        self.args['foldback_overwrite'] = False
        self.args['foldback_driver'] = False
        self.args['cd_in_step'] = True
        self.args['cd_on_driver'] = False
        speeds = self.dyno.config["efft_rpm"]
        self.args['speeds'] = self.parse_param(speeds)
        apks = self.dyno.config["efft_apk"]
        self.args['apks'] = self.parse_param(apks)
        self.args['device'] = self.dyno.config['efft_device']
        self.args['temp_window'] = [float(self.dyno.config['efft_temp_win'].split(',')[0]),
                                    float(self.dyno.config['efft_temp_win'].split(',')[1])]
        self.args['ss_samples'] = int(self.dyno.config['efft_ss_samples'])
        self.args['ss_rpm'] = float(self.dyno.config['efft_ss_rpm'])
        self.args['ss_current'] = float(self.dyno.config['efft_ss_current'])
        self.args['timeout'] = int(self.dyno.config['efft_timeout'])
        self.args['total_cycles'] = len(self.args['speeds'])
        self.args['steps'] = [self.args['timeout']] * len(self.args['apks'])
        self.args['ramps'] = [0] * len(self.args['apks'])
        self.args['total_steps'] = len(self.args['steps'])
        reset = self.dyno.config['efft_reset']
        try:
            if 't' in reset.lower():
                self.args['reset'] = True
            else:
                self.args['reset'] = False
        except:
            self.args['reset'] = False
        ramp = self.dyno.config['efft_ramp']
        try:
            if 't' in ramp.lower():
                self.args['ramp_torque'] = True
            else:
                self.args['ramp_torque'] = False
        except:
            self.args['ramp_torque'] = False
        self.args['rated_motor_current'] = self.dyno.devices[1].read('Rated motor current')
        self.dyno.test_outputs['skip_ss'] = False
        self.dyno.test_outputs['extra'] = 'SS points'
        self.dyno.test_outputs['samples'] = 0
        self.dyno.test_outputs['current_target'] = 0

    def temperature_map_args(self):
        self.args['ratio'] = float(self.dyno.config['ratio'])
        self.args['foldback_overwrite'] = False
        self.args['foldback_driver'] = False
        self.args['cd_in_step'] = True
        self.args['cd_on_driver'] = False
        speeds = self.dyno.config["tempm_rpm"]
        self.args['speeds'] = self.parse_grid(speeds)
        torques = self.dyno.config["tempm_t"]
        self.args['torques'] = self.parse_grid(torques)
        self.args['total_cycles'] = len(self.args['speeds'])
        self.args['steps'] = [0] * len(self.args['torques'])
        self.args['total_steps'] = len(self.args['torques'])
        self.args['timeout'] = int(self.dyno.config["tempm_timeout"])
        self.args['speed_window'] = float(self.dyno.config["tempm_speed_window"])
        self.args['torque_window'] = float(self.dyno.config["tempm_torque_window"])
        self.args['max_temperature'] = int(self.dyno.config["tempm_max_temperature"])
        self.args['device'] = self.dyno.config["tempm_device"]
        self.args['brake'] = int(self.dyno.config["tempm_brake"])
        self.args['alt_lower'] = float(self.dyno.config["tempm_alt_lower"])
        self.args['alt_max'] = float(self.dyno.config["tempm_alt_max"])
        try:
            self.args['alt_kp'] = float(self.dyno.config["tempm_alt_kp"])
        except TypeError:
            self.args['alt_kp'] = None
        try:
            self.args['alt_ki'] = float(self.dyno.config["tempm_alt_ki"])
        except TypeError:
            self.args['alt_ki'] = None
        self.args['settleTime'] = float(self.dyno.config["pt_settle"])
        MinTorque = self.dyno.config["pt_mintorque"]
        self.args['minTorque'] = float(MinTorque)
        MaxTorque = self.dyno.config["pt_maxtorque"]
        self.args['maxTorque'] = float(MaxTorque)
        TorqueStep = self.dyno.config["pt_step"]
        self.args['torqueStep'] = float(TorqueStep)
        motoring = self.dyno.config["pt_motoring"]
        self.args['motoring'] = float(motoring)

    def maple_tak_production_args(self):
        self.args['ratio'] = float(self.dyno.config['ratio'])
        self.args['brake'] = self.dyno.config['mtakpt_brake']
        if self.args['brake'] == 'ABB':
            print("ABB as brake, skipping reverse loaded step")
        elif self.args['brake'] == 'BAC':
            print("BAC2BAC, runs reverse loaded step")
        self.args['ramp_step'] = float(self.dyno.config['mtakpt_step'])
        self.args['no_load_duration'] = float(self.dyno.config['mtakpt_no_load_dur'])
        self.args['no_load_speed_command'] = float(self.dyno.config['mtakpt_no_load_speed'])
        self.args['max_torque'] = float(self.dyno.config['mtakpt_max'])
        self.args['typical_torque'] = float(self.dyno.config['mtakpt_typical'])
        self.args['max_duration'] = float(self.dyno.config['mtakpt_max_dur'])
        self.args['typical_torque_duration'] = float(self.dyno.config['mtakpt_typical_dur'])
        self.dyno.test_outputs['test_result'] = False
        self.dyno.test_outputs['init_controller_temp'] = 0
        self.dyno.test_outputs['init_motor_temp'] = 0

    def debug_args(self):
        self.args['total_cycles'] = 10
        self.dyno.test_outputs['current_cycle'] = 0

    def interrupt(self):
        self.testing = False
        self.dyno.testing = False
        if self.watchdog:
            self.stop_watchdog()
        self.dyno.int_event.set()
        raise TestInterrupt

    @abstractmethod
    def logging_setup(self):
        ...

    @abstractmethod
    def log_result(self, *args, **kwargs):
        ...

    @abstractmethod
    def test(self, **kwargs):
        ...

    @abstractmethod
    def post_test(self, **kwargs):
        ...

    def default_test_procedure(self):
        try:
            self.parse_test_args()
            self.startTime = datetime.now()
            self.logging_setup()
            self.dyno.backup_parameters('DUT', 'BRK')
            self.test()
        except (KeyboardInterrupt, TestInterrupt):
            print(f"\n\nInterrupted")
        except TestError as e:
            print(e)
        finally:
            self.dyno.stop_test()
            self.dyno.stop_logging()
            delta = (datetime.now() - self.startTime).total_seconds() / 60
            print(f"Run duration: {delta:.2f} minutes")
            self.log_result()
            self.post_test()
            self.testing = False
            self.dyno.int_event.clear()

    run = default_test_procedure
    wait = sleep

    def _watchdog_thread(self):
        if self.dyno.devices[1]:
            self.dyno.devices[1].write(32, 4000 * (self.watchdog_interval + 0.05))  # Set comm loss threshold to 4X(+0.05) watchdog interval
            self.dyno.devices[1].write(49, 2000 * (self.watchdog_interval + 0.05))  # Set average comm loss threshold to +0.05 watchdog interval
        if self.dyno.devices[2]:
            self.dyno.devices[2].write(32, 4000 * (self.watchdog_interval + 0.05))  # Set comm loss threshold to 4X(+0.05) watchdog interval
            self.dyno.devices[2].write(49, 2000 * self.watchdog_interval + 0.05)  # Set average comm loss threshold to +0.05 watchdog interval
        while self.watchdog_enabled:
            if self.dyno.devices[1]:
                self.dyno.devices[1].write("Remote state command", 258)  # Toggle high bit off
            if self.dyno.devices[2]:
                self.dyno.devices[2].write("Remote state command", 258)  # Toggle high bit off
            sleep(self.watchdog_interval / 2)
            if self.dyno.devices[1]:
                self.dyno.devices[1].write("Remote state command", 514)  # Toggle high bit on
            if self.dyno.devices[2]:
                self.dyno.devices[2].write("Remote state command", 514)  # Toggle high bit on
            sleep(self.watchdog_interval / 2)
        if self.dyno.devices[1]:
            self.dyno.devices[1].write(32, 0)  # Reset comm loss threshold to 0
            self.dyno.devices[1].write(49, 0)  # Reset average comm loss threshold to 0
            self.dyno.devices[1].write("Remote state command", 0)
        if self.dyno.devices[2]:
            self.dyno.devices[2].write(32, 0)  # Reset comm loss threshold to 0
            self.dyno.devices[2].write(49, 0)  # Reset average comm loss threshold to 0
            self.dyno.devices[2].write("Remote state command", 0)

    def stop_watchdog(self):
        self.watchdog_enabled = False
        self.watchdog = Thread(target=self._watchdog_thread)

    def log_barcode(self):
        if self.args['use_barcode']:
            result_txt = self.dyno.logdir / "cyclic result.txt"
            with open(result_txt, "a") as txt:
                txt.write("DUT A Barcode:")
                txt.write(self.dyno.devices[1].barcode)
                txt.write("\nDUT B Barcode:")
                txt.write(self.dyno.devices[2].barcode)

    def debug_logging_setup(self):
        self.dyno.start_logging(1, 'Debug')

    def rundown_logging_setup(self):
        if self.args['use_barcode']:
            output = self.args['barcode1']['serial_num']
            parameter = self.args['barcode1']['parameter']
            if str(parameter).startswith('92-000308') or '22' in self.args['motor_type']:
                self.args['torque_target'] = 15
            elif str(parameter).startswith('92-000311') or '18' in self.args['motor_type']:
                self.args['torque_target'] = 12
        else:
            try:
                sn, idx = self.args['sn1'].split("-")
                output = f"{int(sn)}-{int(idx):05d}"
            except (AttributeError, TypeError, ValueError):
                output = f"0000-00000"
            if '22' in self.args['motor_type'] or \
                    'scythe' in self.args['motor_type'] or \
                    'maple' in self.args['motor_type']:
                self.args['torque_target'] = 15
            elif '18' in self.args['motor_type']:
                self.args['torque_target'] = 12

        self.dyno.start_logging(1, run_down=f"{output} ({self.args['motor_type']})")

    def single_logging_setup(self):
        if self.args['use_barcode']:
            output = self.args['barcode1']['serial_num']
        else:
            try:
                sn, idx = self.args['sn1'].split("-")
                output = f"{int(sn)}-{int(idx):05d}"
            except (AttributeError, TypeError, ValueError):
                output = f"0000-00000"

        self.dyno.start_logging(1, run_down=f"{output} ({self.args['note']})")

    def double_logging_setup(self):
        if self.args['use_barcode']:
            output = self.args['barcode1']['serial_num']
            output += ' '
            output += self.args['barcode2']['serial_num']
        else:
            try:
                sn, idx = self.args['sn1'].split("-")
                output = f"{int(sn)}-{int(idx):05d}"
                output += ' '
                sn, idx = self.args['sn2'].split('-')
                output += f"{int(sn)}-{int(idx):05d}"
            except (AttributeError, TypeError, ValueError):
                output = f"0000-00000 0000-00000"

        self.testing = self.dyno.start_logging(1, run_down=f"{output} ({self.args['note']})")

    def parse_param(self, var):
        if 'steps' in self.args.keys():
            ans = [0] * len(self.args['steps'])
        if isinstance(var, str):
            if var.startswith('[') and var.endswith(']'):
                ans = var.strip('[]').split(', ')
        elif pd.isna(var):
            ans = [0] * len(self.args['steps'])
        else:
            try:
                float(var)
            except (ValueError, TypeError):
                pass
            else:
                ans = [float(var)] * len(self.args['steps'])
        if len(ans) == 1:
            if pd.isna(ans[0]):
                ans = [0] * len(self.args['steps'])
        return ans

    def parse_grid(self, var):
        min_var = float(var.split(',')[0])
        max_var = float(var.split(',')[1])
        step_var = float(var.split(',')[2])

        return_list = []
        steps = int((max_var - min_var) / step_var)
        for i in range(steps):
            return_list.append(min_var + step_var * i)
        return_list.append(max_var)

        return return_list
