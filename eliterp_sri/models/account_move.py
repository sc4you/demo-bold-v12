# -*- coding: utf-8 -*-

from odoo import fields, models


class MoveLine(models.Model):
    _inherit = 'account.move.line'

    point_printing_id = fields.Many2one('sri.point.printing', related='move_id.point_printing_id',
                                        string='Punto de impresión', readonly=False,
                                        store=True, copy=False)


class Move(models.Model):
    _inherit = 'account.move'

    point_printing_id = fields.Many2one('sri.point.printing', string='Punto de impresión')
