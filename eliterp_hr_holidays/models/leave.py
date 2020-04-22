# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


class LeaveType(models.Model):
    _inherit = 'hr.leave.type'

    description = fields.Char('Descripción')
    time_type = fields.Selection([('leave', 'Ausencia'), ('vacation', 'Vacaciones')], default='leave',
                                 string="Clase de ausencia")  # CM


class VacationLine(models.Model):
    _name = 'hr.vacation.line'
    _description = _('Línea de vacación')

    employee_id = fields.Many2one('hr.employee', string='Empleado')
    name = fields.Char('Período')
    vacations_generated = fields.Integer('Generadas')
    vacations_taken = fields.Integer('Gozadas')
    vacations_available = fields.Integer('Por gozar')
    holiday_id = fields.Many2one('hr.leave', 'De', ondelete="cascade")


class Employee(models.Model):
    _inherit = 'hr.employee'

    @api.multi
    def _compute_leave_status(self):
        """
        MM: Se modificó por qué se cambio de horas a fechas
        :return:
        """
        # Used SUPERUSER_ID to forcefully get status of other user's leave, to bypass record rule
        holidays = self.env['hr.leave'].sudo().search([
            ('employee_id', 'in', self.ids),
            ('date_from', '<=', fields.Date.today()),
            ('date_to', '>=', fields.Date.today()),
            ('state', 'not in', ('cancel', 'refuse'))
        ])
        leave_data = {}
        for holiday in holidays:
            leave_data[holiday.employee_id.id] = {}
            leave_data[holiday.employee_id.id]['leave_date_from'] = holiday.date_from
            leave_data[holiday.employee_id.id]['leave_date_to'] = holiday.date_to
            leave_data[holiday.employee_id.id]['current_leave_state'] = holiday.state
            leave_data[holiday.employee_id.id]['current_leave_id'] = holiday.holiday_status_id.id

        for employee in self:
            employee.leave_date_from = leave_data.get(employee.id, {}).get('leave_date_from')
            employee.leave_date_to = leave_data.get(employee.id, {}).get('leave_date_to')
            employee.current_leave_state = leave_data.get(employee.id, {}).get('current_leave_state')
            employee.current_leave_id = leave_data.get(employee.id, {}).get('current_leave_id')

    @api.one
    def _compute_days_taken(self):
        """
        Calculamos los días tomados de vacaciones por empleado
        :return:
        """
        for record in self:
            leave_type = self.env['hr.leave.type'].search([('time_type', '=', 'vacation')])
            # Solo clase de ausencia 'vacaciones'
            holidays = self.env['hr.leave'].search([
                ('employee_id', '=', record.id),
                ('holiday_status_id', 'in', leave_type._ids),
                ('state', '=', 'validate')
            ])
            days_taken = 0
            for line in holidays:
                if line.holiday_type == 'employee':
                    days_taken += line.number_of_days
                else:  # TODO: Vacaciones por etiqueta de empleado (Revisar)
                    for line in line.category_id.line_employe_category:
                        if line.employee_id == record.id:
                            days_taken += line.number_of_days
            self.days_taken = days_taken

    days_taken = fields.Integer('Días tomados', compute='_compute_days_taken')


