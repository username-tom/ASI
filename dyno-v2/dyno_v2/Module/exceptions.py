class CommLossError(Exception):
    """Error when communication is lost"""
    pass

class NotInRunParameterError(Exception):
    """Raise when accessing parameter not in run parameter"""
    pass

class NotInPDOParameterError(Exception):
    """Raised when accessing parameter not in run parameter"""
    pass

class NotInLogParameterError(Exception):
    """Raised when accessing parameter not in log parameter"""
    pass

class ConnectionInterruptedError(Exception):
    """Raise when connection is interrupted"""
    pass

class TestError(Exception):
    """Raise when something is wrong during a test"""
    pass

class TestInterrupt(Exception):
    """Raise when interrupting a test"""
    pass

class J1939TimeoutError(Exception):
    """Raise when J1939 takes too long to respond"""
    pass
