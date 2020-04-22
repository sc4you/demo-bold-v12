# -*- coding: utf-8 -*-


from odoo import models, fields, _
from odoo.addons import decimal_precision as dp


class PartnerCommercialReference(models.Model):
    _description = _('Referencias comerciales')
    _name = "res.partner.commercial.reference"

    name = fields.Char('Nombre', required=True, index=True)


class Partner(models.Model):
    _inherit = 'res.partner'

    default_discount = fields.Float('Descuento por defecto (%)',
                                    digits=dp.get_precision('Discount'),
                                    default=0.0,
                                    help="Descuento aplicado por defecto en cada línea de proforma/pedio de venta.")
    commercial_reference_ids = fields.Many2many('res.partner.commercial.reference',
                                                'res_partner_commercial_reference_rel', 'partner_id',
                                                'commercial_reference_id', string='Referencias comerciales')
