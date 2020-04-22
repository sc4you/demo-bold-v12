# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


class Employee(models.Model):
    _inherit = 'hr.employee'

    def _compute_contract_id(self):
        """
        MM: Obtenemos el último contrato activo
        :return:
        """
        Contract = self.env['hr.contract']
        for employee in self:
            employee.contract_id = Contract.search(
                [('employee_id', '=', employee.id), ('state_customize', '=', 'active')], order='date_start desc',
                limit=1)


class ContractType(models.Model):
    _inherit = 'hr.contract.type'

    halftime = fields.Boolean('Medio tiempo', default=False,
                              help='Técnico: Saber si tipo de contrato es medio tiempo.')


class Contract(models.Model):
    _inherit = 'hr.contract'

    @api.constrains('employee_id')
    def _check_employee_id(self):
        """
        Validamos qué empleado no tenga contrato activo
        :return:
        """
        contract = self.employee_id.contract_id
        if contract and contract.state_customize == 'active':
            raise ValidationError(_("Empleado %s tiene contrato activo en sistema.") % self.employee_id.name)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """
        ME: Traemos la fecha de ingreso si contrato no está finalizado
        """
        res = super(Contract, self)._onchange_employee_id()
        self.date_start = self.employee_id.admission_date
        return res

    @api.depends('date_start')
    def _compute_antiquity(self):
        """
        Obtenemos los días de antiguedad del empleado por contrato
        :return:
        """
        for record in self:
            end_date = record.date_start + timedelta(days=record.days_for_trial)
            record.antiquity = abs(end_date - record.date_start).days

    @api.depends('date_start')
    def _compute_days_for_trial(self):
        """
        Contador de los días de prueba
        :return:
        """
        for contract in self:
            if not contract.date_start:
                continue
            if contract.days_for_trial == contract.test_days:
                result = contract.test_days
            else:
                days = abs(fields.Date.today() - contract.date_start).days
                result = days
            contract.days_for_trial = result

    @api.onchange('is_trial', 'date_start')
    def _onchange_is_trial(self):
        """
        Colocamos las fechas de inicio y fin al cambiar campo Es período de prueba?
        :return:
        """
        if self.is_trial and self.date_start:
            self.trial_date_start = self.date_start
            self.trial_date_end = self.date_start + relativedelta(days=+ self.test_days)

    @api.depends('days_for_trial')
    def _compute_end_trial(self):
        """
        Si contador de días es mayor 90 días terminó pruebas
        :return:
        """
        if self.days_for_trial >= 90:
            self.end_trial = True

    def _get_name(self):
        company = self.company_id
        sequence = self.env['ir.sequence'].with_context(force_company=company.id).next_by_code('hr.contract')
        if not sequence:
            raise UserError(
                _("No está definida la secuencia con código 'hr.contract' para compañía: %s") % company.name)
        return sequence

    @api.multi
    def active_contract(self):
        """
        Activamos contrato con fecha de ingreso de empleado y secuencia
        :return:
        """
        self.ensure_one()
        new_name = self._get_name().split('/')
        return self.write({
            'name': new_name[0] + "/" + new_name[1] + "/" + new_name[2] + "/" + str(self.employee_id.id),
            'state_customize': 'active'
        })

    @api.multi
    def print_contract(self):
        return self.env.ref('eliterp_hr_contract.action_report_contract').report_action(self)

    @api.multi
    def unlink(self):
        if self.filtered(lambda c: c.state_customize != 'draft'):
            raise ValidationError(_("No se puede borrar contratos activos o finalizados!"))
        return super(Contract, self).unlink()

    @api.multi
    def finalized_contract(self):
        self.ensure_one()
        if not self.date_end:
            raise ValidationError(_("Debe colocar fecha de finalización de contrato!"))
        return self.write({'state_customize': 'finalized'})

    @api.model
    def _default_wage(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'contract.minimum_wage',
            default=394
        )

    name = fields.Char('Nº de documento', required=False, copy=False, track_visibility="onchange")  # CM
    test_days = fields.Integer('Días de prueba')  # Configuración RRHH
    # TODO: Antiguedad hacer cómo en empleado
    antiquity = fields.Integer('Antiguedad (días)', compute='_compute_antiquity', store=True)
    is_trial = fields.Boolean('Es período de prueba')
    end_trial = fields.Boolean(compute='_compute_end_trial', string='Finalizó prueba', default=False)
    trial_date_start = fields.Date('Fecha inicio prueba')
    days_for_trial = fields.Integer('Días de prueba', compute='_compute_days_for_trial')
    state = fields.Selection(track_visibility=None)  # CM
    state_customize = fields.Selection([
        ('draft', 'Nuevo'),
        ('active', 'Activo'),
        ('finalized', 'Finalizado')
    ], 'Estado', default='draft', track_visibility="onchange")
    wage = fields.Monetary('Wage', digits=(16, 2), required=True, track_visibility="onchange",
                           help="Salario bruto mensual del empleado.", default=_default_wage)  # CM, Configuración RRHH
