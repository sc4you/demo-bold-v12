# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Config(models.Model):
    _inherit = 'pos.config'

    module_account = fields.Boolean(default=True)  # CM
    point_printing_id = fields.Many2one('sri.point.printing', string='Punto de impresión')

    journal_id = fields.Many2one('account.journal', default=False)  # CM

    @api.constrains('point_printing_id')
    def _check_point_printing_id(self):
        """
        Validamos tenga facturación electrónica habilitada,
        escencial para este módulo.
        :return:
        """
        if any(self.filtered(lambda pc: not pc.point_printing_id.allow_electronic_invoice)):
            raise ValidationError(_("El punto de impresión debe tener facturación electrónica habilitada!"))