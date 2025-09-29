# ASI Includes
from dyno_v2.TestScript.cyclic_test_jason import *
from dyno_v2.Module.asi_controller import ASIController

class EfficiencyTableABBTest(CyclicTest):

    def __init__(
            self,
            dyno,
            *args,
            **kwargs
            # use_barcode=False,
            # motor_type=None,
            # barcode=None,
            # sn=None
    ):
        """
        Efficiency Table w/ ABB Test
        Only works on big Dyno for now
        Uses ABB in speed mode and DUT in torque mode for efficiency values

        Parameters:
            dyno : ASIDynoModule, required
            kwargs: dict, required
                {use_barcode : bool, required |
                barcode1 : dict, required |
                sn1 : str, required |
                note : str, required}
        """
        super().__init__(dyno, *args, **kwargs)

    def parse_test_args(self):
        self.efficiency_table_abb_args()

    def logging_setup(self):
        self.single_logging_setup()

    def test(self):
        
        self.dyno.cycle(
            ramp_command=self.dyno.efficiency_table_ramp,
            hold_setup=self.dyno.efficiency_table_setup,
            hold_condition=self.dyno.efficiency_table_hold_condition,
            hold_command=self.dyno.efficiency_table_hold_command,
            **self.args
        )
            
    def post_test(self):
        """
        Process data here
        """
        print("Test finished")

