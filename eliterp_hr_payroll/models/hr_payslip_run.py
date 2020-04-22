# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class Payslip(models.Model):
    _inherit = 'hr.payslip'

    @api.depends('payslip_run_id.state', 'pay_order_ids.pay_order_id.state', 'pay_order_ids.amount')
    def _compute_amount(self):
        for record in self:
            record.paid_amount = sum(
                line.amount for line in record.pay_order_ids.filtered(lambda p: p.pay_order_id.state == 'paid'))
            record.residual = record.net_receive - record.paid_amount
            if record.pay_order_ids and float_is_zero(record.residual, precision_rounding=0.01):
                record.reconciled = True
            else:
                record.reconciled = False

    @api.depends('payslip_run_id')
    def _compute_parent_state(self):
        for record in self.filtered('payslip_run_id'):
            record.parent_state = record.payslip_run_id.state

    @api.one
    @api.constrains('amount_payable')
    def _check_amount_payable(self):
        if self.amount_payable > self.residual:
            raise ValidationError(_("Monto a pagar (%.2f) mayor al saldo (%.2f) para %s.") % (
                self.amount_payable, self.residual, self.employee_id.name
            ))

    @api.onchange('selected')
    def _onchange_selected(self):
        if self.selected:
            self.amount_payable = self.residual

    @api.multi
    def action_view_slip(self):
        self.ensure_one()
        view_id = self.env.ref('eliterp_hr_payroll.view_form_payslip').id
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.payslip',
            'res_id': self.id,
            'view_id': view_id,
            'context': {},
        }

    parent_state = fields.Char(compute="_compute_parent_state", string="Estado de rol")
    selected = fields.Boolean('Seleccionar', default=False)
    reconciled = fields.Boolean('Conciliado', compute='_compute_amount', store=True)
    paid_amount = fields.Float('Pagado', compute='_compute_amount', store=True)
    residual = fields.Float('Saldo', compute='_compute_amount', store=True)
    amount_payable = fields.Float('A pagar')
    pay_order_ids = fields.One2many('account.employee.order.line', 'pay_order_payslip_run_line_id',
                                    string="Líneas de ordenes de pago",
                                    readonly=True,
                                    copy=False)


