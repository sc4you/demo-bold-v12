# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import time, timedelta, datetime


class Order(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def _cron_email_purchase_import(self):
        """
        Envío de correo electrónico a usuario responsable de la
        bodega de recepciones.
        :return:
        """
        # Url para 'id'
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_url = "{0}/web?#id={1}&view_type=form&model={2}".format(
            base_url,
            self.id,
            'purchase.order'
        )

        # Usuario responsable de bodega destino
        user = self.picking_type_id.default_location_dest_id.user_id

        template = self.env.ref('eliterp_purchase.template_mail_purchase_import')
        rendering_context = dict(self._context)
        rendering_context.update({
            'action_url': action_url,
            'email_to': user.login
        })
        template.with_context(rendering_context).send_mail(self.id)

    @api.model
    def run_scheduler_pi(self, d=15):
        """
        Ejecutamos recordatorio de compras tipo importaciones con fecha de recepción
        con 15 días de alarma a través de un correo electrónico a usuario responsable de bodega
        general.
        """
        future = fields.Date.today() + timedelta(days=d)
        datetime_from = datetime.combine(future, time.min)
        datetime_to = datetime.combine(future, time.max)
        purchases = self.search([
            ('type', '=', 'import'),
            ('state', 'in', ['purchase', 'done']),
            ('date_planned', '>=', datetime_from),
            ('date_planned', '<=', datetime_to),
        ])
        # is_shipped = Sin nigún picking validado
        for p in purchases.filtered(lambda x: not x.is_shipped):
            p._cron_email_purchase_import()

    def _get_name(self):
        company = self.env.user.company_id
        sequence = self.env['ir.sequence'].with_context(force_company=company.id).next_by_code('purchase.order')
        if not sequence:
            raise UserError(
                _("No está definida la secuencia con código 'purchase.order' para compañía: %s") % company.name)
        return sequence

    @api.model
    def create(self, vals):
        """
        MM: Le cambiamos qué al crear una orden de compra deba tener su secuencia
        :param vals:
        :return:
        """
        if vals.get('name', 'New') == 'New':
            sequence = self._get_name()
            vals['name'] = sequence
        return super(Order, self).create(vals)

    @api.multi
    def button_confirm(self):
        """
        ME: Añadimos el usuario de confirmación de la orden de compra.
        :return:
        """
        result = super(Order, self).button_confirm()
        for record in self:
            record.write({'approval_user': self._uid})
        return result

    name = fields.Char('Order Reference', required=True, index=True, copy=False, default='Nuevo pedido')  # CM
    type = fields.Selection([('local', 'Local'), ('import', 'Importación')],
                            readonly=True,
                            states={'draft': [('readonly', False)]}, default='local', string="Tipo de compra")
    approval_user = fields.Many2one('res.users', 'Usuario de aprobación', readonly=1, copy=False)
    invoice_status = fields.Selection([
        ('no', 'Pendiente'),
        ('to invoice', 'Para facturar'),
        ('invoiced', 'Facturado'),
    ], string='Estado de facturación', compute='_get_invoiced', store=True, readonly=True, copy=False, default='no',
        track_visibility='onchange')
    state = fields.Selection([
        ('draft', 'SDP Borrador'),
        ('sent', 'SDP Enviada'),
        ('to approve', 'OCS por aprobar'),
        ('purchase', 'OCS Aprobado'),
        ('done', 'Bloqueado'),
        ('cancel', 'Cancelado')
    ], string='Estado', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')


class OrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.onchange('product_id')
    def onchange_product_id(self):
        """
        ME: Colocamos el costo local por defecto.
        Si existe proveedor registrado me trae el precio del mismo.
        :return:
        """
        result = super(OrderLine, self).onchange_product_id()
        if not self.price_unit:
            self.price_unit = self.product_id.standard_price
        return result


class InvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    purchase_line_id = fields.Many2one('purchase.order.line', copy=False)  # CM
