# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class AuthorizedVouchers(models.Model):
    _inherit = 'sri.authorized.vouchers'

    validate_retention = fields.Boolean('Validar retención', default=False,
                                        help="Técnico: Para saber si documento necesitar emitir retención.")


class Authorization(models.Model):
    _inherit = 'sri.authorization'

    @api.multi
    def unlink(self):
        """
        Al borrar evitar eliminar autorización relacionadas con
        retenciones.
        :return object:
        """
        ObjectRetention = self.env['account.retention']
        for record in self:
            if bool(ObjectRetention.search([('sri_authorization_id', '=', record.id)])):
                raise ValidationError(_("Está autorización SRI está relacionada a un documento."))
        return super(Authorization, self).unlink()
