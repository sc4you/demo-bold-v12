# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import ValidationError
from dateutil import relativedelta
import math

DAYS_IN_YEAR = 360
DAYS_IN_MONTH = 30

class Employee(models.Model):
    _inherit = 'hr.employee'

    def _create_partner(self, vals):
        object_partner = self.env['res.partner']
        partner = object_partner.create({
            'name': vals['name'],
            'is_company': False,
            'company_type': 'person',
            'image': vals.get('image'),
            'customer': True,
            'supplier': False,
            'email': vals.get('work_email') or '-',
            'street': vals.get('emergency_contact') or '-',
            'phone': vals.get('emergency_phone') or '-',
            'type_documentation': '1',
            'documentation_number': vals.get('identification_id')
        })
        return partner

    @api.model
    def create(self, vals):
        if not vals.get('address_home_id') and 'create_partner' in vals and vals.get('create_partner'):
            vals['address_home_id'] = self._create_partner(vals).id
        self.clear_caches()
        return super(Employee, self).create(vals)

    @api.constrains('identification_id', 'address_home_id')
    def _check_identification(self):
        """
        Verificamos qué empeado tenga mismo documento qué empleado
        :return:
        """
        if self.filtered(
                lambda e: e.address_home_id and e.address_home_id.documentation_number[:10] != e.identification_id):
            raise ValidationError(_('Empresa relacionada debe tener misma identificación qué empleado.'))


    def _get_format(self, days):
        year = days / DAYS_IN_YEAR
        month = (days % DAYS_IN_YEAR) / DAYS_IN_MONTH
        day = (days % DAYS_IN_YEAR) % DAYS_IN_MONTH
        return math.floor(year), math.floor(month), day

    @api.depends('admission_date', 'previous_period_days', 'previous_period_months', 'previous_period_years')
    def _compute_service(self):
        date_to = datetime.today().date()
        for record in self:
            result = relativedelta.relativedelta(date_to, record.admission_date)
            years = result.years + record.previous_period_years
            months = result.months + record.previous_period_months
            days = result.days + record.previous_period_days
            result_year, result_month, result_day = self._get_format(days + (months * DAYS_IN_MONTH) + (years * DAYS_IN_YEAR))
            record.days_service = result_day
            record.months_service = result_month
            record.years_service = result_year

    accumulate_tenths = fields.Selection([('yes', 'Si'), ('no', 'No')], string='Acumula décimos?', default='yes')
    accumulate_reserve_funds = fields.Selection([('yes', 'Si'), ('no', 'No')], string='Acumula fondos de reserva?',
                                                default='yes')
    previous_period_days = fields.Integer('Días períodos anteriores', default=0,
                                          help="Empleado arrastra días de otros períodos anteriores (Cálculo de fondos de reserva).")
    previous_period_months = fields.Integer('Meses períodos anteriores', default=0,
                                            help="Empleado arrastra meses de otros períodos anteriores (Cálculo de fondos de reserva).")
    previous_period_years = fields.Integer('Años períodos anteriores', default=0,
                                           help="Empleado arrastra años de otros períodos anteriores (Cálculo de fondos de reserva).")
    days_service = fields.Integer('Días de servicio', compute='_compute_service', store=True)
    months_service = fields.Integer('Meses de servicio', compute='_compute_service', store=True)
    years_service = fields.Integer('Años de servicio', compute='_compute_service', store=True)
    create_partner = fields.Boolean('Crear empresa',
                                    help="Técnico: Si se marca se creará una empresa de este empleado.", default=True)
