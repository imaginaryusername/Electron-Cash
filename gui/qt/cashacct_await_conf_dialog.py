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


class AwaitConfirmationDialog(WindowModalDialog):

    def __init__(self, parent, txid, username):
        WindowModalDialog.__init__(self, parent, _("Awaiting Confirmation"))
        self.parent = parent
        self._txid = txid
        self._username = username
        self.block_height = -1
        self.setMinimumWidth(700)
        vbox = QVBoxLayout()
        self.setLayout(vbox)

        vbox.addWidget(QLabel(_("Awaiting confirmation for username: " + username)))
        vbox.addWidget(QLabel(_("Transaction id: " + txid)))

        self.begin_checking()

    def exec_(self):
        ''' Overrides super class and does some cleanup after exec '''
        retval = super().exec_()
        import gc
        QTimer.singleShot(10, lambda: gc.collect()) # run GC in 10 ms. Otherwise this window sticks around in memory for way too long
        return retval

    def begin_checking(self):
        import threading

        def run_check():
            thread = threading.Timer(5.0, run_check)
            thread.start()
            self.block_height = self.check_for_block()

            if self.block_height.__eq__(-1):
                print(self.block_height)
                print("Running check again...")
            else:
                hash = self.get_block_hash()
                collision = self.calculate_cash_acct_collision(hash, self._txid)
                basic_identity = self.block_height - 563620
                cash_account = self.get_cash_account(self._username, basic_identity.__str__(), collision.__str__()).__str__()
                # It is recommended before saving the cash account here to remove the semi-colon
                # attached at the end by the lookup server.
                print(cash_account)
                thread.cancel()

        if self.block_height.__eq__(-1):
            run_check()

    def check_for_block(self):
        import urllib.request
        import json
        block_explorer_url = "https://bch-chain.api.btc.com/v3/tx/"
        txid_str = self._txid
        url = block_explorer_url + txid_str
        print("Checking for block of tx " + txid_str)

        response = urllib.request.urlopen(url)
        block_data = json.loads(response.read().decode())

        if 'err_msg' not in block_data:
            if block_data['data']['block_height'] == -1:
                return -1
            else:
                return block_data['data']['block_height']
        else:
            return -1

    def get_block_hash(self):
        import urllib.request
        import json
        block_explorer_url = "https://bch-chain.api.btc.com/v3/tx/"
        txid_str = self._txid
        url = block_explorer_url + txid_str
        print("Getting block hash of tx " + txid_str)

        response = urllib.request.urlopen(url)
        block_data = json.loads(response.read().decode())

        if 'err_msg' not in block_data:
            if block_data['data']['block_height'] == -1:
                return "???"
            else:
                return block_data['data']['block_hash']
        else:
            return "???"

    def calculate_cash_acct_collision(self, block_hash, tx_hash):
        from hashlib import sha256
        concatenated_string = block_hash.__str__().lower() + tx_hash.__str__().lower()
        print(concatenated_string)
        import codecs

        decode_hex = codecs.getdecoder("hex_codec")
        decoded_concatenated = decode_hex(concatenated_string)[0]

        hashed_string = sha256(decoded_concatenated).hexdigest()
        print(hashed_string)

        first_four_bytes = hashed_string[:8]
        print(first_four_bytes)

        decimal_notation = int(first_four_bytes, 16).__str__()
        print(decimal_notation)

        reverse_decimal = decimal_notation[::-1]
        print(reverse_decimal)

        padded_decimal = reverse_decimal.ljust(10, '0')
        print(padded_decimal)

        return padded_decimal

    def get_cash_account(self, username, block, collision):
        import urllib.request
        import json
        lookup_url = "https://api.cashaccount.info/account/" + block + "/" + username + "/" + collision
        response = urllib.request.urlopen(lookup_url)
        account_data = json.loads(response.read().decode())

        if 'error' not in account_data:
            return account_data['identifier']
        else:
            return account_data['error']