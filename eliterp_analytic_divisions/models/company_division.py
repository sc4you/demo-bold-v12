# -*- coding: utf-8 -*-


from odoo import api, fields, models, _


class Move(models.Model):
    _inherit = 'account.move.line'

    company_division_id = fields.Many2one('account.company.division', string='División',
                                          related='move_id.company_division_id', store=True)


class Move(models.Model):
    _inherit = 'account.move'

    company_division_id = fields.Many2one('account.company.division', string='División', readonly=True,
                                          states={'draft': [('readonly', False)]}, track_visibility='onchange')


class CompanyDivision(models.Model):
    _name = 'account.company.division'
    _description = _('División empresarial')
    _inherit = ['mail.thread']

    @api.multi
    def toggle_active(self):
        for record in self:
            record.active = not record.active

    @api.multi
    def name_get(self):
        res = []
        for data in self:
            res.append((data.id, "[{0}] {1}".format(data.code, data.name)))
        return res

    name = fields.Char('Nombre', index=True, required=True)
    code = fields.Char(required=True, string="Código")
    active = fields.Boolean(default=True, string='Activo?')
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('code_uniq', 'unique (code, company_id)', _('El código debe ser único por compañía!'))
    ]


class Invoice(models.Model):
    _inherit = 'account.invoice'

    @api.model
    def _default_company_division(self):
        company = self.env.user.company_id.id
        company_division_ids = self.env['account.company.division'].search([('company_id', '=', company)], limit=1)
        return company_division_ids

    @api.onchange('company_division_id')
    def _onchange_company_division_id(self):
        if not self.project_id:
            project_ids = self.company_division_id.project_ids
            self.project_id = project_ids and project_ids[0].id or False

    company_division_id = fields.Many2one('account.company.division', string='División', readonly=True,
                                          states={'draft': [('readonly', False)]}, track_visibility='onchange',
                                          default=_default_company_division)
