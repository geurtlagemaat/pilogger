########################################
# Fabfile to:
#    - deploy Bliknet Logger
########################################

# Import Fabric's API module
import sys
from fabric.api import *
import fabric.contrib.files
import time
import os
from os.path import join
from posixpath import join as posixjoin

SCRIPT_DIR = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
# targets is located 1 level up (contains credentials)
if __name__ == 'fabfile':
    sys.path.insert(0, join(SCRIPT_DIR))
    sys.path.insert(0, join(SCRIPT_DIR, '..'))

    import targets  # noqa

# todo fix common import
import common  # noqa

"""env.hosts = ['localhost']
env.user = "pi"
env.password = "raspberry"
env.warn_only = True
pi_hardware = os.uname()[4] """

#######################
## Core server setup ##
#######################

def install_start():
    """ Notify of install start """
    print("* Warning *")
    print("""The primary use of this installer is for a new Bliknet Node""")
    time.sleep(10)
    print("Installer is starting...")
    print("Your Raspberry Pi will reboot when the installer is complete.")
    time.sleep(5)

def setup_dirs():
    """ Create all needed directories inside bliknet root and change ownership """
    with cd(common.BLIKNET_BASE_DIR):
        sudo("mkdir pilogger")
        sudo("chown bliknet:bliknet pilogger")
        with cd("pilogger"):
            sudo("mkdir -p src")
            sudo("chown bliknet:bliknet src")

####################################
## Build and Install Applications ##
####################################
def setup_pilogger():
    """ Activate Virtualenv, Install setup_pilogger """
    with cd(os.join(common.BLIKNET_BASE_DIR,"/pilogger/src")):
        sudo("git clone --branch master https://github.com/geurtlagemaat/pilogger.git", user="bliknet")
        with cd("pilogger"):
            sudo("git checkout python", user="bliknet")
            sudo("source %s/bin/activate && make build" % common.BLIKNET_BASE_VIRTUAL_ENV, user="bliknet")
            sudo("source %s/bin/activate && make install" % common.BLIKNET_BASE_VIRTUAL_ENV, user="bliknet")

def setup_services():
    """ Enable applications to start at boot via systemd """
    with cd("/etc/systemd/system/"):
        put("home-assistant.service", "home-assistant.service", use_sudo=True)
    with settings(sudo_user='homeassistant'):
        sudo("/srv/homeassistant/homeassistant_venv/bin/hass --script ensure_config --config /home/homeassistant/.homeassistant")


    hacfg="""
mqtt:
  broker: 127.0.0.1
  port: 1883
  client_id: home-assistant-1
  username: pi
  password: raspberry
"""


    fabric.contrib.files.append("/home/homeassistant/.homeassistant/configuration.yaml", hacfg, use_sudo=True)
    sudo("systemctl enable home-assistant.service")
    sudo("systemctl daemon-reload")
    sudo("systemctl start home-assistant.service")

#############
## Deploy! ##
#############

def deploy():
    ## Install Start ##
    install_start()
    ## Initial Update and Upgrade ##
    common.update_upgrade()
    ## Setup service accounts ##
    common.create_bliknet_user()
    ## Setup directories ##
    common.create_root_dirs()
    setup_dirs()
    ## Install dependencies ##
    common.install_syscore()
    common.install_pycore()
    ## Create VirtualEnv ##
    common.create_venv()
    ## Install pilogger from GIT ##
    setup_pilogger()
    ## Make apps start at boot ##
    # setup_services()
    ## Reboot the system ##
    # reboot()
