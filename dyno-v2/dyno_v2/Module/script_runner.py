from dyno_v2.Module.ASIDynoModule import *
# print(sys.path)

import importlib
classes = {}
for test in TEST_SCRIPTS:
    try:
        module = importlib.import_module(TEST_MODULES[test])
        classes[test] = getattr(module, TEST_CLASSES[test])
    except KeyError:
        pass

# from dyno_v2.TestScript.controller_thermal_max import ControllerThermalMax
# from dyno_v2.TestScript.rundown_test import RundownTest
# from dyno_v2.TestScript.LineReactorTest import LineReactorTest
# from dyno_v2.TestScript.for_debug import ForDebug
# from dyno_v2.TestScript.production_validation import ProductionValidation
# from dyno_v2.TestScript.debug_dyno_start_stop import DebugStartStop
# from dyno_v2.TestScript.cyclic_test_jason import CyclicTest
# from dyno_v2.TestScript.efficiency_map import EfficiencyMapTest
# from dyno_v2.TestScript.cyclic_open_loop import CyclicOpenLoopTest


class ScriptRunner:

    def __init__(
            self,
            preset: str,
            dyno: ASIDynoModule,
            # barcode: bool,
            # barcode1: str,
            # barcode2: str,
            # note: str,
            # sn1: str,
            # sn2: str,
            *args,
            **kwargs
    ):
        """
        ScriptRunner

        Parameters:
            preset : str, required | config name
            dyno: ASIDynoModule, required
            args: list, optional [
                use_barcode : bool, optional. Use barcode or serial number. Default value: False |
                barcode1 : dict, required if barcode is True |
                sn1 : str, required if barcode is False. If missing, default value: 0000-00000 |
                note : str, optional |
                barcode2 : dict, required if test runs 2 ASIControllers and barcode is True |
                sn2 : str, required if test runs 2 ASIControllers and barcode is False]
            kwargs : dict, optional {
                zoom : bool, optional |
                zoom_lo : int, required if zoom is True |
                zoom_hi : int, required if zoom is True |
                enable_email : bool, optional |
                enable_int_email : bool, optional}
        """
        configs = config_reader()
        try:
            configs.loc[preset]
        except KeyError:
            print('Test not in dyno_config.csv. Please try again')
            raise TestError

        self.dyno = dyno
        print(self.dyno)
        # self.dyno.testing = True
        if self.dyno.devices[1] is None and \
            self.dyno.devices[2] is None and \
            self.dyno.devices[PA] is None:
            raise TestError("No devices connected")

        if not hasattr(self, 'dyno'):
            print('No DynoModule found in arguments')
            raise TestError
        
        self.test = configs.loc[preset]['test']
        if self.test in ['Life Test/Cyclic Test', 'Efficiency Map']:
            self.cyclic = True
        else:
            self.cyclic = False
        self.preset = preset

        self.test_parameters = {'Start Time': datetime.now(),
                                'Duration': '',
                                'Est. Test Time': '',
                                'Steps': '0/0',
                                'Cycles': '0/0'}

        for pair in zip(TEST_KW, args):
            self.test_parameters[pair[0]] = pair[1]

        self.status_thread = None

        for arg in kwargs:
            self.test_parameters[arg] = kwargs[arg]

        # if no values provided for args i.e. barcode or serial number
        if 'use_barcode' not in self.test_parameters.keys():
            self.test_parameters['use_barcode'] = False
            self.test_parameters['sn1'] = '0000-00000'
            self.test_parameters['note'] = ''

        # check barcode if using barcode
        if self.test_parameters['use_barcode']:
            if 'barcode1' not in self.test_parameters.keys() or \
                    not self.test_parameters['barcode1'] or \
                    not isinstance(self.test_parameters['barcode1'], dict):
                logging.warning("Bad barcode provided while using barcode."
                                "Using default serial number instead")
                self.test_parameters['use_barcode'] = False
                if 'sn1' not in self.test_parameters.keys():
                    self.test_parameters['sn1'] = '0000-00000'
                    self.test_parameters['sn2'] = '0000-00000'
                    self.test_parameters['note'] = ''

        # rundown zoom-in mode parameters check
        if 'zoom' not in self.test_parameters.keys():
            self.test_parameters['zoom'] = False
        else:
            if self.test_parameters['zoom']:
                if 'zoom_lo' not in self.test_parameters.keys():
                    raise TestError('"zoom_lo" required for zoom-in mode for rundown')
                if 'zoom_hi' not in self.test_parameters.keys():
                    raise TestError('"zoom_hi" required for zoom-in mode for rundown')
                if self.test_parameters['zoom_lo'] >= self.test_parameters['zoom_hi']:
                    raise TestError('"zoom_lo" >= "zoom_hi"')
        if 'enable_email' not in self.test_parameters.keys():
            self.test_parameters['enable_email'] = False
        if 'enable_int_email' not in self.test_parameters.keys():
            self.test_parameters['enable_int_email'] = False

        self.test_handler = classes[self.test](self.dyno, **self.test_parameters)

        # if self.test == "Production/Rundown":
        #     self.test_handler = RundownTest(self.dyno, use_barcode=self.barcode, zoom=self.test_parameters['zoom'],
        #                                     lo=self.test_parameters['lo'],
        #                                     hi=self.test_parameters['hi'],
        #                                     motor_type=self.note, barcode=self.barcode1, sn=self.sn1)
        # elif self.test == "Validation":
        #     self.test_handler = ProductionValidation(self.dyno, use_barcode=self.barcode, zoom=self.test_parameters['zoom'],
        #                                              lo=self.test_parameters['lo'],
        #                                              hi=self.test_parameters['hi'],
        #                                              motor_type=self.note, barcode=self.barcode1, sn=self.sn1)
        # elif self.test == "ThermalMax":
        #     self.test_handler = ControllerThermalMax(self.dyno, use_barcode=self.barcode,
        #                                           motor_type=self.note, barcode=self.barcode1, sn=self.sn1)
        # elif self.test == 'Life Test/Cyclic Test':
        #     self.cyclic = True
        #     self.test_handler = CyclicTest(self.dyno, use_barcode=self.barcode, barcode2=self.barcode2, sn2=self.sn2,
        #                                    motor_type=self.note, barcode=self.barcode1, sn=self.sn1)
        # elif self.test == 'Efficiency Map':
        #     self.cyclic = True
        #     self.test_handler = EfficiencyMapTest(self.dyno, use_barcode=self.barcode,
        #                                           motor_type=self.note, barcode=self.barcode1,
        #                                           sn=self.sn1)
        # elif self.test == 'Line Reactor Test':
        #     self.cyclic = True
        #     self.test_handler = CyclicOpenLoopTest(self.dyno, use_barcode=self.barcode,
        #                                            motor_type=self.note, barcode=self.barcode1,
        #                                            sn=self.sn1)
        # elif self.test == "LineReactor":
        #     self.test_handler = LineReactorTest(self.dyno, use_barcode=self.barcode,
        #                                         motor_type=self.note, barcode=self.barcode1, sn=self.sn1)
        # elif self.test == "Debug":
        #     self.cyclic = True
        #     self.test_handler = ForDebug(self.dyno)
        # elif self.test == "Debug Dyno Start/Stop":
        #     self.test_handler = DebugStartStop(self.dyno)

    def run(self):
        self.start_update()
        try:
            self.test_handler.run()
            # if self.test == "Production/Rundown":
            #     self.test_handler.rundown_test()
            # elif self.test == "Validation":
            #     self.test_handler.production_validation()
            # elif self.test == "ThermalMax":
            #     self.test_handler.control_thermal_max()
            # elif self.test == 'Life Test/Cyclic Test':
            #     self.test_handler.cyclic_test()
            # elif self.test == 'Efficiency Map':
            #     self.test_handler.cyclic_test()
            #
            # elif self.test == 'Line Reactor Test':
            #     self.test_handler.cyclic_test()
            #
            # elif self.test == "LineReactor":
            #     self.test_handler.line_reactor_test()
            # elif self.test == "Debug":
            #     self.test_handler.debug()
            #     if self.test_parameters['enable_email']:
            #         test_email(to='twu@acceleratedsystems.com', attach=f"{ROOT_DIR}\\Logs\\std-9.log")
            # elif self.test == "Debug Dyno Start/Stop":
            #     self.test_handler.debug()
            if self.test == "Debug":
                if self.test_parameters['enable_email']:
                    test_email(to='twu@acceleratedsystems.com', attach=f"{ROOT_DIR}\\Logs\\std-9.log")
        except TestInterrupt:
            logging.info("Test Interrupted")
        except TestError as e:
            logging.error(f"Error during Test: {e}")
        finally:
            if self.dyno:
                self.dyno.testing = False
                self.dyno.stop_test()
                self.dyno.stop_logging()
            self.stop_update()

    def interrupt(self):
        # self.test_handler.testing = False
        # self.dyno.testing = False
        self.test_handler.interrupt()

    def start_update(self):
        self.status_thread = Thread(target=self.update_status)
        self.status_thread.start()

    def stop_update(self):
        self.status_thread = None

    def update_status(self):
        while self.dyno.testing:
            sleep(1)
            self.test_parameters['Start Time'] = self.test_handler.startTime
            try:
                if str(self.dyno.logdir).split('\\')[-1] != self.test_parameters['result_dir_var'].get():
                    self.test_parameters['result_dir_var'].set(str(self.dyno.logdir).split('\\')[-1])
            except AttributeError:
                pass

            try:
                test_duration = (datetime.now() - self.test_parameters['Start Time']).total_seconds()
                if test_duration > 600:
                    hours = test_duration // 3600
                    minutes = (test_duration % 3600) // 60
                    seconds = test_duration % 60
                    self.test_parameters['Duration'] = f'{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}'
                else:
                    self.test_parameters['Duration'] = f'{test_duration:.1f}'

                # Cyclic test email notification triggers
                if self.cyclic:
                    self.test_parameters['Cycles'] = f'{self.dyno.test_outputs["current_cycle"]}/' \
                                                     f'{self.dyno.test_outputs["total_cycles"]}'
                    self.test_parameters['Steps'] = f'{self.dyno.test_outputs["current_step"]}/' \
                                                    f'{self.dyno.test_outputs["total_steps"]}'
                else:
                    self.test_parameters['Cycles'] = 'N/A'
                    self.test_parameters['Steps'] = 'N/A'

                self._calculate_test_duration()
            except (AttributeError, TypeError, KeyError):
                pass

    def _calculate_test_duration(self):
        """
        GUI backend
        Updates status bar test duration
        WIP
        """
        if self.dyno is not None:
            if self.test == 'ThermalMax':
                self.test_parameters['Est. Test Time'] = f'{self.dyno.TestTime + 2} min'
            elif self.test == 'Life Test/Cyclic Test':
                if self.test_handler.current_cycle < 2:
                    cycle_mode = -1
                    if pd.isna(self.dyno.config['cycle_type']) or self.dyno.config['cycle_type'] == '':
                        self.test_parameters['Est. Test Time'] = '0'
                        # raise TestError('Bad Cycle Mode')
                        return
                    else:
                        cycle_mode = int(self.dyno.config['cycle_type'])
                    if int(self.dyno.config['cycle_type']) == 0:
                        try:
                            cycles = int(self.dyno.config['jw_cyclic_cycle'])
                        except TypeError:
                            print('Bad value for total total_cycles')
                            raise TestError('Bad value for total total_cycles')

                        try:
                            steps = self.dyno.config['jw_cyclic_step']
                        except (AttributeError, TypeError) as e:
                            logging.error(f"{e}\nWhen loading cyclic test hold times (jw_cyclic_step)")
                            raise TestError("Can't read cyclic total_steps")
                        else:
                            if steps.startswith('[') and steps.endswith(']'):
                                steps = steps.strip('[]').split(', ')
                            elif float(steps):
                                steps = [float(steps)]
                            else:
                                logging.error("Bad total_steps format")
                                raise TestError("Bad total_steps format")

                        if pd.isna(self.dyno.config['jw_cyclic_cd_in_step']):
                            cd_in_step = False
                        else:
                            cd_in_step = bool(self.dyno.config['jw_cyclic_cd_in_step'])
                        def parse_param(var):
                            ans = [0] * len(steps)
                            if isinstance(var, str):
                                if var.startswith('[') and var.endswith(']'):
                                    ans = var.strip('[]').split(', ')
                            elif pd.isna(var):
                                ans = [0] * len(steps)
                            else:
                                try:
                                    float(var)
                                except (ValueError, TypeError):
                                    pass
                                else:
                                    ans = [float(var)] * len(steps)
                            if len(ans) == 1:
                                if pd.isna(ans[0]):
                                    ans = [0] * len(steps)
                            return ans

                        cd = self.dyno.config['cycle_cd']
                        cd = parse_param(cd)
                        ramp = self.dyno.config['jw_cyclic_ramp']
                        ramp = parse_param(ramp)

                    duration_sec = 0
                    for i in range(len(steps)):
                        duration_sec += ramp[i] * 2 + float(steps[i])
                        if cd_in_step:
                            if cycle_mode == 0:
                                duration_sec += cd[i] * 60
                            elif cycle_mode > 0:
                                duration_sec += 1800
                    if cycle_mode == 0:
                        duration_sec += cd[0] * 60
                        duration_sec = cycles * duration_sec + 10 - cd[0] * 60
                    elif cycle_mode > 0:
                        duration_sec += 1800
                        duration_sec = cycles * duration_sec + 10 - 1800

                elif 1 < self.test_handler.current_cycle < self.test_handler.cycle:
                    duration_sec = self.dyno.test_outputs['cycle_duration']
                    duration_sec = self.test_handler.args['total_cycles'] * duration_sec - self.test_handler.cooldown * 60

                self.test_parameters['Est. Test Time'] = \
                    f'{duration_sec // 3600:03g}:{(duration_sec % 3600) // 60:02g}:{duration_sec % 60:02g}'
            elif self.test == "Production/Rundown":
                self.test_parameters['Est. Test Time'] = '~3 min'
            elif self.test == "Efficiency Map":
                self.test_parameters['Est. Test Time'] = '~2 hrs'

