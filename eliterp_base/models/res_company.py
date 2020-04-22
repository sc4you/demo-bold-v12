# -*- coding: utf-8 -*-

from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    report_color = fields.Char(string="Color en reporte", help="Seleccionar color (HTML) para reporte.", default="#0056D1")
