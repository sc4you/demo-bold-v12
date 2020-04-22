# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
import calendar
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare, float_is_zero


class PayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    provisions = fields.Boolean('Provisiones?', default=True,
                                help="Estructura salarial (REPRESENTANTE LEGAL) no acumulan beneficios sociales ("
                                     "FONDOS DE "
                                     "RESERVA, etc.), por lo tanto no se debe marcar.")


class SalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = default or {}
        if self.code:
            default['code'] = _("%s (copia)") % self.code
        return super(SalaryRule, self).copy(default=default)

    appears_on_payslip_run = fields.Boolean(string='Aparece en rol consolidado', default=True,
                                            help="Se usa para mostrar la regla salarial en reporte de rol consolidado.")


class PayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    contract_id = fields.Many2one('hr.contract', string='Contract', required=True,
                                  help="The contract for which applied this input")  # TODO


class ContractInvoiceLine(models.Model):
    _name = 'hr.contract.invoice.line'
    _order = 'residual asc'
    _description = _("Línea de factura en contrato")

    @api.onchange('selected')
    def _onchange_selected(self):
        if self.selected:
            self.amount_payable = self.residual

    selected = fields.Boolean('Conciliar', default=False)
    invoice_id = fields.Many2one('account.invoice', 'Factura')
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', store=True, string="Moneda",
                                  related_sudo=False)
    name = fields.Char('No. Factura', related="invoice_id.reference")
    date_due = fields.Date('Fecha vencimiento', related='invoice_id.date_due', store=True)
    amount_total = fields.Monetary('Total de factura', related='invoice_id.amount_total', store=True)
    residual = fields.Monetary('Saldo de factura', related='invoice_id.residual', store=True)
    amount_payable = fields.Float('Monto a pagar')
    contract_id = fields.Many2one('hr.contract', string='Contrato', ondelete="cascade")


class Contract(models.Model):
    _inherit = 'hr.contract'

    @api.multi
    def load_my_invoices(self):
        """
        Calculamos las facturas por pagar de empleado
        :return:
        """
        self.invoice_ids.unlink()
        partner = self.employee_id.address_home_id
        if not partner:
            return
        InvoiceObject = self.env['account.invoice']
        invoices = InvoiceObject.search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'open')
        ])
        list_invoices = []
        for invoice in invoices:
            list_invoices.append([0, 0, {
                'invoice_id': invoice.id
            }])
        self.invoice_ids = list_invoices

    invoice_ids = fields.One2many('hr.contract.invoice.line',
                                  'contract_id',
                                  string='Líneas de facturas')

    @api.model
    def _default_journal_id(self):
        journal_payroll = self.env.user.company_id.default_journal_payroll_id
        return journal_payroll.id if journal_payroll else False

    journal_id = fields.Many2one(default=_default_journal_id)  # CM


class PayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    def _get_partner_id(self):
        register_partner_id = self.salary_rule_id.register_id.partner_id
        partner_id = register_partner_id.id or self.slip_id.employee_id.address_home_id.id
        return partner_id


