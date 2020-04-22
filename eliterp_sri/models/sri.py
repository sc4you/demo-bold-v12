# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime


class PaymentForms(models.Model):
    _name = 'sri.payment.forms'
    _description = _("Forma de pago SRI")
    _order = "sequence"

    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "[{0}] {1}".format(data.code, data.name)))
        return res

    name = fields.Char('Nombre', required=True)
    sequence = fields.Integer('Secuencia', default=10)
    code = fields.Char('Código', size=2, required=True)

    _sql_constraints = [
        ('code_unique', 'unique (code)', 'El código debe ser único!')
    ]


class ProofSupport(models.Model):
    _name = 'sri.proof.support'
    _description = _("Sustentos del comprobante")
    _order = "sequence"

    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "[{0}] {1}".format(data.code, data.name)))
        return res

    name = fields.Char('Nombre', required=True)
    sequence = fields.Integer('Secuencia', default=10)
    code = fields.Char('Código', size=2, required=True)

    _sql_constraints = [
        ('code_unique', 'unique (code)', 'El código debe ser único!')
    ]


class AuthorizedVouchers(models.Model):
    _name = 'sri.authorized.vouchers'
    _description = _("Comprobantes autorizados")

    _order = "code asc"

    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "{0} [{1}]".format(data.name, data.code)))
        return res

    name = fields.Char('Nombre', required=True)
    code = fields.Char('Código', size=2, required=True)
    own_authorizations = fields.Boolean('Mis autorizaciones', default=False,
                                        help="Campo para generación de autorizaciones físicas del SRI (propias).")
    check_authorization = fields.Boolean('Validar autorización', default=False,
                                         help="Técnico: sistema validará qué se ingrese autorización del SRI.")
    type = fields.Selection([('supplier', 'Proveedor'), ('customer', 'Cliente')], string='Tipo',
                            required=True, default='supplier')
    proof_support_ids = fields.Many2many('sri.proof.support', string='Sustentos del comprobante')

    _sql_constraints = [
        ('code_unique', 'unique (code, type)', _("El código debe ser único por tipo!"))
    ]


class SriEstablishment(models.Model):
    _name = 'sri.establishment'
    _inherit = ['mail.thread']

    _description = _("Establecimientos SRI")

    @api.multi
    def name_get(self):
        result = []
        for shop in self:
            result.append((shop.id, "%s: %s" % (shop.company_id.name, shop.name)))
        return result

    @api.multi
    def toggle_active(self):
        for record in self:
            record.active = not record.active

    name = fields.Char('Nombre de tienda', required=True, index=True, track_visibility='onchange')
    logo = fields.Binary('Logo')
    type = fields.Selection([('matrix', 'Matriz'), ('office', 'Oficina')], default='office',
                            string="Tipo",
                            required=True)
    state_id = fields.Many2one("res.country.state", string='Provincia', required=True, track_visibility='onchange')
    street = fields.Char('Dirección', required=True, track_visibility='onchange')
    active = fields.Boolean('Activo', default=True)
    company_id = fields.Many2one('res.company', 'Compañía', default=lambda self: self.env.user.company_id.id)
    establishment = fields.Char('Nº Establecimiento', size=3, required=True)

    _sql_constraints = [
        ('name_unique', 'unique (company_id, name)', _("El nombre de tienda deber ser único por compañía!")),
        ('establishment_unique', 'unique (establishment, company_id)',
         _('El nº de establecimiento debe ser único por compañía!'))
    ]


class SriPointPrinting(models.Model):
    _name = 'sri.point.printing'
    _description = _("Punto de impresión SRI")
    _order = 'establishment_id'

    @api.one
    def _get_authorization(self, t=None):
        """
        Verificamos si tiene autorización del SRI y seleccionamos la primer qué encuentre
        esste método sirve para asegurarnos de qué exista al menos una (físicas).
        :param type:
        :return:
        """
        sri_authorization = self.env['sri.authorization'].search([
            ('point_printing_id', '=', self.id),
            ('authorized_voucher_id.code', '=', t),
            ('is_valid', '=', True)
        ], limit=1)
        if not sri_authorization:
            raise UserError(_(
                'No ha configurado la autorización del SRI para este punto de impresión (%s). O la misma puede estar '
                'vencida.' %
                self.name))
        else:
            return sri_authorization

    @api.depends('establishment_id', 'emission_point')
    def _compute_name(self):
        for record in self:
            record.name = "{0} - {1}".format(record.establishment_id.establishment, record.emission_point)

    name = fields.Char(string='Nombre', compute='_compute_name', store=True, index=True)
    establishment_id = fields.Many2one('sri.establishment', 'Establecimiento', required=True)
    emission_point = fields.Char('Punto emisión', size=3, default='001', required=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('point_printing_unique', 'unique(establishment_id, emission_point, company_id)',
         "El punto de impresión debe ser único por nº establecimiento!")
    ]


