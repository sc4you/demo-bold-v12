# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import UserError
from itertools import groupby
from operator import itemgetter

NOT = ['parents', 'brothers', 'others']


class Employee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _get_family_burden(self):
        family_burden = self.family_burden_ids.filtered(lambda x: x.receive_profits)
        return len(family_burden)


class FamilyBurden(models.Model):
    _inherit = 'hr.employee.family.burden'

    @api.multi
    @api.depends('age', 'relationship', 'disability')
    def _compute_receive_profits(self):
        for record in self:
            if record.relationship in NOT:
                continue
            if record.relationship == 'spouse':
                record.receive_profits = True
            elif record.disability or (record.age < 18):
                record.receive_profits = True

    receive_profits = fields.Boolean('Recibe utilidades', compute='_compute_receive_profits',
                                     help="Técnico: Específica si carga se otorga utilidades.")


class PayrollUtilityLine(models.Model):
    _name = 'hr.payroll.utility.line'
    _description = _('Línea de utilidad de nómina')

    @api.multi
    def unlink(self):
        for line in self:
            if line.parent_state != 'draft':
                raise UserError(_("No podemos borrar líneas diferentes de borrador."))
        return super(PayrollUtilityLine, self).unlink()

    @api.depends('payroll_utility_id.state')
    def _compute_parent_state(self):
        for record in self.filtered('payroll_utility_id'):
            record.parent_state = record.payroll_utility_id.state

    @api.multi
    @api.depends('amount_ten', 'amount_five')
    def _compute_amount(self):
        for record in self:
            amount = record.amount_ten + record.amount_five
            record.amount = amount

    name = fields.Many2one('hr.employee', string='Empleado')
    family_burden = fields.Integer('Cargas familiares')
    days_worked = fields.Integer('Días trabajados')
    amount_ten = fields.Float(string='Monto 10% calculado')
    amount_five = fields.Float(string='Monto 5% calculado')
    amount = fields.Float(string='Monto a recibir', compute='_compute_amount', store=True)
    reconciled = fields.Boolean('Pagado', default=False, help="Indica si la línea se encuentra pagada.")
    parent_state = fields.Selection([('draft', 'Borrador'),
                                     ('validate', 'Validado'),
                                     ('cancel', 'Anulado')],
                                    string='Estado del padre', compute='_compute_parent_state')
    payroll_utility_id = fields.Many2one('hr.payroll.utility', string='Utilidad de nómina', ondelete="cascade")


