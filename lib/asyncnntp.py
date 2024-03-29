# Rewrite of some built in Python NNTP classes to be more applicable to our use case.

import re
import socket
from nntplib import NNTP_PORT, NNTPPermanentError, NNTPTemporaryError, NNTPReplyError, \
    CRLF, NNTPProtocolError, LONGRESP, NNTPDataError
import time
import select


def coroutine(func):
    def start(*args, **kwargs):
        cr = func(*args, **kwargs)
        cr.next()
        return cr
    return start


class BasicNNTPResponse(object):
    def __init__(self, line):
        pass


class BasicNNTP(object):
    def __init__(self, connection):
        self.conn = connection
        self.inbuffer = bytearray()
        self.outbuffer = bytearray()
        self.authenticated = False
        self.responses = []

    def handle_recv(self, bytes):
        print 'Receiving:', bytes
        self.inbuffer += bytes
        self.flush_buffer()

    def handle_send(self):
        if self.outbuffer:
            out = str(self.outbuffer)
            self.outbuffer = bytearray()
            print 'Sending:', out
            return out
        raise ValueError('Nothing to Send')

    def flush_buffer(self):
        while True:
            index = self.inbuffer.find(CRLF)
            if index >= 0:
                index += len(CRLF)
                line = str(self.inbuffer[:index])
                self.inbuffer[:index] = []

                if not line:
                    raise EOFError

                line.rstrip(CRLF)
                # Add response to response stack.
                self.responses.append((line[:3], line[4:].strip()))
            else:
                break

    def putline(self, line):
        self.outbuffer += (line + CRLF)
        #self.conn.sendall(line + CRLF)

    def putcmd(self, line):
        self.putline(line)

    def cmd(self, line):
        """Internal: send a command and get the response."""
        self.putcmd(line)
        print 'sending cmd', line
        #return self.getresp()

    def getresp(self):
        while True:
            print 'waiting in getresp'
            if len(self.responses) == 0:
                time.sleep(0.05)
            else:
                yield self.responses.pop()

#        resp = self.getline()
#        c = resp[:1]
#        if c == '4':
#            raise NNTPTemporaryError(resp)
#        if c == '5':
#            raise NNTPPermanentError(resp)
#        if c not in '123':
#            raise NNTPProtocolError(resp)
#        return resp

    def longcmd(self, line, file=None):
        """Internal: send a command and get the response plus following text."""
        self.putcmd(line)
        return self.getlongresp(file)

    def authenticate(self, user, password=None):
        self.cmd('authinfo user ' + user)
        response = self.getresp().next()
        print 'RESPONSE OMG', response
#        return
#        # Asking for password
#        if resp[:3] == '381':
#            if password is None:
#                raise NNTPReplyError(resp)
#            resp = self.cmd('authinfo pass ' + password)
#            if resp[:3] != '281':
#                raise NNTPPermanentError(resp)
#        self.authenticated = True


class NNTPPool(object):
    """
    Open a number of NTTP connections and receive requests,
    multiplex them onto the pool.
    """
    _TIMEOUT = 0.1

    def __init__(self, host, port, user=None, password=None, connections=20):
        self.running = True
        self.conns = {}
        for i in range(connections):
            sock = socket.create_connection((host, port))
            sock.setblocking(0)
            conn = BasicNNTP(sock)
            # Perform NNTP authentication if needed.
            if user is not None:
                conn.authenticate(user, password)
            self.conns[sock] = conn

    def fetch_message(self, group, msg_id):
        pass

    def run(self):
        debug_run_limit = 10
        debug_run_start = int(time.time())
        while self.running is True:
            sockets = self.conns.keys()
            ready_to_read, ready_to_write, in_error = \
                select.select(sockets, sockets, sockets, self._TIMEOUT)

            print len(ready_to_read), len(ready_to_write)

            for sock in ready_to_read:
                self.conns[sock].handle_recv(sock.recv(4096))

            for sock in ready_to_write:
                try:
                    sock.send(self.conns[sock].handle_send())
                except ValueError:
                    pass

            time.sleep(0.1)
            if int(time.time()) >= (debug_run_start + debug_run_limit):
                print 'Ending after 10 seconds...'
                break


