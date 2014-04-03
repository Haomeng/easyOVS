__author__ = 'baohua'

from cmd import Cmd
from select import poll, POLLIN
from subprocess import call
import sys

from easyovs.bridge import br_addflow, br_delflow, br_dump, br_exists, br_list, br_show
from easyovs.log import info, output, error
from easyovs.util import color_str


PROMPT_KW = 'EasyOVS> '


def check_arg(func):
    def wrapper(self, arg):
        if not arg:
            output('Argument is missed\n')
        else:
            func(self, arg)
    return wrapper


class CLI(Cmd):
    """
    Simple command-arg interface to talk to nodes.
    """

    helpStr = (
        'The command format is: <bridge> command {args}\n'
        'For example:\n'
        '\tEasyOVS> br-int dump\n'
        '\n'
        'Default bridge can be set using\n\tset <bridge>.\n'
    )

    def __init__(self, bridge=None, stdin=sys.stdin):
        self.prompt = color_str('g', PROMPT_KW)
        self.bridge = bridge
        self.stdin = stdin
        self.in_poller = poll()
        self.in_poller.register(stdin)
        Cmd.__init__(self)
        output("***\n Welcome to EasyOVS, type help to see available commands.\n***\n")
        info('*** Starting CLI:\n')
        while True:
            try:
                #if self.isatty():
                #quietRun( 'stty sane' )
                self.cmdloop()
                break
            except KeyboardInterrupt:
                info('\nInterrupt\n')

    def do_addflow(self, arg):
        """
        [bridge] addflow flow
        Add a flow to a bridge.
        """
        args = arg.replace('"', '').replace("'", "")
        if 'actions=' not in args:
            output('Please give a valid flow.\n')
            return
        i = args.index('actions=')
        actions = args[i:].split()
        args = args[:i].split()
        if len(args) >= 2:
            bridge, rule = args[0], args[1:]
        elif self.bridge:
            bridge, rule = self.bridge, args
        else:
            output("Please use [bridge] addflow flow.\n")
            return
        if not rule or not actions or len(actions) != 1:
            output('The flow is not valid.\n')
            return
        rule = ','.join(rule)
        actions = ','.join(actions)
        flow = rule + ' ' + actions
        if not br_addflow(bridge, flow):
            output('Add flow <%s> to %s failed.\n' % (flow, bridge))
        else:
            output('Add flow <%s> to %s done.\n' % (flow, bridge))

    def do_delflow(self, arg):
        """
        [bridge] delflow flow_id
        Del a flow from a bridge.
        """
        args = arg.split()
        if len(args) >= 2:
            flow_ids = ' '.join(args[1:]).replace(',', ' ').split()
            if not br_delflow(args[0], flow_ids):
                output('Del flow#%s from %s failed.\n' % (' '.join(flow_ids), args[0]))
            else:
                output('Del flow#%s from %s done.\n' % (','.join(flow_ids), args[0]))
        elif len(args) == 1 and self.bridge:
            if not br_delflow(self.bridge, arg):
                output('Del flow#%s from %s failed.\n' % (arg, self.bridge))
            else:
                output('Del flow#%s from %s done.\n' % (arg, self.bridge))
        else:
            output("Please use [bridge] delflow flow_id.\n")

    def do_dump(self, arg):
        """
        [bridge] dump
        Dump the flows from a bridge.
        """
        if arg:
            br_dump(arg)
        elif self.bridge:
            br_dump(self.bridge)
        else:
            output("Please give a valid bridge.\n")
            return

    def do_EOF(self, arg):
        """
        Exit.
        """
        output('\n')
        return self.do_exit(arg)

    def do_exit(self, _arg):
        """
        Exit.
        """
        return 'exited by user command\n'

    def do_get(self, _arg):
        """
        Get current default bridge.
        """
        if self.bridge:
            output('Current default bridge is %s\n' % self.bridge)
        else:
            output('Default bridge is not set yet.\nPlease try <bridge> set.\n')

    def do_help(self, line):
        """
        Describe available CLI commands.
        """
        Cmd.do_help(self, line)
        if line is '':
            output(self.helpStr)

    def do_list(self, _arg):
        """
        List available bridges in the system.
        """
        br_list()

    def do_quit(self, line):
        """
        Exit
        """
        return self.do_exit(line)

    def do_set(self, arg):
        """
        <bridge> set
        Set the default bridge
        """
        if not arg:
            output('Argument is missed\n')
        elif not br_exists(arg):
            output('The bridge does not exist.\n You can check available bridges using show\n')
        else:
            self.prompt = color_str('g', PROMPT_KW[:-2] + ':%s> ' % color_str('b', arg))
            self.bridge = arg
            output('Set the default bridge to %s.\n' % self.bridge)

    def do_sh(self, line):
        """
        Run an external shell command.
        """
        call(line, shell=True)

    def do_show(self, arg):
        """
        Show port details of a bridge, with neutron information.
        """
        if arg:
            br_show(arg)
        elif self.bridge:
            br_show(self.bridge)
        else:
            output("Please give a valid bridge.\n")
            return

    def emptyline(self):
        """
        Don't repeat last command when you hit return.
        """
        pass

    def default(self, line):
        #bridge, cmd, line = self.parseline( line )
        if len(line.split()) < 2:
            error('*** Unknown command: %s ***\n' % line)
            return
        bridge, cmd, args = '', '', ''
        if len(line.split()) == 2:
            bridge, cmd = line.split()
        else:
            bridge, cmd, args = line.split()[0], line.split()[1], ' '.join(line.split()[2:])
        if br_exists(bridge):
            try:
                if args:
                    getattr(self, 'do_%s' % cmd)(' '.join([bridge, args]))
                else:
                    getattr(self, 'do_%s' % cmd)(bridge)
            except AttributeError:
                error('*** Unknown command: %s, cmd=%s, bridge=%s, args=%s ***\n' % (line, cmd, bridge, args))
        else:
            error('*** Bridge %s is not existed\n' % bridge)