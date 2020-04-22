# -*- coding: utf-8 -*-

from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    default_advance_percentage = fields.Integer(
        string='Porcentaje de quincena por defecto',
        default=30
    )
    default_journal_advance_id = fields.Many2one('account.journal', string="Diario de anticipo por defecto",
                                                 domain=[('type', '=', 'general')])
    default_journal_payroll_id = fields.Many2one('account.journal', string="Diario de nómina por defecto",
                                                 domain=[('type', '=', 'general')])
    default_account_payroll_id = fields.Many2one('account.account', string="Cuenta para nómina (pagos) por defecto",
                                                 domain=[('internal_type', '=', 'payable')])
    default_account_payroll_utility_id = fields.Many2one('account.account', string="Cuenta para utilidades (pagos) "
                                                                                   "por defecto",
                                                         domain=[('internal_type', '=', 'payable')])
