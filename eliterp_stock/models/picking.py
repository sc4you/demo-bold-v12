# -*- coding: utf-8 -*-


from odoo import models, fields, api


class Move(models.Model):
    _inherit = 'stock.move'

    quantity_presentation = fields.Integer('Cantidad por presentación', related='product_id.product_tmpl_id'
                                                                                '.quantity_presentation')
    presentation_id = fields.Many2one('product.presentation', string='Presentación', related='product_id'
                                                                                             '.product_tmpl_id.presentation_id')

    @api.one
    @api.depends('product_id', 'product_uom_qty')
    def _compute_qty_presentation(self):
        if self.product_id:
            qty_presentation = self.product_id._get_qty_presentation(int(self.product_uom_qty))
            self.qty_presentation = qty_presentation

    qty_presentation = fields.Char('DI x P', compute='_compute_qty_presentation')


class Picking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _send_email_location_dest(self):
        """
        Envíamos el correo a la bodega destino
        con el URL del movimiento
        :return:
        """
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_url = "{0}/web?#id={1}&view_type=form&model={2}".format(
            base_url,
            self.id,
            'stock.picking'
        )

        template = self.env.ref('eliterp_stock.template_mail_location_destination')
        rendering_context = dict(self._context)
        rendering_context.update({
            'action_url': action_url
        })
        template.with_context(rendering_context).send_mail(self.id)

    @api.one
    def action_done(self):
        """
        ME: Al aplicar la transferencia enviar correo a usuario
        responsable de la bodega destino.
        :return:
        """
        result = super(Picking, self).action_done()
        if self.picking_type_id.code == 'internal' and self.location_dest_id.usage == 'internal':
            self._send_email_location_dest()
        return result

    @api.onchange('picking_type_id')
    def onchange_picking_type(self):
        """
        ME: Bodega destino no colocamos la por defecto
        Cuando se realiza una recepción (Borrador) traiga la bodega por defecto de destino
        :return:
        """
        res = super(Picking, self).onchange_picking_type()
        if self.state == 'draft' and self.picking_type_id.code == 'internal':
            self.location_dest_id = False
        if self.picking_type_id.code == 'incoming':
            self.location_dest_id = self.picking_type_id.default_location_dest_id.id
        return res

    location_dest_id = fields.Many2one(
        'stock.location', "Bodega destino",
        default=lambda self: self.env['stock.picking.type'].browse(
            self._context.get('default_picking_type_id')).default_location_dest_id, required=True)  # CM

    def _get_reason_incoming(self, flag=False):
        """
        Obtenemos el Motivo del movimiento' del picking
        dependiendo si es salida o retorno.
        :return:
        """
        self.ensure_one()
        if self.picking_type_id.code == 'incoming':
            if not flag:
                reason_incoming = 'purchase'
            else:
                reason_incoming = 'return_sale'
        elif self.picking_type_id.code == 'outgoing':
            if not flag:
                reason_incoming = 'sale'
            else:
                reason_incoming = 'return_purchase'
        else:
            reason_incoming = 'transfer'
        return reason_incoming

    @api.model
    def create(self, vals):
        """
        ME: Aumentamos el campo 'Motivo del movimiento'
        :param vals:
        :return:
        """
        picking = super(Picking, self).create(vals)
        picking.reason_incoming = picking._get_reason_incoming()
        return picking

    reason_incoming = type = fields.Selection([
        ('purchase', 'Compra'),
        ('return_purchase', 'Devolución Compra'),
        ('sale', 'Venta'),
        ('return_sale', 'Devolución Venta'),
        ('gift', 'Regalo'),
        ('transfer', 'Transferencia entre bodegas'),
        ('other', 'Otro'),
    ], string="Motivo del movimiento", default='other', readonly=True, states={'draft': [('readonly', False)]},
        help="Referencia interna para saber motivo de la operación o movimiento.")
    is_return = fields.Boolean('Es devolución', default=False, help="Técnico: Saber si movimiento es devolución.")


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.multi
    def _create_returns(self):
        """
        ME: Aumentamos el 'Motivo del movimiento' y cuando
        sea retorno de productos lo marcamos.
        :return:
        """
        new_picking, pick_type_id = super(ReturnPicking, self)._create_returns()
        picking = self.env['stock.picking'].browse(new_picking)
        reason = picking._get_reason_incoming(True)
        picking.write({
            'is_return': True,
            'reason_incoming': reason
        })
        return new_picking, pick_type_id
