# -*- coding: utf-8 -*-

from odoo import fields, models


class LeaveReport(models.Model):
    _inherit = "hr.leave.report"

    date_from = fields.Date()
    date_to = fields.Date()