# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class WarehouseOrderPoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    @api.model
    def _send_email_orderpoint(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_url = "{0}/web?#id={1}&view_type=form&model={2}".format(
            base_url,
            self.id,
            'stock.warehouse.orderpoint'
        )

        template = self.env.ref('eliterp_stock.template_mail_warehouse_orderpoint')
        rendering_context = dict(self._context)
        rendering_context.update({
            'action_url': action_url
        })
        template.with_context(rendering_context).send_mail(self.id)


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def _procurement_from_orderpoint_post_process(self, orderpoint_ids):
        """
        ME: Se envia correo de notificacion de Regla de abastecimiento.
        Solo para bodegas fisicas creamos correo.
        :param orderpoint_ids:
        :return:
        """
        result = super(ProcurementGroup, self)._procurement_from_orderpoint_post_process(orderpoint_ids)
        for op in self.env['stock.warehouse.orderpoint'].browse(orderpoint_ids):
            if op.location_id.usage == 'internal':
                _logger.info("Enviando correo de Regla de abastecimiento %s:" % op.name)
                op._send_email_orderpoint()
        return result
