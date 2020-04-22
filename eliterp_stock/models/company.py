# -*- coding: utf-8 -*-

from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    sequence_inventory_id = fields.Many2one('ir.sequence', string="Secuencia de A. Inventario",
                                            help="Secuencia utilizada para ajustes de inventario dentro de compañía.")
