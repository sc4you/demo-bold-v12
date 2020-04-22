# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons import decimal_precision as dp
from odoo.osv import expression

TYPE_TAX = [
    ('t1', 'IVA diferente de 0%'),
    ('t2', 'IVA 0%'),
    ('t3', 'No objeto a IVA'),
    ('t4', 'Exento de IVA'),
    ('t5', 'Retención renta'),
    ('t6', 'Retención de IVA'),
    ('t7', 'Retención impuesto a la renta'),
    ('t8', 'No sujetos a RIR'),
    ('t9', 'Impuesto aduana'),
    ('t10', 'Super de bancos'),
    ('t11', 'Compensaciones'),
    ('t12', 'Otro')
]


class AccountType(models.Model):
    _inherit = 'account.account.type'

    type = fields.Selection(selection_add=[('view', 'Vista')])


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def _prepare_transfer_account_template(self):
        vals = super(AccountChartTemplate, self)._prepare_transfer_account_template()
        vals.update({
            'name': 'CUENTA DE TRANSFERENCIAS BANCARIAS',
            'account_level': '5'
        })
        return vals

    def _get_account_vals(self, company, account_template, code_acc, tax_template_ref):
        """
        ME: Actualizamos los campos nuevos en cuenta contable.
        Para la cuenta 101010201 debemos colocar manualmente datos adicionales.
        :return:
        """
        vals = super(AccountChartTemplate, self)._get_account_vals(
            company, account_template, code_acc, tax_template_ref
        )
        vals.update({
            'account_level': account_template.account_level,
            'alternate_code': account_template.alternate_code or False
        })
        return vals

    def load_for_current_company(self, sale_tax_rate, purchase_tax_rate):
        """
        ME: Actualizamos las cuentas padres de cada cuenta.
        :param sale_tax_rate:
        :param purchase_tax_rate:
        :return:
        """
        result = super(AccountChartTemplate, self).load_for_current_company(sale_tax_rate, purchase_tax_rate)
        company = self.env.user.company_id
        existing_accounts = self.env['account.account'].search([('company_id', '=', company.id)])
        for a in existing_accounts.filtered(lambda x: x.account_level != '1'):
            parent_id = self.env['account.account'].search([('code', '=', a.code[:len(a.code) - 2])])
            if parent_id:
                a.write({'parent_id': parent_id.id})
        return result

    @api.model
    def _get_default_bank_journals_data(self):
        """
        MM
        :return:
        """
        return [{'acc_name': _('EFECTIVO'), 'account_type': 'cash'},
                {'acc_name': _('BANCO BOLIVARIANO'), 'account_type': 'bank'}]


class AccountTemplate(models.Model):
    _inherit = 'account.account.template'

    parent_id = fields.Many2one('account.account.template', 'Cuenta padre')
    alternate_code = fields.Char(string='Código alterno', size=64, index=True,
                                 help="Sirve para facilidad de búsqueda de cuentas contables.")
    account_level = fields.Selection(
        [
            ('1', '1'),
            ('2', '2'),
            ('3', '3'),
            ('4', '4'),
            ('5', '5'),
            ('6', '6'),
        ], string="Nivel de cuenta", help="Sirve para saber el nivel de jerarquía de la cuenta.")


