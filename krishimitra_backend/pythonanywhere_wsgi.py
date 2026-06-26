import sys
import os

# 1. Provide the exact path to your backend directory on PythonAnywhere.
#    Replace 'shivamkarma' with your PythonAnywhere username if it is different.
path = '/home/shivamkarma/KrishiMitra/krishimitra_backend'
if path not in sys.path:
    sys.path.append(path)

# 2. Ensure environment variables can be loaded from the backend directory
from dotenv import load_dotenv
project_folder = os.path.expanduser(path)
load_dotenv(os.path.join(project_folder, '.env'))

# 3. Import the Flask app object
from app import app as application
