#!/usr/bin/env python3
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@gitorious
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from electroncash.i18n import _
from electroncash.address import Address

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .util import *
from .history_list import HistoryList
from .qrtextedit import ShowQRTextEdit


class RegisterCashAcctDialog(WindowModalDialog):

    def __init__(self, parent, address):
        assert isinstance(address, Address)
        WindowModalDialog.__init__(self, parent, _("Register Cash Account"))
        self.address = address
        self.parent = parent
        self.config = parent.config
        self.wallet = parent.wallet
        self.app = parent.app
        self.saved = True
        self.setMinimumWidth(700)
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel(_("Desired username:")))
        self.cashacct_e = ButtonsLineEdit()
        vbox.addWidget(self.cashacct_e)

        vbox.addWidget(QLabel(_("Address:")))
        self.addr_e = ButtonsLineEdit()
        self.addr_e.addCopyButton()
        self.addr_e.setReadOnly(True)
        vbox.addWidget(self.addr_e)
        self.update_addr()

        vbox.addLayout(Buttons(RegisterCashAcctButton(self)))
        vbox.addLayout(Buttons(CloseButton(self)))

    def update_addr(self):
        self.addr_e.setText(self.address.to_full_ui_string())

    def show_qr(self):
        text = self.address.to_full_ui_string()
        try:
            self.parent.show_qrcode(text, 'Address', parent=self)
        except Exception as e:
            self.show_message(str(e))

    def exec_(self):
        ''' Overrides super class and does some cleanup after exec '''
        retval = super().exec_()
        import gc
        QTimer.singleShot(10, lambda: gc.collect()) # run GC in 10 ms. Otherwise this window sticks around in memory for way too long
        return retval