class Account(models.Model):
    _inherit = 'account.account'
    _parent_name = "parent_id"
    _parent_store = True
    _order = 'parent_path'

    @api.model
    def _search_new_account_code(self, company, digits, prefix):
        """
        MM: Quitamos los dígitos colocamos directamente
        :param company:
        :param digits:
        :param prefix:
        :return:
        """
        for num in range(1, 100):
            new_code = str(prefix.ljust(11 - 1, '0')) + str(num)
            rec = self.search([('code', '=', new_code), ('company_id', '=', company.id)], limit=1)
            if not rec:
                return new_code
        raise UserError(_('No se puede generar un código de cuenta no utilizado.'))

    def _get_beginning_balance(self, start_date):
        """
        Obtenemos el saldo inicial de una cuenta contable:
        :param start_date:
        :return: float
        """
        debit = 0.00
        credit = 0.00
        move_lines = self.env['account.move.line'].search([
            ('account_id', '=', self.id),
            ('date', '<', start_date)
        ])
        for line in move_lines:
            credit += line.credit
            debit += line.debit
        type = self.code[0]
        return self._get_balance_nature_account(type, debit, credit)

    @staticmethod
    def _get_balance_nature_account(type_account, debit, credit):
        """
        Monto de balance según naturaleza de cuenta contable
        http://enrique-asuntoscontables.blogspot.com/2011/09/clasificacion-general-de-las-cuentas.html
        :param type:
        :param debit:
        :param credit:
        :return balance:
        """
        balance = debit - credit
        if type_account in ['1', '5']:
            if debit < credit:
                if balance > 0:
                    balance = -1 * balance
        if type_account in ['2', '3', '4']:
            if debit < credit:
                if balance < 0:
                    balance = -1 * balance
            if debit > credit:
                if balance > 0:
                    balance = -1 * balance
        return balance

    @api.multi
    def _account_balance(self, account, accounts, date_from=False, date_to=False):
        """
        Balance de cuenta contable
        https://www.contabilidae.com/deudor-y-acreedor/
        :param accounts:
        :param date_from:
        :param date_to:
        :return:
        """
        debit = 0.00
        credit = 0.00
        balance = 0.00
        arg = [('account_id', 'in', accounts.ids)]
        if date_from and date_to:
            arg.append(('date', '>=', date_from))
            arg.append(('date', '<=', date_to))
        account_lines = self.env['account.move.line'].search(arg)
        if not account_lines:
            return debit, credit, balance
        for line in account_lines:
            credit += line.credit
            debit += line.debit
        balance = self._get_balance_nature_account(account.code[0], debit, credit)
        return debit, credit, balance

    @api.multi
    @api.depends('accounting_lines', 'accounting_lines.debit', 'accounting_lines.credit')
    def _compute_balance(self):
        """
        Mostramos el débito, crédito y balance de cada cuenta,
        las cuenta padres suman los registros de las cuentas hijas.
        :return:
        """
        for account in self:
            # Colocamos contexto para no mostrar cuentas padres en transacciones
            subaccounts = self.with_context({'show_parent_account': True}).search([('id', 'child_of', [account.id])])
            data = list(self._account_balance(account, subaccounts))
            account.debit = data[0]
            account.credit = data[1]
            account.balance = data[2]

    @api.multi
    def write(self, vals):
        """
        Revisar qué al cambiar el tipo a vista no tenga línea de movimiento
        :param vals:
        :return:
        """
        if 'user_type_id' in vals and self.user_type_id.id != vals['user_type_id']:
            user_type_id = self.env['account.account.type'].browse(vals['user_type_id'])
            # Soló cuando queremos cambiar a tipo vista verificamos no tenga movimientos
            if user_type_id.type == 'view':
                if self.env['account.move.line'].search([('account_id', 'in', self.ids)], limit=1):
                    raise UserError(
                        _(
                            "Está cuenta ya contiene apuntes, por lo tanto, no puede cambiar a tipo vista. (código: %s)" % self.code))
        return super(Account, self).write(vals)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        """
        Verificar cuenta padre
        :return:
        """
        if not self._check_recursion():
            raise ValidationError(_('No puede crear cuentas padres recursivas.'))
        if not self._check_account_parent_id():
            raise ValidationError(_("Cuenta padre inválida para código de cuenta: %s.") % self.code)
        return True

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """
        MM: Agregamos ala búsqueda el código alterno de la cuenta contable y soló cuentas tipo vista
        cuando estemos en el menú del mismo
        :param name:
        :param args:
        :param operator:
        :param limit:
        :param name_get_uid:
        :return:
        """
        args = args or []
        domain = []
        if not self._context.get('show_parent_account', False):
            args += [('internal_type', '!=', 'view')]
        if name:
            args += [('alternate_code', '=', name)]
            account_ids = self._search(args, limit=limit, access_rights_uid=name_get_uid)
            if account_ids:
                return self.browse(account_ids).name_get()
            args.pop()
            domain = ['|', ('code', '=ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        account_ids = self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
        return self.browse(account_ids).name_get()

    def _check_account_parent_id(self):
        """
        Validar cuenta padre sea válida para
        código de cuenta
        :return:
        """
        result = True
        temp = len(self.code)
        if not self.account_level == '1' and temp >= 3:
            parent_code = self.parent_id.code
            if parent_code != self.code[:temp - 2]:
                result = False
        return result

    alternate_code = fields.Char(string='Código alterno', size=64, index=True,
                                 help="Sirve para facilidad de búsqueda de cuentas contables.")
    accounting_lines = fields.One2many('account.move.line', 'account_id', string='Líneas de asientos contables')
    parent_id = fields.Many2one('account.account', 'Cuenta padre')
    account_level = fields.Selection(
        [
            ('1', '1'),
            ('2', '2'),
            ('3', '3'),
            ('4', '4'),
            ('5', '5'),
            ('6', '6'),
        ], string="Nivel de cuenta", help="Sirve para saber el nivel de jerarquía de la cuenta.")
    child_ids = fields.One2many('account.account', 'parent_id', string='Cuentas hijas')
    credit = fields.Float(string='Crédito', compute='_compute_balance', digits=dp.get_precision('Account'))
    debit = fields.Float(string='Débito', compute='_compute_balance', digits=dp.get_precision('Account'))
    balance = fields.Float(string='Saldo', compute='_compute_balance', digits=dp.get_precision('Account'))
    parent_path = fields.Char(index=True)

    _sql_constraints = [
        ('alternate_code_company_unique', 'unique (alternate_code, company_id)',
         _('El código alterno debe ser único por compañía!')),
    ]


class TaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    def _get_tax_vals(self, company, tax_template_to_tax):
        vals = super(TaxTemplate, self)._get_tax_vals(company, tax_template_to_tax)
        vals.update({
            'ats_code': self.ats_code or False,
            'type_tax': self.type_tax
        })
        return vals

    ats_code = fields.Char('Código ATS')
    type_tax = fields.Selection(TYPE_TAX, string='Tipo de impuesto', default='t1', required=True)


class Tax(models.Model):
    _inherit = 'account.tax'

    @api.multi
    def name_get(self):
        result = []
        for data in self:
            if data.type_tax in ['t5', 't6'] and data.ats_code:
                result.append((data.id, "[%s] %s" % (data.ats_code, data.name)))
            else:
                result.append((data.id, "%s" % data.name))
        return result

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = default or {}
        if self.ats_code:
            default['ats_code'] = _("%s (copia)") % self.ats_code
        return super(Tax, self).copy(default=default)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        """
        ME: Agregamos a la búsqueda el código de retención
        :param name:
        :param args:
        :param operator:
        :param limit:
        :param name_get_uid:
        :return:
        """
        args = args or []
        if name:
            args = [('ats_code', '=', name)]
        tax_ids = self._search(args, limit=limit, access_rights_uid=name_get_uid)
        if not tax_ids:
            return super(Tax, self)._name_search(name, args=None, operator=operator, limit=limit,
                                                 name_get_uid=name_get_uid)
        return self.browse(tax_ids).name_get()

    ats_code = fields.Char('Código ATS')
    type_tax = fields.Selection(TYPE_TAX, string='Tipo de impuesto', default='t1', required=True)
    _sql_constraints = [
        ('code_unique', 'unique (ats_code, type_tax_use, company_id)',
         _("El código ATS debe ser único por tipo de impuesto!"))
    ]


class Journal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def _get_account_parent_id(self, code):
        """
        Obtenemos la cuenta padre soló para diarios
        tipo banco y efectivo.
        :param code:
        :return:
        """
        temp = len(code)
        parent_account = self.env['account.account'].search([('code', '=', code[:temp - 2])])
        if parent_account:
            return parent_account.id
        raise UserError(_("No existe cuenta padre para código %s en Diario contable.\n"
                          "Revise plan contable de compañía.") % code)

    @api.model
    def _prepare_liquidity_account(self, name, company, currency_id, type):
        vals = super(Journal, self)._prepare_liquidity_account(name, company, currency_id, type)
        if type in ['cash', 'bank']:
            vals['parent_id'] = self._get_account_parent_id(vals['code'])
        return vals

    @api.model
    def _create_sequence(self, vals, refund=False):
        """
        ME: Le quitamos el padding a 0
        :param vals:
        :param refund:
        :return:
        """
        seq = super(Journal, self)._create_sequence(vals, refund)
        seq.padding = 0
        return seq