class Payslip(models.Model):
    _name = 'hr.payslip'
    _order = 'employee_id asc, date_from desc'
    _inherit = ['hr.payslip', 'mail.thread']

    @api.multi
    def print_role(self):
        return self.env.ref('eliterp_hr_payroll.action_report_payslip').report_action(self)

    @api.one
    @api.depends('date_from')
    def _compute_reference(self):
        self.reference = self.env['res.function']._get_period_string(self.date_from)

    @api.one
    @api.depends('line_ids')
    def _compute_net_receive(self):
        # TODO: Ver si es mejor manera de realizar
        self.net_receive = self.line_ids.filtered(lambda l: l.code == 'TOTA_REC').amount

    def _get_name(self):
        company = self.company_id
        sequence = self.env['ir.sequence'].with_context(force_company=company.id).next_by_code('salary.slip')
        if not sequence:
            raise UserError(
                _("No está definida la secuencia con código 'salary.slip' para compañía: %s") % company.name)
        return sequence

    @api.multi
    def compute_sheet(self):
        """
        MM:
        :return:
        """
        for payslip in self:
            payslip.line_ids.unlink()
            contract_id = payslip.contract_id.id
            lines = [(0, 0, line) for line in self._get_payslip_lines(contract_id, payslip.id)]
            payslip.write({'line_ids': lines})
        return True

    @api.model
    def get_inputs(self, contract=None, struct=None):
        """
        MM: Obtenemos la lista de reglas salariales
        :param employee_id:
        :return: list
        """
        res = []
        contract = self.contract_id or contract
        rule_ids = self.env['hr.payroll.structure'].browse(self.struct_id.id or (struct and struct.id)).get_all_rules()
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
        inputs = self.env['hr.salary.rule'].browse(sorted_rule_ids).mapped('input_ids')
        for input in inputs:
            input_data = {
                'contract_id': contract.id,
                'name': input.name,
                'code': input.code,
            }
            res += [input_data]
        return res

    def _get_number_absences(self, employee=None, df=None, dt=None):
        """
        TODO: Obtenemos los días de ausencias por período
        Soló las marcadas en el sistema cómo Reportadas en nómina y relacionadas al empleado
        :param df:
        :param dt:
        :return int:
        """
        arg = []
        arg.append(('state', '=', 'validate'))
        arg.append(('holiday_type', '=', 'employee'))
        arg.append(('date_from', '>=', df))
        arg.append(('date_from', '<=', dt))
        arg.append(('payslip_status', '=', True))
        arg.append(('employee_id', '=', employee.id))
        absences = self.env['hr.leave'].search(arg)
        return sum(line.number_of_days for line in absences)

    def _check_employee_payslip(self, id, date_from, date_to):
        sql = "" \
              "SELECT id FROM hr_payslip WHERE employee_id = %s" \
              "AND state = 'done' AND date_from BETWEEN '%s' AND '%s' LIMIT 1;" % (id, date_from, date_to)
        self.env.cr.execute(sql)
        result = self.env.cr.fetchone()
        if result:
            return True
        else:
            return False

    @staticmethod
    def _get_date_from(date_from, date_start):
        if not date_start:
            return date_from
        if (date_from.year == date_start.year) and (date_from.month == date_start.month):
            return date_start
        else:
            return date_from

    @staticmethod
    def _get_worked_days(date_to, date_from):
        days = abs(date_to - date_from).days + 1
        if days == 31 or (date_to.month == 2 and days == 28):
            days = 30
        return days

    @api.onchange('date_from')
    def onchange_date_from(self):
        if self.date_from:
            self.date_to = self.date_from.replace(day=calendar.monthrange(self.date_from.year, self.date_from.month)[1])

    @api.multi
    def onchange_employee_id(self, date_from, date_to, employee_id=False, contract_id=False):
        """
        MM
        :param date_from:
        :param date_to:
        :param employee_id:
        :param contract_id:
        :return:
        """
        res = {
            'value': {
                'line_ids': [],
                'input_line_ids': [(2, x,) for x in self.input_line_ids.ids],
                'worked_days': 0,
                'number_absences': 0,
                'name': '',
                'contract_id': False,
                'struct_id': False,
            }
        }
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        employee = self.env['hr.employee'].browse(employee_id)
        date_from = self._get_date_from(date_from, contract_id.date_start)
        name_date = self.env['res.function']._get_period_string(date_from)
        res['value'].update({
            'date_from': date_from,
            'name': _('Rol de %s por %s') % (employee.name, name_date),
            'company_id': employee.company_id.id,
        })

        if not contract_id:
            return res
        res['value'].update({
            'contract_id': contract_id.id
        })
        struct = contract_id.struct_id
        if not struct:
            return res
        res['value'].update({
            'struct_id': struct.id,
        })
        worked_days = self._get_worked_days(date_from, date_to)
        number_absences = self._get_number_absences(employee, date_from, self.date_to)
        input_line_ids = self.get_inputs(contract_id, struct)
        res['value'].update({
            'worked_days': worked_days,
            'number_absences': number_absences,
            'input_line_ids': input_line_ids,
        })
        return res

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):
        """
        MM: Cálculo de ingresos, egresos y provisiones
        """
        res = {}
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return res

        employee = self.employee_id
        contract = employee.contract_id
        self.date_from = self._get_date_from(self.date_from, contract.date_start)
        date_from = self.date_from

        if not contract:
            res['warning'] = {'title': _('Advertencia'), 'message': _(
                'Empleado %s no tiene contrato activo en sistema.') % employee.name}
            return res

        if self._check_employee_payslip(employee.id, date_from, self.date_to):
            res['warning'] = {'title': _('Advertencia'), 'message': _(
                'Empleado %s ya tiene un rol (realizado) en rango de fechas!') % employee.name}
            return res

        name_date = self.env['res.function']._get_period_string(date_from)
        self.name = 'Rol de %s por %s' % (
            employee.name, name_date)
        self.company_id = employee.company_id
        self.contract_id = contract.id
        self.struct_id = contract.struct_id
        self.worked_days = self._get_worked_days(self.date_to, date_from)
        self.number_absences = self._get_number_absences(employee, date_from, self.date_to)
        # Obtenemos todos las reglas salariales a calcular
        input_line_ids = self.get_inputs()
        # Vacíamos las líneas para nuevo cálculo
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines
        return

    @api.constrains('worked_days')
    def _check_worked_days(self):
        if self.worked_days > 30:
            raise ValidationError(_('No puede haber más de 30 días trabajados en período!'))

    @api.depends('date_from', 'date_to', 'employee_id.days_service', 'employee_id.months_service',
                 'employee_id.years_service')
    def _get_number_of_months(self):
        today = fields.Date.today()
        for slip in self:
            employee = slip.employee_id
            days_service = employee.days_service + (employee.months_service * 30) + (employee.years_service * 360)
            days = days_service + (slip.date_to - today).days + 1
            # TODO: Ver la forma de mejorar
            slip.number_of_months = int(days / 30)
            if slip.number_of_months >= 12:
                days = days - 360
                slip.payment_days_reserve_funds = 30 if days > 30 else days
            else:
                slip.payment_days_reserve_funds = 0

    @api.model
    def _default_journal_id(self):
        journal_payroll = self.env.user.company_id.default_journal_payroll_id
        return journal_payroll.id if journal_payroll else False

    @api.multi
    def action_payslip_posted(self):
        precision = self.env['decimal.precision'].precision_get('Payroll')
        context = dict(self._context or {})
        ref = context.get('ref', False)
        for slip in self:
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            date = slip.date or slip.date_to
            name = _('Nómina de %s') % slip.employee_id.name
            number = slip._get_name()
            move_dict = {
                'narration': name,
                'ref': number + ": " + ref or name,
                'journal_id': slip.journal_id.id,
                'date': date,
            }
            for line in slip.details_by_salary_rule_category:
                amount = slip.credit_note and -line.total or line.total
                if float_is_zero(amount, precision_digits=precision):
                    continue
                debit_account_id = line.salary_rule_id.account_debit.id
                credit_account_id = line.salary_rule_id.account_credit.id

                if debit_account_id:
                    debit_line = (0, 0, {
                        'name': line.name + ' / ' + slip.employee_id.name,
                        'partner_id': line._get_partner_id(),
                        'account_id': debit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amount > 0.0 and amount or 0.0,
                        'credit': amount < 0.0 and -amount or 0.0,
                        'tax_line_id': line.salary_rule_id.account_tax_id.id,
                    })
                    line_ids.append(debit_line)
                    debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if credit_account_id:
                    credit_line = (0, 0, {
                        'name': line.name + ' / ' + slip.employee_id.name,
                        'partner_id': line._get_partner_id(),
                        'account_id': credit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amount < 0.0 and -amount or 0.0,
                        'credit': amount > 0.0 and amount or 0.0,
                        'tax_line_id': line.salary_rule_id.account_tax_id.id,
                    })
                    line_ids.append(credit_line)
                    credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

            if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                acc_id = slip.journal_id.default_credit_account_id.id
                if not acc_id:
                    raise UserError(_('En el diario %s no se ha configurado cuenta de crédito!') % (
                        slip.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('LÍNEA DE AJUSTE (CRÉDITO)'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': 0.0,
                    'credit': debit_sum - credit_sum,
                })
                line_ids.append(adjust_credit)

            elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                acc_id = slip.journal_id.default_debit_account_id.id
                if not acc_id:
                    raise UserError(_('En el diario %s no se ha configurado cuenta de débito!') % (
                        slip.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('LÍNEA DE AJUSTE (DÉBITO)'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': credit_sum - debit_sum,
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)
            move_dict['line_ids'] = line_ids
            move = self.env['account.move'].create(move_dict)
            slip.write({'move_id': move.id, 'date': date, 'state': 'done', 'number': number})
            move.post()
        return True

    @api.onchange('contract_id')
    def onchange_contract(self):
        """
        MM
        :return:
        """
        pass

    @api.model
    def _default_wage(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'contract.minimum_wage',
            default=394
        )

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_amount_advance(self):
        model = self.env['hr.salary.advance.line']
        for slip in self:
            date_from = slip._get_date_from(slip.date_from, slip.contract_id.date_start)
            advance_ids = model.search([
                ('parent_state', '=', 'posted'),
                ('employee_id', '=', slip.employee_id.id),
                ('advanced_id.date', '>=', date_from),
                ('advanced_id.date', '<=', slip.date_to)
            ])
            slip.amount_advance = round(sum(line.amount_advance for line in advance_ids), 2)

    worked_days = fields.Integer(string="Días trabajados", default=30, required=True,
                                 readonly=True, states={'draft': [('readonly', False)]})
    number_absences = fields.Integer(string="Nº de ausencias", default=0, readonly=True,
                                     states={'draft': [('readonly', False)]},
                                     help="Al calcular rol el sistema traerá las ausencias reportadas para descuento en el período seleccionado.")
    minimum_wage = fields.Float('SBU', help="Técnico: Sirve para calcular el décimo cuarto.",
                                readonly=True, default=_default_wage)
    number_of_months = fields.Integer('Meses de servicio', compute='_get_number_of_months')
    payment_days_reserve_funds = fields.Integer('Días fondo de reserva', compute='_get_number_of_months',
                                                help="Técnico: Días para cálculo de fondos de reserva.")
    amount_advance = fields.Float('Monto de avance', compute='_compute_amount_advance')
    net_receive = fields.Float('Neto a recibir', compute='_compute_net_receive', store=True,
                               track_visibility='onchange')
    journal_id = fields.Many2one(default=_default_journal_id)  # CM
    approval_user = fields.Many2one('res.users', 'Aprobado por', related='payslip_run_id.approval_user')
    comment = fields.Text('Notas y comentarios', track_visibility='onchange')
