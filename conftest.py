# Exclude the standalone installation script from pytest collection.
# It is designed to run as `python test_installation.py`, not through pytest.
collect_ignore = ["test_installation.py"]
