from __future__ import print_function

"""Fake SMTP Server"""

__author__  = "Ernesto Menéndez"
__version__ = "0.7"

import asyncore
import smtpd
import socket

from commands import run_command


subscribers = set()


class Mail(object):
    layout =\
"""\n==========================================
peer: {peer}
mailfrom: {mailfrom}
rcpttos: {rcpttos}
----------------- DATA -------------------
{data}
==========================================
""".replace("\n", "\n\r")

    def __init__(self, peer, mailfrom, rcpttos, data):
        self.peer = peer
        self.mailfrom = mailfrom
        self.rcpttos = rcpttos
        self.data = data
        
    def __str__(self):
        return Mail.layout.format(peer=self.peer, mailfrom=self.mailfrom,
                                  rcpttos=self.rcpttos, data=self.data.replace("\n", "\n\r"))


class DummySMTPServer(smtpd.SMTPServer):
    def __init__(self, localaddr, remoteaddr):
        smtpd.SMTPServer.__init__(self, localaddr, remoteaddr)
        
    def process_message(self, peer, mailfrom, rcpttos, data):
        mail = Mail(peer, mailfrom, rcpttos, data)
        print(mail)
        publish(mail)
        
        
class Subscriber(asyncore.dispatcher_with_send):
    def __init__(self, sock):
        asyncore.dispatcher_with_send.__init__(self, sock)
        self._input_buffer = ''
        self._mail_hooks = []

    def handle_read(self):
        char = self.recv(1)
        
        if (char == ""):
            self.unsubscribe()
        elif (char == '\n'):
            run_command(self, self._input_buffer)
            self._input_buffer = ''
            
            if self in subscribers:
                self._interact()
            else:
                return
        elif (char == '\r'):
            pass
        elif (char == '\x08'):
            if len(self._input_buffer) > 0:
                self.send(' ', False)
                self._input_buffer = self._input_buffer[:-1]
            self.send('\r')
        elif (char == '\x09'):
            self.send('\r')
        elif (char == '\x1B'):
            # TODO: Procesar teclas especiales (utilizan mas de un char, de momento se ignoran).
            #       Utilizarlas para agregar funcionalidad a la consola (historia de comandos, etc).
            try:
                self.recv(5)
            except socket.error:
                pass
        elif (char >= '\x20') and (char <= '\x7E'):
            # TODO: reemplazar por un buffer eficiente
            self._input_buffer += char
            
    def unsubscribe(self):
        subscribers.remove(self)
        self.close()

    def send(self, data, interact=True):
        asyncore.dispatcher_with_send.send(self, data)
        if interact:
            self._interact()
            
    def send_mail(self, mail):
        mail = self._call_mail_hooks(mail)
        if mail is not None:
            self.send(str(mail))
            
    def add_mail_hook(self, hook, *args):
        self._mail_hooks.append((hook, args))
        
    def remove_mail_hook(self, hook, *args):
        i = self._get_mail_hook_index(hook, *args)
        if i is not None:
            del self._mail_hooks[i]
        return i is not None
        
    def mail_hook_exists(self, hook, *args):
        return self._get_mail_hook_index(hook, *args) is not None
        
    def _get_mail_hook_index(self, hook, *args):
        for i in xrange(len(self._mail_hooks)):
            hook_, args_ = self._mail_hooks[i]
            if (hook == hook_) and (args == args_):
                return i
        
    def _call_mail_hooks(self, mail):
        try:
            for hook, args in self._mail_hooks:
                if mail is None: break
                mail = hook(mail, *args)
        except:
            self.send('\n\rError procesando "mail_hook": {0}\n\n\r'.format(repr(hook)))
            raise
        return mail
        
    def _interact(self):
        self.send('> ' + self._input_buffer, False)
        

class Publisher(asyncore.dispatcher):
    def __init__(self, addr, welcome_message=None):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(addr)
        self.listen(5)
        
        if welcome_message is None:
            self.welcome_message = 'Bienvenido al publicador de correos version {version}\n\n\r'
        else:
            self.welcome_message = welcome_message
        
        if '{version}' in self.welcome_message:
            self.welcome_message = self.welcome_message.format(version=__version__)

    def handle_accept(self):
        pair = self.accept()
        if pair is not None:
            sock, addr = pair
            subscriber = Subscriber(sock)
            subscriber.send(self.welcome_message)
            subscribers.add(subscriber)


# ================================================================================================


def start(smtp_addr, publisher_addr=None):
    if publisher_addr is not None:
        publisher = Publisher(publisher_addr)
        print("Servidor publicador de mensajes escuchando en %s:%d" % publisher_addr)

    dss = DummySMTPServer(smtp_addr, ())
    print("Servidor SMTP escuchando en %s:%d" % smtp_addr)
    asyncore.loop()


def publish(mail):
    print("Enviando a {n} subscriptor(es)...".format(n=len(subscribers)))
    for s in subscribers:
        s.send_mail(mail)
        
        
if __name__ == "__main__":
    start(("0.0.0.0", 2525), ("0.0.0.0", 2526))
