import pyotp

def generate_totp_secret() -> str:
    """Generate a new TOTP secret."""
    return pyotp.random_base32()

def generate_totp(secret: str, interval: int = 120) -> str:
    """
    Generates a TOTP (Time-based One-Time Password) using the user's secret.
    
    Args:
        secret (str): The TOTP secret.
        interval (int): The time step in seconds (default is 30 seconds).
    
    Returns:
        str: The generated OTP.
    """
    totp = pyotp.TOTP(secret, interval=interval)
    return totp.now()

def verify_totp(secret: str, otp: str, interval: int = 120) -> bool:
    """Verify a TOTP code using the secret."""
    totp = pyotp.TOTP(secret, interval=interval)
    return totp.verify(otp)