class NNTPHardStop(Exception):
    pass


class NNTP(object):
    def __init__(self, host, port=NNTP_PORT, user=None, password=None,
                 readermode=None, usenetrc=True):
        """Initialize an instance.  Arguments:
        - host: hostname to connect to
        - port: port to connect to (default the standard NNTP port)
        - user: username to authenticate with
        - password: password to use with username
        - readermode: if true, send 'mode reader' command after
                      connecting.

        readermode is sometimes necessary if you are connecting to an
        NNTP server on the local machine and intend to call
        reader-specific commands, such as `group'.  If you get
        unexpected NNTPPermanentErrors, you might need to set
        readermode.
        """
        self.host = host
        self.port = port
        self.sock = socket.create_connection((host, port))
        self.sock.setblocking(0)
        self.inbuffer = bytearray()
        self.running = True

        #self.file = self.sock.makefile('rb')
        self.debugging = 0
        self.welcome = self.getresp()

        # 'mode reader' is sometimes necessary to enable 'reader' mode.
        # However, the order in which 'mode reader' and 'authinfo' need to
        # arrive differs between some NNTP servers. Try to send
        # 'mode reader', and if it fails with an authorization failed
        # error, try again after sending authinfo.
        readermode_afterauth = 0
        if readermode:
            try:
                self.welcome = self.shortcmd('mode reader')
            except NNTPPermanentError:
                # error 500, probably 'not implemented'
                pass
            except NNTPTemporaryError, e:
                if user and e.response[:3] == '480':
                    # Need authorization before 'mode reader'
                    readermode_afterauth = 1
                else:
                    raise
        # If no login/password was specified, try to get them from ~/.netrc
        # Presume that if .netc has an entry, NNRP authentication is required.
        try:
            if usenetrc and not user:
                import netrc
                credentials = netrc.netrc()
                auth = credentials.authenticators(host)
                if auth:
                    user = auth[0]
                    password = auth[2]
        except IOError:
            pass
        # Perform NNRP authentication if needed.
        if user:
            resp = self.shortcmd('authinfo user '+user)
            if resp[:3] == '381':
                if not password:
                    raise NNTPReplyError(resp)
                else:
                    resp = self.shortcmd(
                            'authinfo pass '+password)
                    if resp[:3] != '281':
                        raise NNTPPermanentError(resp)
            if readermode_afterauth:
                try:
                    self.welcome = self.shortcmd('mode reader')
                except NNTPPermanentError:
                    # error 500, probably 'not implemented'
                    pass


    # Get the welcome message from the server
    # (this is read and squirreled away by __init__()).
    # If the response code is 200, posting is allowed;
    # if it 201, posting is not allowed
    def getwelcome(self):
        """Get the welcome message from the server
        (this is read and squirreled away by __init__()).
        If the response code is 200, posting is allowed;
        if it 201, posting is not allowed."""

        if self.debugging: print '*welcome*', repr(self.welcome)
        return self.welcome

    def set_debuglevel(self, level):
        """Set the debugging level.  Argument 'level' means:
        0: no debugging output (default)
        1: print commands and responses but not body text etc.
        2: also print raw lines read and sent before stripping CR/LF"""

        self.debugging = level
    debug = set_debuglevel

    def putline(self, line):
        """Internal: send one line to the server, appending CRLF."""
        line += CRLF
        if self.debugging > 1: print '*put*', repr(line)
        self.sock.sendall(line)

    def putcmd(self, line):
        """Internal: send one command to the server (through putline())."""
        if self.debugging: print '*cmd*', repr(line)
        self.putline(line)

    def _read(self):
        while True:
            if self.running is False:
                raise NNTPHardStop()

            try:
                self.inbuffer.extend(self.sock.recv(4096))
            except socket.error as err:
                # We are waiting on data.
                if err.errno == socket.errno.EWOULDBLOCK:
                    break

    def getline(self):
        """Internal: return one line from the server, stripping CRLF.
        Raise EOFError if the connection is closed."""
        #line = self.file.readline()

        # Capture anything already waiting.
        self._read()

        # Check to see if we have a line to give.
        while True:
            if self.running is False:
                raise NNTPHardStop()
            index = self.inbuffer.find(CRLF)
            if index >= 0:
                index += len(CRLF)
                line = str(self.inbuffer[:index])
                self.inbuffer[:index] = []

                if self.debugging > 1:
                    print '*get*', repr(line)

                if not line:
                    raise EOFError

                if line[-2:] == CRLF:
                    line = line[:-2]
                elif line[-1:] in CRLF:
                    line = line[:-1]

                return line
            else:
                # We were asked to produce a line, so that must mean the protocol expects one. Keep trying.
                time.sleep(0.1)
                self._read()

    def getresp(self):
        """Internal: get a response from the server.
        Raise various errors if the response indicates an error."""
        resp = self.getline()
        if self.debugging: print '*resp*', repr(resp)
        c = resp[:1]
        if c == '4':
            raise NNTPTemporaryError(resp)
        if c == '5':
            raise NNTPPermanentError(resp)
        if c not in '123':
            raise NNTPProtocolError(resp)
        return resp

    def getlongresp(self, file=None):
        """Internal: get a response plus following text from the server.
        Raise various errors if the response indicates an error."""

        openedFile = None
        try:
            # If a string was passed then open a file with that name
            if isinstance(file, str):
                openedFile = file = open(file, "w")

            resp = self.getresp()
            if resp[:3] not in LONGRESP:
                raise NNTPReplyError(resp)
            list = []
            while 1:
                line = self.getline()
                if line == '.':
                    break
                if line[:2] == '..':
                    line = line[1:]
                if file:
                    file.write(line + "\n")
                else:
                    list.append(line)
        finally:
            # If this method created the file, then it must close it
            if openedFile:
                openedFile.close()

        return resp, list

    def shortcmd(self, line):
        """Internal: send a command and get the response."""
        self.putcmd(line)
        return self.getresp()

    def longcmd(self, line, file=None):
        """Internal: send a command and get the response plus following text."""
        self.putcmd(line)
        return self.getlongresp(file)

    def newgroups(self, date, time, file=None):
        """Process a NEWGROUPS command.  Arguments:
        - date: string 'yymmdd' indicating the date
        - time: string 'hhmmss' indicating the time
        Return:
        - resp: server response if successful
        - list: list of newsgroup names"""

        return self.longcmd('NEWGROUPS ' + date + ' ' + time, file)

    def newnews(self, group, date, time, file=None):
        """Process a NEWNEWS command.  Arguments:
        - group: group name or '*'
        - date: string 'yymmdd' indicating the date
        - time: string 'hhmmss' indicating the time
        Return:
        - resp: server response if successful
        - list: list of message ids"""

        cmd = 'NEWNEWS ' + group + ' ' + date + ' ' + time
        return self.longcmd(cmd, file)

    def list(self, file=None):
        """Process a LIST command.  Return:
        - resp: server response if successful
        - list: list of (group, last, first, flag) (strings)"""

        resp, list = self.longcmd('LIST', file)
        for i in range(len(list)):
            # Parse lines into "group last first flag"
            list[i] = tuple(list[i].split())
        return resp, list

    def description(self, group):

        """Get a description for a single group.  If more than one
        group matches ('group' is a pattern), return the first.  If no
        group matches, return an empty string.

        This elides the response code from the server, since it can
        only be '215' or '285' (for xgtitle) anyway.  If the response
        code is needed, use the 'descriptions' method.

        NOTE: This neither checks for a wildcard in 'group' nor does
        it check whether the group actually exists."""

        resp, lines = self.descriptions(group)
        if len(lines) == 0:
            return ""
        else:
            return lines[0][1]

    def descriptions(self, group_pattern):
        """Get descriptions for a range of groups."""
        line_pat = re.compile("^(?P<group>[^ \t]+)[ \t]+(.*)$")
        # Try the more std (acc. to RFC2980) LIST NEWSGROUPS first
        resp, raw_lines = self.longcmd('LIST NEWSGROUPS ' + group_pattern)
        if resp[:3] != "215":
            # Now the deprecated XGTITLE.  This either raises an error
            # or succeeds with the same output structure as LIST
            # NEWSGROUPS.
            resp, raw_lines = self.longcmd('XGTITLE ' + group_pattern)
        lines = []
        for raw_line in raw_lines:
            match = line_pat.search(raw_line.strip())
            if match:
                lines.append(match.group(1, 2))
        return resp, lines

    def group(self, name):
        """Process a GROUP command.  Argument:
        - group: the group name
        Returns:
        - resp: server response if successful
        - count: number of articles (string)
        - first: first article number (string)
        - last: last article number (string)
        - name: the group name"""

        resp = self.shortcmd('GROUP ' + name)
        if resp[:3] != '211':
            raise NNTPReplyError(resp)
        words = resp.split()
        count = first = last = 0
        n = len(words)
        if n > 1:
            count = words[1]
            if n > 2:
                first = words[2]
                if n > 3:
                    last = words[3]
                    if n > 4:
                        name = words[4].lower()
        return resp, count, first, last, name

    def help(self, file=None):
        """Process a HELP command.  Returns:
        - resp: server response if successful
        - list: list of strings"""

        return self.longcmd('HELP',file)

    def statparse(self, resp):
        """Internal: parse the response of a STAT, NEXT or LAST command."""
        if resp[:2] != '22':
            raise NNTPReplyError(resp)
        words = resp.split()
        nr = 0
        id = ''
        n = len(words)
        if n > 1:
            nr = words[1]
            if n > 2:
                id = words[2]
        return resp, nr, id

    def statcmd(self, line):
        """Internal: process a STAT, NEXT or LAST command."""
        resp = self.shortcmd(line)
        return self.statparse(resp)

    def stat(self, id):
        """Process a STAT command.  Argument:
        - id: article number or message id
        Returns:
        - resp: server response if successful
        - nr:   the article number
        - id:   the message id"""

        return self.statcmd('STAT ' + id)

    def next(self):
        """Process a NEXT command.  No arguments.  Return as for STAT."""
        return self.statcmd('NEXT')

    def last(self):
        """Process a LAST command.  No arguments.  Return as for STAT."""
        return self.statcmd('LAST')

    def artcmd(self, line, file=None):
        """Internal: process a HEAD, BODY or ARTICLE command."""
        resp, list = self.longcmd(line, file)
        resp, nr, id = self.statparse(resp)
        return resp, nr, id, list

    def head(self, id):
        """Process a HEAD command.  Argument:
        - id: article number or message id
        Returns:
        - resp: server response if successful
        - nr: article number
        - id: message id
        - list: the lines of the article's header"""

        return self.artcmd('HEAD ' + id)

    def body(self, id, file=None):
        """Process a BODY command.  Argument:
        - id: article number or message id
        - file: Filename string or file object to store the article in
        Returns:
        - resp: server response if successful
        - nr: article number
        - id: message id
        - list: the lines of the article's body or an empty list
                if file was used"""

        return self.artcmd('BODY ' + id, file)

    def article(self, id):
        """Process an ARTICLE command.  Argument:
        - id: article number or message id
        Returns:
        - resp: server response if successful
        - nr: article number
        - id: message id
        - list: the lines of the article"""

        return self.artcmd('ARTICLE ' + id)

    def slave(self):
        """Process a SLAVE command.  Returns:
        - resp: server response if successful"""

        return self.shortcmd('SLAVE')

    def xhdr(self, hdr, str, file=None):
        """Process an XHDR command (optional server extension).  Arguments:
        - hdr: the header type (e.g. 'subject')
        - str: an article nr, a message id, or a range nr1-nr2
        Returns:
        - resp: server response if successful
        - list: list of (nr, value) strings"""

        pat = re.compile('^([0-9]+) ?(.*)\n?')
        resp, lines = self.longcmd('XHDR ' + hdr + ' ' + str, file)
        for i in range(len(lines)):
            line = lines[i]
            m = pat.match(line)
            if m:
                lines[i] = m.group(1, 2)
        return resp, lines

    def xover(self, start, end, file=None):
        """Process an XOVER command (optional server extension) Arguments:
        - start: start of range
        - end: end of range
        Returns:
        - resp: server response if successful
        - list: list of (art-nr, subject, poster, date,
                         id, references, size, lines)"""

        resp, lines = self.longcmd('XOVER ' + start + '-' + end, file)
        xover_lines = []
        for line in lines:
            elem = line.split("\t")
            try:
                xover_lines.append((elem[0],
                                    elem[1],
                                    elem[2],
                                    elem[3],
                                    elem[4],
                                    elem[5].split(),
                                    elem[6],
                                    elem[7]))
            except IndexError:
                raise NNTPDataError(line)
        return resp,xover_lines

    def xgtitle(self, group, file=None):
        """Process an XGTITLE command (optional server extension) Arguments:
        - group: group name wildcard (i.e. news.*)
        Returns:
        - resp: server response if successful
        - list: list of (name,title) strings"""

        line_pat = re.compile("^([^ \t]+)[ \t]+(.*)$")
        resp, raw_lines = self.longcmd('XGTITLE ' + group, file)
        lines = []
        for raw_line in raw_lines:
            match = line_pat.search(raw_line.strip())
            if match:
                lines.append(match.group(1, 2))
        return resp, lines

    def xpath(self,id):
        """Process an XPATH command (optional server extension) Arguments:
        - id: Message id of article
        Returns:
        resp: server response if successful
        path: directory path to article"""

        resp = self.shortcmd("XPATH " + id)
        if resp[:3] != '223':
            raise NNTPReplyError(resp)
        try:
            [resp_num, path] = resp.split()
        except ValueError:
            raise NNTPReplyError(resp)
        else:
            return resp, path

    def date (self):
        """Process the DATE command. Arguments:
        None
        Returns:
        resp: server response if successful
        date: Date suitable for newnews/newgroups commands etc.
        time: Time suitable for newnews/newgroups commands etc."""

        resp = self.shortcmd("DATE")
        if resp[:3] != '111':
            raise NNTPReplyError(resp)
        elem = resp.split()
        if len(elem) != 2:
            raise NNTPDataError(resp)
        date = elem[1][2:8]
        time = elem[1][-6:]
        if len(date) != 6 or len(time) != 6:
            raise NNTPDataError(resp)
        return resp, date, time

    def post(self, f):
        """Process a POST command.  Arguments:
        - f: file containing the article
        Returns:
        - resp: server response if successful"""

        resp = self.shortcmd('POST')
        # Raises error_??? if posting is not allowed
        if resp[0] != '3':
            raise NNTPReplyError(resp)
        while 1:
            line = f.readline()
            if not line:
                break
            if line[-1] == '\n':
                line = line[:-1]
            if line[:1] == '.':
                line = '.' + line
            self.putline(line)
        self.putline('.')
        return self.getresp()

    def ihave(self, id, f):
        """Process an IHAVE command.  Arguments:
        - id: message-id of the article
        - f:  file containing the article
        Returns:
        - resp: server response if successful
        Note that if the server refuses the article an exception is raised."""

        resp = self.shortcmd('IHAVE ' + id)
        # Raises error_??? if the server already has it
        if resp[0] != '3':
            raise NNTPReplyError(resp)
        while 1:
            line = f.readline()
            if not line:
                break
            if line[-1] == '\n':
                line = line[:-1]
            if line[:1] == '.':
                line = '.' + line
            self.putline(line)
        self.putline('.')
        return self.getresp()

    def quit(self):
        """Process a QUIT command and close the socket.  Returns:
        - resp: server response if successful"""

        resp = self.shortcmd('QUIT')
        self.running = False  # This will exit any waitloops
        #self.file.close()
        self.sock.close()
        #del self.file, self.sock
        del self.sock
        return resp
