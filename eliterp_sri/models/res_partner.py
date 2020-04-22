# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from stdnum import ec

LIST_TYPE_DOCUMENTATION = [
    ('0', 'RUC'),
    ('1', 'Cédula'),
    ('2', 'Pasaporte'),
    ('3', 'Consumidor final'),
    ('4', 'Otro'),
]


class Partner(models.Model):
    _inherit = 'res.partner'

    @api.onchange('documentation_number')
    def _onchange_documentation_number(self):
        """
        Al ir cambiando número de identificación vamos actualizando el campo VAT (Sirve para búsquedas)
        :return object:
        """
        vat = ""
        if self.documentation_number:
            vat = "EC" + self.documentation_number
        res = {'value': {'vat': vat}}
        return res

    @api.constrains('documentation_number')
    def _check_documentation_number(self):
        """
        Validar dígitos de documento y verificar qué no exista empresa.
        Se utiliza la clase ec de la librería stdnum.
        :return:
        """
        if not self.documentation_number:
            return True
        if self.type_documentation == '0' and self.documentation_number and len(self.documentation_number) != 13:
            raise ValidationError(_("Debe ingresar 13 dígitos para tipo RUC."))
        if self.type_documentation == '1' and self.documentation_number and len(self.documentation_number) != 10:
            raise ValidationError(_("Debe ingresar 10 dígitos para tipo Cédula."))
        # TODO: Revisar librería ec

    @api.one
    @api.depends('documentation_number')
    def _compute_kind_person(self):
        """
        Calculamos el tipo de persona
        :return:
        """
        if not self.documentation_number:
            return
        if len(self.documentation_number) < 3:
            return
        if int(self.documentation_number[2]) <= 6:
            self.kind_person = '6'
        elif int(self.documentation_number[2]) in [6, 9]:
            self.kind_person = '9'
        else:
            self.kind_person = '0'

    def _valid_documentation_number(self, dn):
        """
        Verificamos no exista empresa
        Si viene campo cómo cédula revisar no exista cómo RUC
        y asi viceversa. Recortamos el campo o aumentamos en el campo para búsqueda.
        :param dn:
        :return:
        """
        if len(dn) == 10:
            new_dn = dn + '001'
        else:
            new_dn = dn[:10]
        partner_id = self.search([('documentation_number', 'in', [dn, new_dn]), ('id', '!=', self.id)])
        if partner_id:
            raise ValidationError(
                _('Ya existe empresa en registros con este No. Identificación.'))
        else:
            return

    @api.model
    def create(self, vals):
        if 'documentation_number' in vals and 'type_documentation' in vals:
            if not vals['type_documentation'] == '2':
                self._valid_documentation_number(vals['documentation_number'])
        # Si es una empresa creada dentro de otra se lo coloca cómo contacto
        if 'parent_id' in vals:
            if vals['parent_id']:
                vals.update({'is_contact': True})
        return super(Partner, self).create(vals)

    @api.multi
    def write(self, vals):
        if not self.type_documentation == '2':
            if 'documentation_number' in vals:
                self._valid_documentation_number(vals['documentation_number'])
        if 'parent_id' in vals:
            if vals['parent_id']:
                vals.update({'is_contact': True})
        return super(Partner, self).write(vals)

    @api.multi
    def name_get(self):
        res = []
        for data in self:
            if data.documentation_number:
                display_name = '{0} [{1}]'.format(data.name, data.documentation_number)
            else:
                display_name = data.name
            res.append((data.id, display_name))
        return res

    @api.multi
    def _compute_balance_provider(self):
        """
        Saldo pendiente por pagar de proveedor
        :return: object
        """
        Invoice = self.env['account.invoice']
        for partner in self:
            domain = [
                ('partner_id', '=', partner.id),
                ('state', '=', 'open'),
                ('type', '=', 'in_invoice')
            ]
            invoices = Invoice.search(domain)
            partner.balance_provider = sum(line.residual for line in invoices)

    @api.multi
    def action_view_balance_provider(self):
        """
        Llevamos a la acción para mostrar facturas pendientes por pagar de proveedor
        :return:
        """
        self.ensure_one()
        action = self.env.ref('account.action_vendor_bill_template')
        result = action.read()[0]
        result['context'] = {
            'default_partner_id': self.id
        }
        result['domain'] = [('partner_id', '=', self.id), ('state', '=', 'open')]
        return result

    tradename = fields.Char('Nombre comercial')
    type_documentation = fields.Selection(LIST_TYPE_DOCUMENTATION, string='Tipo de identificación')
    documentation_number = fields.Char('Nº Identificación',
                                       copy=False,
                                       size=13,
                                       help='Identificación o registro único de contribuyente (RUC).')
    kind_person = fields.Selection(
        compute='_compute_kind_person',
        selection=[
            ('6', 'Persona Natural'),
            ('9', 'Persona Jurídica'),
            ('0', 'Otro')
        ],
        string='Tipo de persona',
        store=True
    )
    country_id = fields.Many2one('res.country', string='País',
                                 ondelete='restrict',
                                 default=lambda self: self.env.ref('base.ec'))  # CM: Por defecto dejamos Ecuador
    canton_id = fields.Many2one('res.canton', string='Cantón')
    parish_id = fields.Many2one('res.parish', string='Parroquia')
    related_party = fields.Selection([('yes', 'Si'),
                                      ('not', 'No')], string='Parte relacionada', default='not', required=True)
    is_company = fields.Boolean(string='Is a Company', default=True,
                                help="Check if the contact is a company, otherwise it is a person")  # CM

    balance_provider = fields.Float(compute='_compute_balance_provider', string='Saldo')
