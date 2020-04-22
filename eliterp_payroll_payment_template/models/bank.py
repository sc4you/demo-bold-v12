# -*- coding: utf-8 -*-

from odoo import api, fields, models
from datetime import datetime


class Bank(models.Model):
    _inherit = 'res.bank'

    generate_payroll_payment = fields.Boolean('Generar planilla de pago', default=False,
                                              help="Sirve para decirle al sistema qué tiene plantilla para pagos de nómina.")
