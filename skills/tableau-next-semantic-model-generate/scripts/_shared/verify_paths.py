"""Verify script paths are accessible."""
import os
import sys


def verify_scripts():
    """Check if shared scripts are accessible."""
    required_scripts = [
        "discover_sdm.py",
        "create_calc_field.py",
        "create_metric.py",
        "create_sdm.py",
        "add_data_object.py",
        "add_relationship.py",
    ]

    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    missing = []

    for script in required_scripts:
        path = os.path.join(script_dir, script)
        if not os.path.exists(path):
            missing.append(script)

    if missing:
        print(f"ERROR: Missing scripts: {missing}")
        print(f"Expected location: {script_dir}")
        print("The tableau-next-semantic-model-generate skill appears incomplete. Re-install it.")
        sys.exit(1)

    print("All required scripts accessible")
    return True


if __name__ == "__main__":
    verify_scripts()
