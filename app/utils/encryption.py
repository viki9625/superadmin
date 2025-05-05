from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv, set_key
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load the .env file
env_file = ".env" # Consider using a more robust way to find the .env file if needed
load_dotenv(dotenv_path=env_file)

# Check if the key exists in the .env file
key_str = os.getenv("ENCRYPTION_KEY") # Use a more descriptive variable name like ENCRYPTION_KEY

# Validate the key (Fernet keys are base64-encoded 32-byte keys)
key_bytes = None
if key_str:
    try:
        key_bytes = key_str.encode()
        # Attempt to initialize Fernet to validate the key format implicitly
        Fernet(key_bytes)
        logger.info("Encryption key loaded successfully from .env file.")
    except (ValueError, TypeError):
        logger.warning("Invalid key format found in .env file. Generating a new key.")
        key_bytes = None # Invalidate the key if format is wrong

if not key_bytes:
    # Generate a new key
    key_bytes = Fernet.generate_key()
    key_str = key_bytes.decode() # Store the string representation
    logger.info(f"Generated new encryption key.")

    # Store the new key in the .env file
    # Ensure the .env file exists or handle the case where it doesn't
    if not os.path.exists(env_file):
        with open(env_file, "w") as f:
            pass # Create the file if it doesn't exist
        logger.info(f"Created .env file at: {os.path.abspath(env_file)}")

    if set_key(env_file, "ENCRYPTION_KEY", key_str):
        logger.info("New encryption key stored in .env file.")
    else:
        logger.error("Failed to store the new encryption key in the .env file. Please store it manually.")
        logger.error(f"Generated Key: {key_str}") # Log the key if saving fails


# Initialize Fernet with the key bytes
try:
    fernet = Fernet(key_bytes)
except Exception as e:
    logger.critical(f"Failed to initialize Fernet encryption: {e}")
    # Depending on your application's needs, you might want to exit or raise a critical error here.
    # For now, we'll raise an exception to prevent the application from running without encryption.
    raise RuntimeError("Could not initialize encryption service.") from e

def encrypt_data(data: str) -> bytes:
    """
    Encrypts the provided string data.

    Args:
        data: The string data to encrypt.

    Returns:
        The encrypted data as bytes.

    Raises:
        TypeError: If the input data is not a string.
        Exception: For any unexpected errors during encryption.
    """
    if not isinstance(data, str):
        raise TypeError("Input data must be a string.")
    try:
        encoded_data = data.encode('utf-8')
        encrypted_data = fernet.encrypt(encoded_data)
        return encrypted_data
    except Exception as e:
        logger.error(f"Error during data encryption: {e}")
        # Re-raise the exception or handle it as appropriate for your application
        raise Exception("Encryption failed.") from e


def decrypt_data(encrypted_data: bytes) -> str | None:
    """
    Decrypts the provided byte data.

    Args:
        encrypted_data: The encrypted data as bytes.

    Returns:
        The decrypted data as a string, or None if decryption fails
        (e.g., invalid token, wrong key).

    Raises:
        TypeError: If the input data is not bytes.
    """
    if not isinstance(encrypted_data, bytes):
        raise TypeError("Input encrypted_data must be bytes.")
    try:
        decrypted_data = fernet.decrypt(encrypted_data)
        return decrypted_data.decode('utf-8')
    except InvalidToken:
        logger.error("Decryption failed: Invalid token or key.")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during decryption: {e}")
        return None
