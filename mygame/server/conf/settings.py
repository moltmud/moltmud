# Moltmud Game Settings
# Built on Evennia 5.0.1 with SQLite backend for initial development

from evennia.settings_default import *
import os

# Game Name
SERVERNAME = "moltmud"

######################################################################
# Database Configuration - SQLite for initial development
######################################################################

# Create database directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "database")

# Ensure database directory exists
os.makedirs(DB_DIR, exist_ok=True)

# SQLite Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(DB_DIR, 'moltmud.db'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

######################################################################
# Evennia Server Configuration
######################################################################

SERVER_PORT = 4000

######################################################################
# Game-specific settings
######################################################################

# Auto-create superuser on first run
MULTISESSION_MODE = True

# Session cache settings
SESSION_TIMEOUT = 60 * 60  # 1 hour

# Account creation - allow agents to self-register
# For production, enable Moltbook verification
AUTO_CREATE_SUPERUSER = True

# Email validation - disabled for development
EMAIL_VALIDATION = False

######################################################################
# Import from secret_settings if needed
######################################################################

try:
    from server.conf.secret_settings import *
except ImportError:
    # secret_settings.py not required for SQLite dev mode
    pass

######################################################################
# Moltmud-specific imports
######################################################################

# We'll add our typeclasses, commands, etc. in later files
# These are registered in server/conf/typeclasses.py
