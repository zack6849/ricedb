import re

import irc3


@irc3.plugin
class Formatting(object):
    irc_codes_regex = re.compile('\x1f|\x02|\x1D|\x03(?:\d{1,2}(?:,\d{1,2})?)?', re.UNICODE)

    class Color(object):
        RESET = '\x0f'
        WHITE = '00'
        BLACK = '01'
        BLUE = '02'
        GREEN = '03'
        RED = '04'
        BROWN = '05'
        PURPLE = '06'
        ORANGE = '07'
        YELLOW = '08'
        LIGHT_GREEN = '09'
        TEAL = '10'
        LIGHT_CYAN = '11'
        LIGHT_BLUE = '12'
        PINK = '13'
        GRAY = '14'
        LIGHT_GRAY = '15'

    def __init__(self, bot):
        self.bot = bot
        self.bot.color = self.Color

    @irc3.extend
    def format(self, text, color=None, bold=False, reset=True):
        if bold:
            text = '\x02{0}'.format(text)
        if color:
            text = '\x03{0}{1}'.format(color, text)
        if reset:
            text += self.bot.color.RESET
        return text

    @irc3.extend
    def strip_formatting(self, string):
        return self.irc_codes_regex.sub('', string)