class PayslipRun(models.Model):
    _name = 'hr.payslip.run'
    _order = 'date_start desc'
    _inherit = ['hr.payslip.run', 'mail.thread']

    @api.multi
    def print_payslip_run_pay(self):
        self.ensure_one()
        return self.env.ref('eliterp_hr_payroll.action_report_payslip_run_pay').report_action(self)

    @api.multi
    def print_payslip_run(self):
        return self.env.ref('eliterp_hr_payroll.action_report_payslip_run').report_action(self)

    @api.multi
    def to_approve(self):
        self.ensure_one()
        if not self.slip_ids:
            raise UserError(_("No hay líneas de rol en período creadas en el sistema!"))
        return self.write({'state': 'to_approve'})

    @api.multi
    def action_approve(self):
        self.ensure_one()
        return self.write({'state': 'approve', 'approval_user': self._uid})

    @api.one
    def confirm_payslip_run(self):
        self.slip_ids.with_context(ref=self.name).action_payslip_posted()
        return self.write({'state': 'closed'})

    @api.multi
    def unlink(self):
        if self.filtered(lambda p: p.state != 'draft'):
            raise ValidationError(_("No podemos borrar rol consolidado diferente de borrador."))
        return super(PayslipRun, self).unlink()

    def _get_domain(self):
        domain = []
        return domain

    @api.multi
    def action_compute_roles(self):
        self.ensure_one()
        payslips = self.env['hr.payslip']
        self.slip_ids.unlink()
        for employee in self.env['hr.employee'].search(self._get_domain()):
            contract = employee.contract_id
            if contract.state_customize != 'active':
                continue
            slip_data = self.env['hr.payslip'].onchange_employee_id(self.date_start, self.date_end, employee.id,
                                                                    contract)
            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'struct_id': slip_data['value'].get('struct_id'),
                'contract_id': slip_data['value'].get('contract_id'),
                'payslip_run_id': self.id,
                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                'worked_days': slip_data['value'].get('worked_days'),
                'number_absences': slip_data['value'].get('number_absences'),
                'date_from': slip_data['value'].get('date_from'),
                'date_to': self.date_end,
                'company_id': employee.company_id.id,
            }
            payslips += self.env['hr.payslip'].create(res)
        payslips.compute_sheet()

    @api.one
    @api.depends('slip_ids.net_receive')
    def _compute_amount_total(self):
        self.amount_total = sum(line.net_receive for line in self.slip_ids)
        self.count_employees = len(self.slip_ids)

    @api.multi
    def action_deny(self):
        return self.write({'state': 'deny'})

    @api.onchange('date_start')
    def _onchange_date_start(self):
        if self.date_start:
            self.name = _("Rol de ") + self.env['res.function']._get_period_string(self.date_start)

    @api.model
    def _default_journal_id(self):
        journal_payroll = self.env.user.company_id.default_journal_payroll_id
        return journal_payroll.id if journal_payroll else False

    journal_id = fields.Many2one(default=_default_journal_id)
    slip_ids = fields.One2many('hr.payslip', 'payslip_run_id', string='Roles', readonly=False)  # CM
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('to_approve', 'Por aprobar'),
        ('approve', 'Aprobado'),
        ('closed', 'Cerrado'),
        ('deny', 'Negado')
    ], string='Estado', index=True, readonly=True, copy=False, default='draft', track_visibility='onchange')  # CM
    amount_total = fields.Float('Total de rol', compute='_compute_amount_total', store=True,
                                track_visibility='onchange')
    count_employees = fields.Integer('No. Empleados', compute='_compute_amount_total')
    approval_user = fields.Many2one('res.users', 'Aprobado por', copy=False, track_visibility='onchange')
    comment = fields.Text('Notas y comentarios')
    company_id = fields.Many2one('res.company', string="Compañía", default=lambda self: self.env.user.company_id)

    # Ordenes de pago
    @api.one
    @api.depends('pay_order_line.state', 'state')
    def _compute_customize_amount(self):
        pays = self.pay_order_line.filtered(lambda x: x.state == 'paid')
        if not pays:
            self.state_pay_order = 'no credits'
            self.residual_pay_order = self.amount_total
        else:
            self.improved_pay_order = round(sum(pay.amount for pay in pays), 2)
            self.residual_pay_order = round(self.amount_total - self.improved_pay_order, 2)
            if float_is_zero(self.residual_pay_order, precision_rounding=0.01):
                self.state_pay_order = 'paid'
            else:
                self.state_pay_order = 'partial_payment'

    @api.depends('pay_order_line')
    def _compute_pay_orders(self):
        object = self.env['account.pay.order']
        for record in self:
            pays = object.search([('payslip_run_id', '=', record.id)])
            record.pay_order_line = pays
            record.pay_orders_count = len(pays)

    @api.multi
    def action_view_pay_orders(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('eliterp_payment.action_pay_order')
        list_view_id = imd.xmlid_to_res_id('eliterp_payment.view_tree_pay_order')
        form_view_id = imd.xmlid_to_res_id('eliterp_payment.view_form_pay_order')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(self.pay_order_line) > 1:
            result['domain'] = "[('id','in',%s)]" % self.pay_order_line.ids
        elif len(self.pay_order_line) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = self.pay_order_line.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result

    @api.one
    @api.depends('slip_ids.selected')
    def _compute_total_pay_order(self):
        total = sum(line.amount_payable for line in self.slip_ids.filtered(lambda l: l.selected and not l.reconciled))
        self.total_pay_order = round(total, 2)

    state_pay_order = fields.Selection([
        ('no credits', 'Sin abonos'),
        ('partial_payment', 'Abono parcial'),
        ('paid', 'Pagado'),
    ], string="Estado de pago", compute='_compute_customize_amount', readonly=True, copy=False,
        store=True)
    improved_pay_order = fields.Float('(-) Abonado', compute='_compute_customize_amount', store=True)
    residual_pay_order = fields.Float('Saldo', compute='_compute_customize_amount', store=True)
    pay_order_line = fields.One2many('account.pay.order', 'payslip_run_id', string='Órdenes de pago', store=True)
    pay_orders_count = fields.Integer('# Ordenes de pago', compute='_compute_pay_orders', store=True)
    total_pay_order = fields.Float('Total a pagar', compute='_compute_total_pay_order')
