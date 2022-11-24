"""Tests for the filesize component."""
import os

from spencerassistant.core import spencerAssistant

TEST_DIR = os.path.join(os.path.dirname(__file__))
TEST_FILE_NAME = "mock_file_test_filesize.txt"
TEST_FILE_NAME2 = "mock_file_test_filesize2.txt"
TEST_FILE = os.path.join(TEST_DIR, TEST_FILE_NAME)
TEST_FILE2 = os.path.join(TEST_DIR, TEST_FILE_NAME2)


async def async_create_file(hass: spencerAssistant, path: str) -> None:
    """Create a test file."""
    await hass.async_add_executor_job(create_file, path)


def create_file(path: str) -> None:
    """Create the test file."""
    with open(path, "w", encoding="utf-8") as test_file:
        test_file.write("test")
