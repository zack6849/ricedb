try:
    import ujson as json
except ImportError:
    import json
import os
import random
import re
import sqlite3

import irc3
import markovify
from irc3.plugins.command import command

CMD_PREFIX_PATTERN = re.compile(r'^\s*(\.|!|~|`|\$)+')
SED_CHECKER = re.compile(r's/(.*/.*(?:/[igx]{{,4}})?)\S*$')


def should_ignore_message(line):
    if not line:
        return

    return CMD_PREFIX_PATTERN.match(line) or SED_CHECKER.match(line) or line.startswith('[') or line.startswith('\x01ACTION ')


@irc3.plugin
class Ai(object):
    requires = [
        'plugins.botui',
        'plugins.formatting'
    ]

    def __init__(self, bot):
        self.bot = bot
        self.datadir = 'data'
        self.channel_file = os.path.join(self.datadir, 'ai.json')
        self.active_channels = []
        self.ignore_nicks = []
        self.max_loaded_lines = 20000

        try:
            self.ignore_nicks = self.bot.config[__name__]['ignore_nicks'].split()
        except KeyError:
            pass

        try:
            self.max_loaded_lines = self.bot.config[__name__]['max_loaded_lines']
        except KeyError:
            pass

        try:
            with open(self.channel_file, 'r') as fd:
                self.active_channels = json.load(fd)
        except FileNotFoundError:
            if not os.path.exists(self.datadir):
                os.mkdir(self.datadir)
                self.bot.log.debug('Created {0}/ directory'.format(self.datadir))

        self._init_db()

    def _init_db(self):
        self.conn = sqlite3.connect(os.path.join(self.datadir, 'ai.sqlite'))
        cursor = self.conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS corpus (line TEXT PRIMARY KEY, channel TEXT)')
        self.conn.commit()

    def _add_line(self, line, channel):
        cursor = self.conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO corpus VALUES (?,?)', (line, channel))
        self.conn.commit()

    def _get_lines(self, channel=None):
        cursor = self.conn.cursor()
        if channel:
            cursor.execute('SELECT * FROM corpus WHERE channel=? ORDER BY RANDOM() LIMIT ?', (channel, self.max_loaded_lines))
        else:
            cursor.execute('SELECT * FROM corpus ORDER BY RANDOM() LIMIT ?', (self.max_loaded_lines,))

        lines = [self.bot.strip_formatting(line[0]) for line in cursor.fetchall()]
        return lines if len(lines) > 0 else None

    def _line_count(self, channel=None):
        cursor = self.conn.cursor()
        if channel:
            cursor.execute('SELECT COUNT(*) FROM corpus WHERE channel=?', (channel,))
        else:
            cursor.execute('SELECT COUNT(*) FROM corpus')
        return cursor.fetchone()[0]

    def is_active(self, channel):
        return channel in self.active_channels

    def toggle(self, channel):
        try:
            self.active_channels.remove(channel)
        except ValueError:
            self.active_channels.append(channel)

        with open(self.channel_file, 'w') as fd:
            json.dump(self.active_channels, fd)

    @command
    def ai(self, mask, target, args):
        """Toggles chattiness.

            %%ai [--status]
        """

        if args['--status']:
            line_count = self._line_count()
            channel_line_count = self._line_count(target)
            channel_percentage = 0

            # Percentage of global lines the current channel accounts for.
            if channel_line_count >= 0 and line_count >= 0:
                channel_percentage = int(round(100 * float(channel_line_count) / float(line_count), ndigits=0))

            return 'Chatbot is currently {0} for {3}. Channel/global line count: {2}/{1} ({4}%).'.format(
                'enabled' if self.is_active(target) else 'disabled',
                line_count, channel_line_count, target, channel_percentage)

        if not self.bot.is_chanop(target, mask.nick):
            return 'You must be a channel operator (% and above) to do that.'

        self.toggle(target)
        return 'Chatbot activated.' if self.is_active(target) else 'Shutting up!'

    @irc3.event(r'.*:(?P<mask>\S+!\S+@\S+) PRIVMSG (?P<channel>#\S+) :\s*(?P<data>\S+.*)$')
    def handle_line(self, mask, channel, data):
        if mask.nick in self.ignore_nicks or mask.nick == self.bot.nick:
            return

        data = data.strip()
        if should_ignore_message(data):
            return

        # Only respond to messages mentioning the bot in an active channel
        if self.bot.nick.lower() not in data.lower():
            # Only add lines that aren't mentioning the bot
            self._add_line(data, channel)
            return

        if not self.is_active(channel):
            return

        corpus = self._get_lines()
        if not corpus:
            self.bot.log.warning('Not enough lines in corpus for markovify to generate a decent reply.')
            return

        text_model = markovify.NewlineText('\n'.join(corpus))
        generated_reply = text_model.make_short_sentence(180)
        if not generated_reply:
            self.bot.privmsg(channel, random.choice(['What?', 'Hmm?', 'Yes?', 'What do you want?']))
            return

        self.bot.privmsg(channel, generated_reply.strip())
