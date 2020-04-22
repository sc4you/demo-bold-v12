# -*- coding: utf-8 -*-

from odoo import api, models, fields


class BankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def process_reconciliation(self, counterpart_aml_dicts=None,
                               payment_aml_rec=None, new_aml_dicts=None):
        """
        ME: Cambiamos el nombre de pago y si es tipo Banco
        colocamos el tipo interno. (POS)
        :param counterpart_aml_dicts:
        :param payment_aml_rec:
        :param new_aml_dicts:
        :return:
        """
        result = super(BankStatementLine, self).process_reconciliation(
            counterpart_aml_dicts=counterpart_aml_dicts,
            payment_aml_rec=payment_aml_rec, new_aml_dicts=new_aml_dicts)
        payment = result.mapped('line_ids.payment_id')
        new_name = payment._get_move_name(payment.payment_type)
        # FIXME: internal_movement
        payment.write({
            'name': new_name,
            'internal_movement': 'transfer' if payment.journal_id.type == 'bank' else False
        })
        return result