class Leave(models.Model):
    _name = 'hr.leave'
    _inherit = "hr.leave"
    _order = "employee_id asc, date_from desc"

    @api.constrains('date_from', 'date_to')
    def _check_date(self):
        """
        MM
        :return:
        """
        for holiday in self:
            domain = [
                ('date_from', '>=', holiday.date_from),
                ('date_from', '<=', holiday.date_from),
                ('employee_id', '=', holiday.employee_id.id),
                ('id', '!=', holiday.id),
                ('state', 'not in', ['cancel', 'refuse']),
            ]
            nholidays = self.search_count(domain)
            if nholidays:
                raise ValidationError(_('No puedes tener 2 ausencias que se superpongan en el mismo día!'))

    def _default_get_request_parameters(self, values):
        new_values = dict(values)
        if values.get('date_from'):
            new_values['request_date_from'] = values['date_from']
        if values.get('date_to'):
            new_values['request_date_to'] = values['date_to']
        return new_values

    @api.model
    def default_get(self, fields_list):
        defaults = super(Leave, self).default_get(fields_list)
        defaults = self._default_get_request_parameters(defaults)

        LeaveType = self.env['hr.leave.type'].with_context(employee_id=defaults.get('employee_id'),
                                                           default_date_from=defaults.get('date_from',
                                                                                          fields.Date.today()))
        lt = LeaveType.search([('valid', '=', True)])

        defaults['holiday_status_id'] = lt[0].id if len(lt) > 0 else defaults.get('holiday_status_id')
        return defaults

    def _get_number_of_days(self, date_from, date_to, employee_id=None):
        """
        MM: Cambiamos para qué genere días por fechas, y no por horas
        :param date_from:
        :param date_to:
        :param employee_id:
        :return:
        """
        return int((date_to - date_from).days) + 1

    @api.multi
    def action_refuse(self):
        """
        MM: Negamos la ausencia
        """
        return self.write({'state': 'refuse'})

    @api.constrains('state', 'number_of_days', 'holiday_status_id')
    def _check_holidays(self):
        """
        MM: TODO: Revisar qué hace este método
        """
        return True

    @api.multi
    def action_approve(self):
        """
        MM: Aprobamos al ausencia
        """
        return self.write({
            'approval_user': self.env.user.id,
            'state': 'validate1'
        })

    @api.multi
    def action_validate(self):
        """
        MM: Validamos la ausencia
        """
        return self.write({'state': 'validate'})

    @api.onchange('holiday_status_id')
    def _onchange_holiday_status_id(self):
        """
        Actualizamos la descripción de la ausencia
        :return:
        """
        self.name = self.holiday_status_id.description

    @api.multi
    def action_confirm(self):
        """
        MM: Solicitamos la aprobación
        """
        return self.write({
            'state': 'confirm'
        })

    @api.constrains('number_of_days')
    def _check_number_of_days(self):
        """
        Validamos qué vacaciones solicitadas no sean mayores a las por gozar
        :return:
        """
        if self.holiday_status_id.time_type == 'vacation' and self.holiday_type == 'employee':
            total = 0
            for line in self.vacation_line:
                total += line.vacations_available
            if self.number_of_days_display > total:
                raise ValidationError(
                    _("Duración de vacaciones a gozar mayores a las totales por gozar (%s).") % int(total))

    @staticmethod
    def _get_holiday_lines(employee):
        """
        Obtenemos las líneas de vacaciones por período y empleado
        :return: list
        """
        lines = []
        if not employee:
            return lines
        today = datetime.today().date()
        days = 0
        admission_date = employee.admission_date
        years = today.year - admission_date.year
        if years == 0:
            days = int(float((datetime.combine(today, datetime.min.time()) - datetime.combine(admission_date,
                                                                                              datetime.min.time())).days) / float(
                24))
            data = {
                'employee_id': employee.id,
                'name': str(admission_date.year) + "-" + str(today.year),
                'vacations_generated': days,
                'vacations_taken': 0,
                'vacations_available': 0,
            }
            lines.append(data)
        if years >= 1:
            if years == 1:
                if today < admission_date.replace(year=today.year):
                    days = int(float((datetime.combine(today, datetime.min.time()) - datetime.combine(
                        admission_date, datetime.min.time())).days) / float(24))
                    data = {
                        'employee_id': employee.id,
                        'name': str(admission_date.year) + "-" + str(today.year),
                        'vacations_generated': days,
                        'vacations_taken': 0,
                        'vacations_available': 0,
                    }
                    lines.append(data)
                else:
                    days = 15
                    data = {
                        'employee_id': employee.id,
                        'name': str(admission_date.year) + "-" + str(today.year),
                        'vacations_generated': days,
                        'vacations_taken': 0,
                        'vacations_available': 0,
                    }
                    lines.append(data)

                    days = int(float((datetime.combine(today, datetime.min.time()) - datetime.combine(
                        admission_date.replace(year=today.year), datetime.min.time())).days) / float(24))
                    data = {'employee_id': employee.id,
                            'name': str(today.year) + "-" + str(today.year + 1),
                            'vacations_generated': days,
                            'vacations_taken': 0,
                            'vacations_available': 0, }
                    lines.append(data)
            if years > 1:
                for x in range(1, years):
                    days = 15
                    data = {'employee_id': employee.id,
                            'name': str(admission_date.year) + "-" + str(admission_date.year + x),
                            'vacations_generated': days,
                            'vacations_taken': 0,
                            'vacations_available': 0, }
                    lines.append(data)
                if today < admission_date.replace(year=today.year):
                    days = int(float((datetime.combine(today, datetime.min.time()) - datetime.combine(
                        admission_date.replace(year=today.year - 1), datetime.min.time())).days) / float(24))
                    data = {'employee_id': employee.id,
                            'name': str(admission_date.year + 1) + "-" + str(today.year),
                            'vacations_generated': days,
                            'vacations_taken': 0,
                            'vacations_available': 0, }
                    lines.append(data)
                else:
                    days = 15
                    data = {'employee_id': employee.id,
                            'name': str(admission_date.year + 1) + "-" + str(today.year),
                            'vacations_generated': days,
                            'vacations_taken': 0,
                            'vacations_available': 0, }
                    lines.append(data)
                    days = int(float((datetime.combine(today, datetime.min.time()) - datetime.combine(
                        admission_date.replace(year=today.year), datetime.min.time())).days) / float(24))
                    data = {'employee_id': employee.id,
                            'name': str(today.year) + "-" + str(today.year + 1),
                            'vacations_generated': days,
                            'vacations_taken': 0,
                            'vacations_available': 0, }
                    lines.append(data)
        return lines

    @api.onchange('employee_id', 'holiday_status_id')
    def _onchange_employee_id(self):
        """
        Generamos las vacaciones de empleado si el tipo de ausencia
        es clase 'vacaciones' y asignar departamento si tiene
        :return:
        """
        self.department_id = self.employee_id.department_id
        if self.holiday_status_id.time_type == 'vacation' and self.holiday_type == 'employee':
            employee = self.employee_id
            vacation_line = self.vacation_line.browse([])
            data = self._get_holiday_lines(employee)
            for line in data:  # Añadimos líneas de vacaciones a objeto
                vacation_line += vacation_line.new(line)
            self.vacation_line = vacation_line
            vacations_taken = self.employee_id.days_taken  # Las vacaciones tomados por empleado hasta la fecha
            # Hacemos la disminución con los días de vacaciones tomados
            for line in self.vacation_line:
                if vacations_taken != 0:
                    if vacations_taken == line.vacations_generated:
                        line.update({
                            'vacations_taken': vacations_taken,
                            'vacations_available': 0
                        })
                        vacations_taken = 0
                        continue
                    if vacations_taken - line.vacations_generated > 0:
                        line.update({
                            'vacations_taken': line.vacations_generated,
                            'vacations_available': 0
                        })
                        vacations_taken = vacations_taken - line.vacations_generated
                        continue
                    if vacations_taken - line.vacations_generated < 0:
                        line.update({
                            'vacations_taken': vacations_taken,
                            'vacations_available': abs(vacations_taken - line.vacations_generated)
                        })
                        vacations_taken = 0
                        continue
                if vacations_taken == 0:
                    line.update({
                        'vacations_taken': 0,
                        'vacations_available': line.vacations_generated
                    })
            if vacations_taken != 0:
                self.vacation_line[-1].update(
                    {'vacations_available': self.vacation_line[-1].vacations_available - vacations_taken})
        return

    @api.model
    def _get_vacations(self):
        """
        MR: Obtenemos las vacaciones menos los días de la solicitud
        """
        data = []
        days = int(self.number_of_days)
        for line in self.vacation_line:
            if line.vacations_available <= days:
                data.append({
                    'period': line.period,
                    'vacations_available': line.vacations_available,
                    'requested': line.vacations_available,
                    'residue': 0
                })
                days = days - line.vacations_available
            else:
                data.append({
                    'period': line.name,
                    'vacations_available': line.vacations_available,
                    'requested': days,
                    'residue': int(line.vacations_available - days)
                })
                days = 0
        return data

    @api.multi
    def print_request(self):
        """
        Imprimimos solicitud de vacaciones
        :return:
        """
        self.ensure_one()
        return self.env.ref('eliterp_hr_holidays.action_report_request_vacations').report_action(self)

    @api.onchange('holiday_type')
    def _onchange_type(self):
        """
        MM: TODO: Revisar método
        :return:
        """
        if self.holiday_type == 'employee' and not self.employee_id:
            self.employee_id = False
            self.mode_company_id = False
            self.category_id = False
        elif self.holiday_type == 'company' and not self.mode_company_id:
            self.employee_id = False
            self.mode_company_id = self.company_id.id
            self.category_id = False
        elif self.holiday_type == 'department' and not self.department_id:
            self.employee_id = False
            self.mode_company_id = False
            self.department_id = False
            self.category_id = False
        elif self.holiday_type == 'category':
            self.employee_id = False
            self.mode_company_id = False
            self.department_id = False

    # _check_approval_update

    employee_id = fields.Many2one(
        'hr.employee', string='Empleado', index=True, readonly=True,
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, default=None,
        track_visibility='onchange')  # CM
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Por aprobar'),
        ('refuse', 'Negado'),
        ('validate1', 'Aprobado'),
        ('validate', 'Validado'),
        ('cancel', 'Anulado'),
    ], string='Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
        help="The status is set to 'To Submit', when a holiday request is created." +
             "\nThe status is 'To Approve', when holiday request is confirmed by user." +
             "\nThe status is 'Refused', when holiday request is refused by manager." +
             "\nThe status is 'Approved', when holiday request is approved by manager.")  # CM: TODO: Revisar el parámetro help
    vacation_line = fields.One2many('hr.vacation.line', 'holiday_id', string='Vacaciones', copy=False)
    approval_user = fields.Many2one('res.users', 'Aprobado por')
    time_type = fields.Selection([('leave', 'Ausencia'), ('vacation', 'Vacaciones')],
                                 related='holiday_status_id.time_type',
                                 string="Clase de ausencia")
    company_id = fields.Many2one('res.company', string="Compañía", default=lambda self: self.env.user.company_id)
    date_from = fields.Date(
        'Fecha de inicio', readonly=True, index=True, copy=False, required=True,
        default=fields.Date.today(),
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')
    date_to = fields.Date(
        'Fecha finalización', readonly=True, copy=False, required=True,
        default=fields.Date.today(),
        states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, track_visibility='onchange')