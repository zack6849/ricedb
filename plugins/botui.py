import platform

import irc3
from irc3.plugins.command import command


@irc3.plugin
class BotUI(object):

    requires = [
        'irc3.plugins.command',
        'irc3.plugins.userlist'
    ]

    def __init__(self, bot):
        self.bot = bot

    @irc3.extend
    def is_chanop(self, channel, nick):
        op_modes = ['@', '&', '~', '%']
        for mode in op_modes:
            try:
                if nick in self.bot.channels[channel].modes[mode]:
                    return True
            except (KeyError, AttributeError):
                continue

        return False

    @command(permission='view')
    def bots(self, mask, target, args):
        """Report in!

            %%bots
        """
        yield 'Reporting in! [Python {0}] https://github.com/TheReverend403/ricedb'.format(platform.python_version())

    @command(permission='admin', show_in_help_list=False)
    def join(self, mask, target, args):
        """Join a channel.

            %%join <channel> [<password>]
        """

        channel = args['<channel>']
        if args['<password>']:
            channel += ' %s' % args['<password>']

        self.bot.join(channel)

    @command(permission='admin', show_in_help_list=False)
    def part(self, mask, target, args):
        """Leave a channel.

            %%part [<channel>]
        """

        if args['<channel>']:
            target = args['<channel>']

        self.bot.part(target)

    @command(permission='admin', show_in_help_list=False)
    def nick(self, mask, target, args):
        """Change nickname of the bot.

            %%nick <nick>
        """

        self.bot.set_nick(args['<nick>'])

    @command(permission='admin', show_in_help_list=False)
    def mode(self, mask, target, args):
        """Set user mode for the bot.

            %%mode <mode-cmd>
        """

        self.bot.mode(self.bot.nick, args['<mode-cmd>'])

    @command(permission='admin', show_in_help_list=False)
    def msg(self, mask, target, args):
        """Send a message.

            %%msg <target> <message>...
        """

        msg = ' '.join(args['<message>'] or [])
        self.bot.privmsg(args['<target>'], msg)

    @command(permission='admin', show_in_help_list=False)
    def broadcast(self, mask, target, args):
        """Broadcast a message to all channels.

            %%psa <message>...
        """
        for channel in self.bot.channels:
            self.bot.privmsg(channel, '[Broadcast] {0}'.format(' '.join(args['<message>'])))

    @command(permission='view')
    def ping(self, mask, target, args):
        """Ping!

            %%ping
        """
        self.bot.privmsg(target, 'Pong!')