class PayrollUtility(models.Model):
    _name = 'hr.payroll.utility'
    _inherit = ['mail.thread']
    _description = _('Utilidad de nómina')
    _order = 'date'

    @api.one
    @api.depends('line_ids.reconciled')
    def _compute_reconciled(self):
        if not self.line_ids:
            return
        self.reconciled = all(l.reconciled for l in self.line_ids)

    def _default_date_from(self):
        today = datetime.today().date()
        return date(month=1, day=1, year=today.year)

    def _default_date_to(self):
        today = datetime.today().date()
        return date(month=12, day=31, year=today.year)

    @api.onchange('date_from')
    def _onchange_date_from(self):
        if self.date_from:
            self.date_to = date(month=12, day=31, year=self.date_from.year)

    @api.multi
    def action_validate(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("No existen líneas de empleados."))
        self.write({'state': 'validate'})

    @api.multi
    def action_cancel(self):
        if self.filtered(lambda a: a.reconciled):
            raise UserError(_('No se puede anular registro pagado totalmente.'))
        self.write({'state': 'cancel'})

    @api.multi
    def unlink(self):
        if self.filtered(lambda a: a.state != 'draft'):
            raise UserError(_("No se puede eliminar una registro diferente a estado borrador."))
        return super(PayrollUtility, self).unlink()

    @api.one
    @api.depends('line_ids')
    def _compute_lines(self):
        total_days_worked = 0
        total_days_family_burden = 0
        for line in self.line_ids:
            total_days_family_burden += line.family_burden * line.days_worked
            total_days_worked += line.days_worked
        self.total_days_family_burden = total_days_family_burden
        self.total_days_worked = total_days_worked

    # Actions

    def _get_domain(self):
        domain = []
        domain.append(('date_from', '>=', self.date_from))
        domain.append(('date_to', '<=', self.date_to))
        domain.append(('state', '=', 'done'))
        return domain

    @api.multi
    def action_charge(self):
        """
        Cargamos líneas para posterior cálculo
        :return:
        """
        self.ensure_one()
        self.line_ids.unlink()
        line_ids = []
        payslip_ids = self.env['hr.payslip'].search(self._get_domain())
        for employee, slip_ids in groupby(payslip_ids, key=itemgetter('employee_id')):
            days_worked = sum(line.worked_days for line in slip_ids)
            line_ids.append([0, 0, {
                'name': employee.id,
                'family_burden': employee._get_family_burden(),
                'days_worked': days_worked,
            }])
        return self.write({'line_ids': line_ids})

    @api.multi
    def action_calculate(self):
        """
        Calculamos el monto a pagar para el
        10% y 5% de cada una de las líneas.
        :return:
        """
        self.ensure_one()
        amount_ten = (self.amount_utility * self.percentage_employee) / 100
        amount_five = (self.amount_utility * self.percentage_family_burden) / 100
        # Si no existen cargas familiares se suma ese procentaje
        # a los 10 %.
        if self.total_days_family_burden <= 0:
            amount_ten = amount_ten + amount_five
            amount_five = 0
        for line in self.line_ids:
            values = dict()
            amount_line_ten = (amount_ten * line.days_worked) / self.total_days_worked
            amount_line_five = (amount_five * line.family_burden * line.days_worked) / self.total_days_family_burden
            values['amount_ten'] = amount_line_ten
            values['amount_five'] = amount_line_five
            line.update(values)
        return True

    name = fields.Char(string='Referencia', required=True, index=True, readonly=True,
                       states={'draft': [('readonly', False)]})
    date = fields.Date(string='Fecha contable', required=True, readonly=True, default=fields.Date.context_today,
                       states={'draft': [('readonly', False)]}, track_visibility='onchange')
    date_from = fields.Date(string='Fecha inicio', readonly=True, required=True,
                            states={'draft': [('readonly', False)]}, default=_default_date_from)
    date_to = fields.Date(string='Fecha fin', readonly=True, required=True,
                          states={'draft': [('readonly', False)]}, default=_default_date_to)
    line_ids = fields.One2many('hr.payroll.utility.line', 'payroll_utility_id', string='Líneas de empleados')
    state = fields.Selection([('draft', 'Borrador'),
                              ('validate', 'Validado'),
                              ('cancel', 'Anulado')],
                             string='Estado', default='draft', track_visibility='always')
    percentage_employee = fields.Integer('Porcentaje empleados', default=10, required=True, readonly=True,
                                         states={'draft': [('readonly', False)]})
    percentage_family_burden = fields.Integer('Porcentaje cargas familiares', default=5, required=True, readonly=True,
                                              states={'draft': [('readonly', False)]})
    amount_utility = fields.Float(string="Monto de utilidad", readonly=True, required=True,
                                  states={'draft': [('readonly', False)]})
    total_days_worked = fields.Integer(string="Total de días trabajados", compute='_compute_lines',
                                       help="Días trabajados por todos los empleados en período.")
    total_days_family_burden = fields.Integer(string="Total de días cargas familiares", compute='_compute_lines',
                                              help="Calcula el total de cargas familiares por el total de días trabajados.")
    reconciled = fields.Boolean(string='Pagado', store=True, readonly=True, compute='_compute_reconciled',
                                help="Técnico: Indica si el documento está completamente pagado.")
