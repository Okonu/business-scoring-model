"""Errors raised by the BASEPOINT data source"""


class BasepointError(Exception):
    """Base class for BASEPOINT errors"""


class AuthenticationError(BasepointError):
    """The company code or the user credentials were rejected"""


class BasepointUnavailableError(BasepointError):
    """The BASEPOINT API could not be reached or returned an unusable response"""
