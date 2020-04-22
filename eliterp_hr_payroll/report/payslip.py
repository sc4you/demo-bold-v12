# -*- coding: utf-8 -*-


from odoo import api, models

INCOME = ['ING', 'ING_SBS']
EXPENSE = ['EGR']


class Payslip(models.Model):
    _inherit = 'hr.payslip'

    @api.model
    def _get_lines(self, flag):
        lines = []
        if flag == "1":
            filterDomain = INCOME
        else:
            filterDomain = EXPENSE
        for record in self.line_ids.filtered(lambda l: l.category_id.code in filterDomain):
            lines.append({
                'name': record.name,
                'amount': record.total
            })
        return lines
