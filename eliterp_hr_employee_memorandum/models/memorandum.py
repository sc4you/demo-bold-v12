# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from datetime import datetime, time
from odoo.exceptions import UserError

STATES = [
    ('draft', 'Borrador'),
    ('validate', 'Validado'),
    ('cancel', 'Anulado')
]


class AppearanceMemorandum(models.Model):
    _name = 'hr.appearance.memorandum'
    _description = _('Aspecto de memorandum')

    @api.model
    def create(self, vals):
        context = dict(self._context or {})
        if 'default_document_select' in context:
            if not context['default_document_select']:
                raise UserError(_("No puede crear una aspecto sin escoger un documento!"))
        return super(AppearanceMemorandum, self).create(vals)

    name = fields.Char('Nombre de aspecto', index=True, required=True)
    document_select = fields.Selection([
        ('cal_attention', 'Llamado de atención'),
        ('reglament', 'Reglamento'),
        ('code_work', 'Código de Trabajo')
    ], 'Documento', required=True)


class ClassTypeMemorandum(models.Model):
    _name = 'hr.class.type.memorandum'
    _description = _('Clase de tipo de memorandum')

    name = fields.Char('Nombre', idnex=True, required=True)


class TypeMemorandum(models.Model):
    _name = 'hr.type.memorandum'
    _rec_name = 'class_id'
    _description = _('Tipo de memorandum')

    @api.multi
    def name_get(self):
        result = []
        for data in self:
            result.append((data.id, "%s - %s " % (data.class_id.name, data.provision)))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            domain = ['|', ('class_id', operator, name), ('provision', operator, name)]
        args = args or []
        result = self.search(domain + args, limit=limit)
        return result.name_get()

    appearance_id = fields.Many2one('hr.appearance.memorandum', 'Aspecto', required=True)
    class_id = fields.Many2one('hr.class.type.memorandum', 'Clase', required=True)
    article = fields.Char('Artículo', required=True)
    numeral = fields.Char('Numeral', required=True)
    provision = fields.Text('Disposición', required=True)
    document_select = fields.Selection([
        ('cal_attention', 'Llamado de atención'),
        ('reglament', 'Reglamento'),
        ('code_work', 'Código de Trabajo')
    ], 'Documento', default='reglament', required=True)

    _sql_constraints = [
        ('article_unique', 'unique (article,numeral)', _("El artículo y código deben ser únicos!"))
    ]


class EmployeeMemorandum(models.Model):
    _name = 'hr.employee.memorandum'
    _inherit = ['mail.thread']
    _description = _('Memorándum de empleado')
    _order = 'date desc'

    @api.multi
    def unlink(self):
        if self.filtered(lambda x: x.state != 'draft'):
            raise UserError("No se puede eliminar memorandums diferente a estado borrador!")
        return super(EmployeeMemorandum, self).unlink()

    @api.multi
    def action_validate(self):
        self.ensure_one()
        new_name = self.env['ir.sequence'].next_by_code('employee.memorandum')
        return self.write({'state': 'validate', 'name': new_name or '/'})

    @api.multi
    def action_print(self):
        pass
        # TODO: Falta impresión de reporte
        # return self.env.ref('eliterp_hr_employee_memorandum.action_report_memorandum').report_action(self)

    name = fields.Char('No. Documento', index=True, copy=False)
    date = fields.Date('Fecha documento', default=fields.Date.context_today, required=True, readonly=True,
                       states={'draft': [('readonly', False)]}, track_visibility='onchange')
    sanction = fields.Boolean('Sanción?', default=False, readonly=True,
                              states={'draft': [('readonly', False)]})
    comment_sanction = fields.Text('Comentario de sanción', readonly=True,
                                   states={'draft': [('readonly', False)]})
    employee_id = fields.Many2one('hr.employee', string='Empleado', readonly=True,
                                  required=True,
                                  states={'draft': [('readonly', False)]}, track_visibility='onchange')
    document_select = fields.Selection([
        ('cal_attention', 'Llamado de atención'),
        ('reglament', 'Reglamento'),
        ('code_work', 'Código de Trabajo')
    ], 'Documento', default='cal_attention', required=True, readonly=True,
        states={'draft': [('readonly', False)]})
    appearance_id = fields.Many2one('hr.appearance.memorandum', 'Aspecto', readonly=True,
                                    states={'draft': [('readonly', False)]})
    type_id = fields.Many2one('hr.type.memorandum', 'Tipo', readonly=True,
                              states={'draft': [('readonly', False)]})
    state = fields.Selection(STATES, string='Estado', default='draft', track_visibility='onchange')
    comment = fields.Text('Notas y comentarios', readonly=True,
                          states={'draft': [('readonly', False)]})
    signature_user = fields.Many2one('hr.employee', string='Firma', readonly=True,
                                     states={'draft': [('readonly', False)]})
    file = fields.Binary('Documento', attachment=True)
    file_name = fields.Char('Nombre de documento')


class Employee(models.Model):
    _inherit = 'hr.employee'

    @api.depends('memorandum_ids')
    def _get_memorandum_count(self):
        for record in self:
            memorandum_ids = record.memorandum_ids.filtered(lambda m: m.state != 'draft')
            record.memorandum_count = len((set(memorandum_ids.ids)))

    memorandum_count = fields.Integer(string='# Memorándums', compute='_get_memorandum_count', readonly=True)
    memorandum_ids = fields.One2many('hr.employee.memorandum', 'employee_id', string='Memorándums')
