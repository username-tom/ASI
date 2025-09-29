from configparser import ConfigParser


# loading parameters from config.ini
config = ConfigParser()
config.read('config.ini')
GEOMETRY = config.get('default', 'geometry')
FONT_SIZE = int(config.get('default', 'font_size'))