# -*- coding: utf-8 -*-


from odoo import api, models, _


class BankReconciliation(models.Model):
    _inherit = 'account.bank.reconciliation'

    @api.multi
    def print_conciliation(self):
        """
        Imprimimos conciliación bancaria
        :return:
        """
        self.ensure_one()
        return self.env.ref('eliterp_account_bank_reconciliation.action_report_bank_reconciliation').report_action(self)

    def _search_origin(self, line):
        # TODO: Revisar si es mejor opción, ver cuando son diferentes
        # formas de pago (Ej. Cheques)
        if line.payment_id:
            payment = line.payment_id
            if payment.payment_type == 'transfer':
                return _("Transferencia bancaria")
            elif payment.payment_type == 'inbound':
                return _("Cobro")
            else:
                return _("Pago")
        move = line.move_id
        name = _("Asiento contable")
        if self.env['account.bank.note'].search([('move_id', '=', move.id)]):
            name = _("Nota bancaria")
        if self.env['account.deposit'].search([('move_id', '=', move.id)]):
            name = _("Depósito bancario")
        return name

    @api.model
    def _get_data(self):
        """
        Función para obtener cantidad de registros y sumatorias por diarios contable en
        conciliación bancaria
        :return:
        """
        data = []
        for line in self.bank_reconciliation_line:
            name = self._search_origin(line.move_line_id)
            aggregate = any(d['name'] == name for d in data)
            if not aggregate:
                data.append({
                    'name': name,
                    'amount': line.amount,
                    'quantity': 1
                })
            else:
                index = list(map(lambda x: x['name'], data)).index(name)
                data[index].update({
                    'amount': data[index]['amount'] + line.amount,
                    'quantity': data[index]['quantity'] + 1
                })
        return data