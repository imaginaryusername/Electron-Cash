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

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QCompleter, QPlainTextEdit
from .qrtextedit import ScanQRTextEdit

import re
from decimal import Decimal as PyDecimal  # Qt 5.12 also exports Decimal
from electroncash import bitcoin
from electroncash.address import Address, ScriptOutput
from electroncash import networks
from electroncash.verifier import SPV
from electroncash.transaction import Transaction

from . import util

RE_ALIAS = '^(.*?)\s*\<([0-9A-Za-z:]{26,})\>$'

frozen_style = "QWidget { background-color:none; border:none;}"
normal_style = "QPlainTextEdit { }"

class PayToEdit(ScanQRTextEdit):

    def __init__(self, win):
        ScanQRTextEdit.__init__(self)
        self.win = win
        self.amount_edit = win.amount_e
        self.document().contentsChanged.connect(self.update_size)
        self.heightMin = 0
        self.heightMax = 150
        self.c = None
        self.textChanged.connect(self.check_text)
        self.outputs = []
        self.errors = []
        self.is_pr = False
        self.is_alias = False
        self.scan_f = win.pay_to_URI
        self.update_size()
        self.payto_address = None

        self.previous_payto = ''

    def setFrozen(self, b):
        self.setReadOnly(b)
        self.setStyleSheet(frozen_style if b else normal_style)
        self.overlay_widget.setHidden(b)

    def setGreen(self):
        self.setStyleSheet(util.ColorScheme.GREEN.as_stylesheet(True))

    def setExpired(self):
        self.setStyleSheet(util.ColorScheme.RED.as_stylesheet(True))

    def parse_address_and_amount(self, line):
        x, y = line.split(',')
        out_type, out = self.parse_output(x)
        amount = self.parse_amount(y)
        return out_type, out, amount

    def parse_output(self, x):
        try:
            address = self.parse_address(x)
            return bitcoin.TYPE_ADDRESS, address
        except:
            return bitcoin.TYPE_SCRIPT, ScriptOutput.from_string(x)

    def parse_address(self, line):
        r = line.strip()
        m = re.match(RE_ALIAS, r)
        address = m.group(2) if m else r
        return Address.from_string(address)

    def parse_amount(self, x):
        if x.strip() == '!':
            return '!'
        p = pow(10, self.amount_edit.decimal_point())
        return int(p * PyDecimal(x.strip()))

    def get_cash_account(self, username, block, collision):
        print("Getting cash account...")
        import urllib.request
        import urllib.error
        import json
        lookup_url = "https://api.cashaccount.info/account/" + block + "/" + username + "/" + collision
        print(lookup_url)
        verify_url = "https://api.cashaccount.info/lookup/" + block + "/" + username + "/" + collision
        print(verify_url)
        try:
            response = urllib.request.urlopen(lookup_url)
            account_data = json.loads(response.read().decode())
            verify_response = urllib.request.urlopen(verify_url)
            verify_data = json.loads(verify_response.read().decode())
            if 'error' not in account_data and 'error' not in verify_data:
                # verify transaction is valid from verify_url, this is first step to verifying the actual account
                verify_height = verify_data['block']
                verify_txid = bh2u(Hash(bfh(verify_data['results'][0]['transaction']))[::-1])
                verify_proof = verify_data['results'][0]['inclusion_proof']
                verify_return = self.check_merkle(verify_height,verify_txid,verify_proof)
                
                if verify_return
                    return account_data['information']['payment'][0]['address']
                else:
                    print('Merkle proof did not match')
            else:
                return account_data['error']
        except urllib.error.HTTPError as e:
            print('Error getting Cash Account: {}'.format(e.reason))

            if collision.__eq__(""):
                return "Cash Account not found: " + username + "#" + block
            else:
                return "Cash Account not found: " + username + "#" + block + "." + collision

    def check_text(self):
        self.errors = []
        if self.is_pr:
            return
        # filter out empty lines
        lines = [i for i in self.lines() if i]
        outputs = []
        total = 0
        self.payto_address = None
        if len(lines) == 1:
            data = lines[0]
            if data.lower().startswith(networks.net.CASHADDR_PREFIX + ":"):
                self.scan_f(data)
                return
            try:
                self.payto_address = self.parse_output(data)
            except:
                pass
            if self.payto_address:
                self.win.lock_amount(False)
                return

        is_max = False
        for i, line in enumerate(lines):
            try:
                _type, to_address, amount = self.parse_address_and_amount(line)
            except:
                self.errors.append((i, line.strip()))
                continue

            outputs.append((_type, to_address, amount))
            if amount == '!':
                is_max = True
            else:
                total += amount

        self.win.max_button.setChecked(is_max)
        self.outputs = outputs
        self.payto_address = None

        if self.win.max_button.isChecked():
            self.win.do_update_fee()
        else:
            self.amount_edit.setAmount(total if outputs else None)
            self.win.lock_amount(total or len(lines)>1)

    def check_text_for_cash_acct(self):
        self.errors = []
        if self.is_pr:
            return
        # filter out empty lines
        lines = [i for i in self.lines() if i]
        outputs = []
        total = 0
        self.payto_address = None
        if len(lines) == 1:
            if '#' in lines[0]:
                username, block = lines[0].split("#")
                if '.' in block:
                    new_block, collision = block.split(".")
                    lines[0] = self.get_cash_account(username, new_block, collision).__str__()
                else:
                    lines[0] = self.get_cash_account(username, block, "").__str__()

                data = lines[0]
                if data.lower().startswith(networks.net.CASHADDR_PREFIX + ":"):
                    self.scan_f(data)
                    return
                try:
                    self.payto_address = self.parse_output(data)
                except:
                    pass
                if self.payto_address:
                    self.win.lock_amount(False)
                    return
            else:
                data = lines[0]
                if data.lower().startswith(networks.net.CASHADDR_PREFIX + ":"):
                    self.scan_f(data)
                    return
                try:
                    self.payto_address = self.parse_output(data)
                except:
                    pass
                if self.payto_address:
                    self.win.lock_amount(False)
                    return

        is_max = False
        for i, line in enumerate(lines):
            try:
                if '#' in line:
                    username, block = line.split("#")
                    new_block, amount_str = block.split(",")

                    if '.' in new_block:
                        final_block, collision = new_block.split(".")
                        line = self.get_cash_account(username, final_block, collision).__str__() + "," + amount_str
                        _type, to_address, amount = self.parse_address_and_amount(line)
                    else:
                        line = self.get_cash_account(username, new_block, "").__str__() + "," + amount_str
                        _type, to_address, amount = self.parse_address_and_amount(line)
                else:
                    _type, to_address, amount = self.parse_address_and_amount(line)
            except:
                self.errors.append((i, line.strip()))
                continue

            outputs.append((_type, to_address, amount))
            if amount == '!':
                is_max = True
            else:
                total += amount

        self.win.max_button.setChecked(is_max)
        self.outputs = outputs
        self.payto_address = None

        if self.win.max_button.isChecked():
            self.win.do_update_fee()
        else:
            self.amount_edit.setAmount(total if outputs else None)
            self.win.lock_amount(total or len(lines)>1)

    def get_errors(self):
        return self.errors

    def get_recipient(self):
        return self.payto_address

    def get_outputs(self, is_max):
        if self.payto_address:
            if is_max:
                amount = '!'
            else:
                amount = self.amount_edit.get_amount()

            _type, addr = self.payto_address
            self.outputs = [(_type, addr, amount)]

        return self.outputs[:]

    def lines(self):
        return self.toPlainText().split('\n')

    def is_multiline(self):
        return len(self.lines()) > 1

    def paytomany(self):
        self.setText("\n\n\n")
        self.update_size()

    def update_size(self):
        lineHeight = QFontMetrics(self.document().defaultFont()).height()
        docHeight = self.document().size().height()
        h = docHeight * lineHeight + 11
        if self.heightMin <= h <= self.heightMax:
            self.setMinimumHeight(h)
            self.setMaximumHeight(h)
        self.verticalScrollBar().hide()


    def setCompleter(self, completer):
        self.c = completer
        self.c.setWidget(self)
        self.c.setCompletionMode(QCompleter.PopupCompletion)
        self.c.activated.connect(self.insertCompletion)


    def insertCompletion(self, completion):
        if self.c.widget() != self:
            return
        tc = self.textCursor()
        extra = len(completion) - len(self.c.completionPrefix())
        tc.movePosition(QTextCursor.Left)
        tc.movePosition(QTextCursor.EndOfWord)
        tc.insertText(completion[-extra:])
        self.setTextCursor(tc)


    def textUnderCursor(self):
        tc = self.textCursor()
        tc.select(QTextCursor.WordUnderCursor)
        return tc.selectedText()


    def keyPressEvent(self, e):
        if self.isReadOnly():
            return

        if self.c.popup().isVisible():
            if e.key() in [Qt.Key_Enter, Qt.Key_Return]:
                e.ignore()
                return

        if e.key() in [Qt.Key_Tab]:
            e.ignore()
            return

        if e.key() in [Qt.Key_Down, Qt.Key_Up] and not self.is_multiline():
            e.ignore()
            return

        QPlainTextEdit.keyPressEvent(self, e)

        ctrlOrShift = e.modifiers() and (Qt.ControlModifier or Qt.ShiftModifier)
        if self.c is None or (ctrlOrShift and not e.text()):
            return

        eow = "~!@#$%^&*()_+{}|:\"<>?,./;'[]\\-="
        hasModifier = (e.modifiers() != Qt.NoModifier) and not ctrlOrShift
        completionPrefix = self.textUnderCursor()

        if hasModifier or not e.text() or len(completionPrefix) < 1 or eow.find(e.text()[-1]) >= 0:
            self.c.popup().hide()
            return

        if completionPrefix != self.c.completionPrefix():
            self.c.setCompletionPrefix(completionPrefix)
            self.c.popup().setCurrentIndex(self.c.completionModel().index(0, 0))

        cr = self.cursorRect()
        cr.setWidth(self.c.popup().sizeHintForColumn(0) + self.c.popup().verticalScrollBar().sizeHint().width())
        self.c.complete(cr)

    def qr_input(self):
        data = super(PayToEdit,self).qr_input()
        if data and data.startswith(networks.net.CASHADDR_PREFIX + ":"):
            self.scan_f(data)
            # TODO: update fee

    def resolve(self):
        self.is_alias = False
        if self.hasFocus():
            return
        if self.is_multiline():  # only supports single line entries atm
            return
        if self.is_pr:
            return
        key = str(self.toPlainText())
        if key == self.previous_payto:
            return
        self.previous_payto = key
        if not (('.' in key) and (not '<' in key) and (not ' ' in key)):
            return
        parts = key.split(sep=',')  # assuming single lie
        if parts and len(parts) > 0 and Address.is_valid(parts[0]):
            return
        try:
            data = self.win.contacts.resolve(key)
        except:
            return
        if not data:
            return
        self.is_alias = True

        address = data.get('address')
        name = data.get('name')
        new_url = key + ' <' + address + '>'
        self.setText(new_url)
        self.previous_payto = new_url

        #if self.win.config.get('openalias_autoadd') == 'checked':
        self.win.contacts[key] = ('openalias', name)
        self.win.contact_list.on_update()

        self.setFrozen(True)
        if data.get('type') == 'openalias':
            self.validated = data.get('validated')
            if self.validated:
                self.setGreen()
            else:
                self.setExpired()
        else:
            self.validated = None