class SriAuthorization(models.Model):
    _name = 'sri.authorization'
    _description = _("Autorizaciones SRI")
    _inherit = ['mail.thread']
    _rec_name = 'authorization'

    _order = "expiration_date desc"

    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "{0} [{1}] de {2} a {3}".format(
                data.authorization,
                data.authorized_voucher_id.code,
                data.initial_number,
                data.final_number
            )))
        return res

    def _check_authorization(self, values):
        """
        Verificamos no exista una autorización (Físicas)
        :return:
        """
        if 'is_electronic' in values and values['is_electronic']:
            return True
        domain = [
            ('company_id', '=', values['company_id']),
            ('point_printing_id', '=', values['point_printing_id']),
            ('authorized_voucher_id', '=', values['authorized_voucher_id']),
            ('is_valid', '=', True),
            ('is_electronic', '=', False)
        ]
        if self.search(domain):
            raise ValidationError(_("Ya existe una Autorización válida del SRI para estos parámetros."))

    @api.model
    def create(self, vals):
        self._check_authorization(vals)
        return super(SriAuthorization, self).create(vals)

    @api.multi
    def unlink(self):
        """
        Al borrar evitar eliminar autorización relacionadas con documentos (Facturas, N/C, etc.)
        :return object:
        """
        invoices = self.env['account.invoice']
        for record in self:
            if bool(invoices.search([('sri_authorization_id', '=', record.id)])):
                raise ValidationError(_("Está Autorización SRI está relacionada a un documento."))
        return super(SriAuthorization, self).unlink()

    @api.model
    def _default_company(self):
        """
        Por defecto mandamos la compañía del usuario
        :return object:
        """
        return self.env.user.company_id

    @api.multi
    def is_valid_number(self, number):
        """
        Si es número inválido, no está en el rango ingresado de la autorización
        :param number:
        :return:
        """
        if self.initial_number <= number <= self.final_number:
            return
        else:
            raise ValidationError(_(
                "Secuencial no está entre rango ingresado en autorización %s. "
                "Debe crear una nueva autorización del SRI o corregirla."
                % self.authorization))

    @api.one
    @api.constrains('final_number')
    def _check_final_number(self):
        """
        Verificamos número final si no es factura electrónica
        :return:
        """
        if self.final_number < self.initial_number:
            raise ValidationError(_("Número final no puede ser menor al inicial."))

    @api.one
    @api.depends('expiration_date', 'is_electronic')
    def _compute_is_valid(self):
        """
        Calculamos sea una autorización válida (No se muestra en documentos, soló es para físicas)
        :return:
        """
        if self.is_electronic:
            self.is_valid = True
        else:
            self.is_valid = datetime.today().date() < self.expiration_date

    initial_number = fields.Integer('Nº Inicial', default=1, required=True, track_visibility='onchange')
    final_number = fields.Integer('Nº Final', default=50, size=9, required=True, track_visibility='onchange')
    authorization = fields.Char('Nº Autorización', size=49, required=True, track_visibility='onchange')
    authorized_voucher_id = fields.Many2one('sri.authorized.vouchers', 'Comprobante autorizado', required=True)
    is_valid = fields.Boolean('Es válida?', compute='_compute_is_valid', store=True)
    expiration_date = fields.Date('Fecha de expiración', required=True, track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=_default_company)
    point_printing_id = fields.Many2one('sri.point.printing', string='Punto de impresión', required=True)
    is_electronic = fields.Boolean('Electrónica?', default=False,
                                   help="Técnico: campo determina si es autorización electrónica.")
