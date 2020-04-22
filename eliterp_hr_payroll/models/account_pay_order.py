# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import UserError

class EmployeeOrderLine(models.Model):
    _name = 'account.employee.order.line'
    _description = _('Línea de empleado en orden de pago')

    name = fields.Many2one('hr.employee', 'Nombre de empleado')
    amount = fields.Float('Monto')
    pay_order_id = fields.Many2one('account.pay.order', 'Orden de pago', ondelete="cascade")
    pay_order_salary_advance_line_id = fields.Many2one('hr.salary.advance.line', 'Línea de empleado',
                                                       ondelete="cascade",
                                                       index=True,
                                                       readonly=True)
    pay_order_payslip_run_line_id = fields.Many2one('hr.payslip', 'Línea de empleado',
                                                    ondelete="cascade",
                                                    index=True,
                                                    readonly=True)


class PayOrder(models.Model):
    _inherit = 'account.pay.order'

    def _get_vals_document(self, active_model, active_ids):
        """
        :return dict:
        """
        vals = super(PayOrder, self)._get_vals_document(active_model, active_ids)
        if active_model == 'hr.salary.advance':
            salary_advance = self.env['hr.salary.advance'].browse(active_ids)[0]
            vals.update({
                'date': salary_advance.date,
                'default_date': salary_advance.date,
                'type': 'salary advance',
                'amount': salary_advance.total_pay_order,
                'default_amount': salary_advance.total_pay_order,
                'origin': salary_advance.name,
                'salary_advance_id': salary_advance.id,
                'company_id': self.env.user.company_id.id,
                'beneficiary': '/'
            })
        if active_model == 'hr.payslip.run':
            payslip_run = self.env['hr.payslip.run'].browse(active_ids)[0]
            vals.update({
                'date': payslip_run.date_end,
                'default_date': payslip_run.date_end,
                'type': 'payslip run',
                'amount': payslip_run.total_pay_order,
                'default_amount': payslip_run.total_pay_order,
                'origin': payslip_run.name,
                'payslip_run_id': payslip_run.id,
                'company_id': self.env.user.company_id.id,
                'beneficiary': '/'
            })
        return vals

    @api.model
    def create(self, vals):
        res = super(PayOrder, self).create(vals)
        if res.type in ['salary advance', 'payslip run']:
            if res.salary_advance_id:
                employees = self._salary_advance_employee_ids(res.salary_advance_id)
                res['employee_ids'] = employees

            else:
                employees = self._pasylip_run_employee_ids(res.payslip_run_id)
                res['employee_ids'] = employees
            if len(employees) == 1:
                employee = self.env['hr.employee'].browse(employees[0][2]['name'])
                res['beneficiary'] = employee.name
            else:
                if res.type == 'salary advance':
                    res['beneficiary'] = _("Quincena %s") % res.salary_advance_id.period
                else:
                    res['beneficiary'] = _("Fin de mes %s") % res.payslip_run_id.name
        return res

    def _salary_advance_employee_ids(self, salary_advance):
        employees = []
        for line in salary_advance.line_ids:
            if line.selected and not line.reconciled:
                employees.append([0, 0, {'name': line.employee_id.id,
                                         'amount': line.amount_payable,
                                         'pay_order_salary_advance_line_id': line.id}])
                line.update(
                    {'selected': False, 'amount_payable': 0})  # Le quitamos la selección y colocamos monto a pagar en 0
        return employees

    def _pasylip_run_employee_ids(self, pasylip_run):
        employees = []
        for line in pasylip_run.slip_ids:
            if line.selected and not line.reconciled:
                employees.append([0, 0, {'name': line.employee_id.id,
                                         'amount': line.amount_payable,
                                         'pay_order_payslip_run_line_id': line.id}])
                line.update(
                    {'selected': False, 'amount_payable': 0})  # Le quitamos la selección y colocamos monto a pagar en 0
        return employees

    type = fields.Selection(
        selection_add=[('salary advance', 'Anticipo de quincena'), ('payslip run', 'Rol consolidado')])
    salary_advance_id = fields.Many2one('hr.salary.advance', 'Anticipo de quincena')
    payslip_run_id = fields.Many2one('hr.payslip.run', 'Rol consolidado')
    employee_ids = fields.One2many('account.employee.order.line', 'pay_order_id', string='Empleados')


class Payment(models.Model):
    _inherit = 'account.payment'

    @api.multi
    def data_salary_advance(self):
        salary_advance = self.pay_order_id.salary_advance_id
        account = salary_advance.company_id.default_account_payroll_id
        if not account:
            raise  UserError(_("No tiene cuenta para pagar nómina por defecto!"))
        list_accounts = []
        if account:
            list_accounts.append([0, 0, {'account_id': account.id,
                                         'amount': self.amount,
                                         }])
        return self.update({
            'account_ids': list_accounts,
            'beneficiary': self.pay_order_id.beneficiary,
            'communication': salary_advance.name
        })

    @api.multi
    def data_payslip_run(self):
        payslip_run_id = self.pay_order_id.payslip_run_id
        account = payslip_run_id.company_id.default_account_payroll_id
        if not account:
            raise UserError(_("No tiene cuenta para pagar nómina por defecto!"))
        list_accounts = []

        for line in self.pay_order_id.employee_ids:
            list_accounts.append([0, 0, {
                'partner_id': line.name.address_home_id.id,
                'account_id': account.id,
                'amount': line.amount,
            }])
        return self.update({
            'account_ids': list_accounts,
            'beneficiary': self.pay_order_id.beneficiary,
            'communication': payslip_run_id.name
        })

    @api.onchange('pay_order_id')
    def _onchange_pay_order_id(self):
        if self.type_pay_order == 'salary advance':
            self.data_salary_advance()
        if self.type_pay_order == 'payslip run':
            self.data_payslip_run()
        return super(Payment, self)._onchange_pay_order_id()
