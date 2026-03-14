"""Setup Verification Script."""

import os
import sys

def check_python_version():
    """Check if Python version is 3.8+"""
    print("Checking Python version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Need 3.8+")
        return False

def check_packages():
    """Check if required packages are installed"""
    print("\nChecking required packages...")
    packages = [
        'django',
        'pandas',
        'numpy',
        'sklearn',
        'hmmlearn'
    ]
    
    all_good = True
    for package in packages:
        try:
            __import__(package)
            print(f"✅ {package} - Installed")
        except ImportError:
            print(f"❌ {package} - NOT installed")
            all_good = False
    
    return all_good

def main():
    print("="*50)
    print("Cricket Prediction System - Setup Verification")
    print("="*50)
    print()
    
    python_ok = check_python_version()
    packages_ok = check_packages()
    api_key_present = bool(os.getenv("CRICKETDATA_API_KEY"))

    print("\n" + "="*50)
    if python_ok and packages_ok:
        print("✅ ALL CHECKS PASSED!")
        print("\nYou're ready to run the project!")
        if api_key_present:
            print("✅ CRICKETDATA_API_KEY detected - next match API is enabled")
        else:
            print("ℹ️ CRICKETDATA_API_KEY not set - built-in next match fallback will be used")
        print("\nNext steps:")
        print("1. Run: python manage.py migrate")
        print("2. Run: python manage.py runserver")
        print("3. Open: http://127.0.0.1:8000")
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease install missing packages:")
        print("pip install -r requirements.txt")
    print("="*50)

if __name__ == "__main__":
    main()
