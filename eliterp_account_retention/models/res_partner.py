# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class Template(models.Model):
    _inherit = 'product.template'

    insurance_product = fields.Boolean('Utilizado para seguro', default=False,
                                       help="Técnico: campo al generar retención a Proveedor se retendrá el 0,1% del "
                                            "valor de la prima facturada y se aplica el código 322.")

    @api.onchange('type')
    def _onchange_type_for_expense(self):
        if self.type in ['consu', 'product']:
            self.insurance_product = False


class Company(models.Model):
    _inherit = 'res.company'

    default_tax_retention_id = fields.Many2one('account.tax',
                                               domain=[('type_tax', '=', 't5'), ('type_tax_use', '=', 'purchase')],
                                               string='Impuesto de retención (renta) por defecto. (p.e. 332)')
    default_tax_retention_insurance_id = fields.Many2one('account.tax',
                                                         domain=[('type_tax', '=', 't5'),
                                                                 ('type_tax_use', '=', 'purchase')],
                                                         string='Impuesto de retención (renta) para prima de facturas '
                                                                'de seguros. (p.e 322)')


class Partner(models.Model):
    _inherit = 'res.partner'

    @api.one
    @api.constrains('insurance_company', 'generate_zero_retention')
    def _check_retention(self):
        if self.insurance_company and self.generate_zero_retention:
            raise ValidationError(_("Empresa no puede generar retención en cero y ser empresa de tipo seguro."))

    customer_retention = fields.Boolean('Requiere retención', default=False,
                                        help="Técnico: sirve para saber si cliente debe genera retención.")
    default_retention_rent_id = fields.Many2one('account.tax',
                                                domain=[('type_tax', '=', 't5'), ('type_tax_use', '=', 'purchase')],
                                                string='Retención renta por defecto',
                                                help="Al generar retención de proveedor se utilizará para el cálculo "
                                                     "de la retención renta.")
    default_retention_iva_id = fields.Many2one('account.tax',
                                               domain=[('type_tax', '=', 't6'), ('type_tax_use', '=', 'purchase')],
                                               string='Retención del IVA por defecto',
                                               help="Al generar retención de proveedor se utilizará para el cálculo "
                                                    "de la retención del IVA.")
    insurance_company = fields.Boolean('Empresa de seguro', default=False,
                                       help="Al generar la retención el sistema calculará la base sobre el 1% de la "
                                            "factura.")
    generate_zero_retention = fields.Boolean('Generar retención en cero', default=False,
                                             help="Campo qué sirve para generar retención asumida (p.e proveedores de "
                                                  "gasolina). Impuesto configurado a nivel de compañía.")
