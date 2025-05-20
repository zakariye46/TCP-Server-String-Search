from typing import List, Optional
import logging

logger = logging.getLogger("string_match_server")


def reread_file(file_path: str) -> Optional[List[str]]:
    """
    Reads a file each line and returns a list of stripped lines.

    Args:
        file_path (str): Path to the file.

    Returns:
        Optional[List[str]]: List of lines in the file, or None on failure.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
            return [line for line in lines if line]  # filter out empty lines
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
    except Exception as e:
        logger.error(f"Error reading file '{file_path}': {e}")
    return None


def get_file_size(file_path: str) -> Optional[int]:
    """
    Attempt to read a file and return the length of the content.

    Args:
        file_path - the path to the file to be read

    Return
        The length of the content of the file, or None if an error occurs.
    """
    try:
        return len(reread_file(file_path))
    except Exception as e:
        print(f"[ERROR] An error occurred while getting file size: {e}")
        return None
