from distutils.core import setup

install_requires = [
    'twisted==16.6.0',
	'astral',
    'paho-mqtt==1.3.1',
    'concurrentloghandler>=0.9.1',
    'circus==0.14.0',
    'pyserial==2.7'
]
setup(name='pilogger',
      version='1.1.0',
      description='Python IoT logging utilities',
      long_description='Python IoT logging utilities',
      author='Geurt Lagemaat',
      author_email='geurtlagemaat@gmail.com',
      py_modules=['BliknetNode', 'busListner', 'pvdataUpload' 'smartmeterUpload'],
      )