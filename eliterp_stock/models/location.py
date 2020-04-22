# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
import logging

_logger = logging.getLogger('stock.location')


class LocationArea(models.Model):
    _name = "stock.location.area"
    _description = _("Área de bodega")

    name = fields.Char("Referencia de área", index=True, required=True)


class LocationAreaLine(models.Model):
    _name = "stock.location.area.line"
    _description = _("Áreas dentro de bodega")

    name = fields.Many2one('stock.location.area', string="Nombre de área", required=True)
    location_id = fields.Many2one('stock.location', string="Bodega", ondelete="cascade")


class Location(models.Model):
    _inherit = 'stock.location'

    @api.model
    def _cron_email_stock_location(self, products):
        """
        Envío de correo electrónico a usuario responsable de la
        bodega de recepciones.
        :return:
        """
        # Url para 'id'
        # TODO: Mejorar URL para ver el stock de dicha bodega
        # http://localhost:8069/web?debug=true#action=366&active_id=12&model=stock.quant&view_type=list&menu_id=227
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_url = "{0}/web?#id={1}&view_type=form&model={2}".format(
            base_url,
            self.id,
            'stock.location'
        )

        template = self.env.ref('eliterp_stock.template_mail_stock_location')
        rendering_context = dict(self._context)
        rendering_context.update({
            'action_url': action_url,
            'products': products
        })
        template.with_context(rendering_context).send_mail(self.id)

    @api.model
    def run_scheduler(self, minimum_stock=5):
        """
        Ejecutamos un barrido del stock en las diferentes bodegas y generamos informe (excel)
        de productos bajos de stock y lo envíe por correo a responsable de bodega
        para que gestione transferencias internas.
        :param minimum_stock:
        :return:
        """
        # TODO: Revisar si es la mejor opción
        data_products = []
        object_quant = self.sudo().env['stock.quant']
        for location in self.search([('usage', '=', 'internal')]):
            for quant in object_quant.search([('location_id', '=', location.id)]):
                qty_available = quant.quantity - quant.reserved_quantity
                if qty_available < minimum_stock:
                    # Imprimmos por conveniencia
                    _logger.info("B: %s -> %s [%s]" % (location.name, quant.product_id.display_name, qty_available))
                    data_products.append({
                        'name': quant.product_id.display_name,
                        'qty_available': qty_available
                    })
            # Soló si existen datos de productos envíamos correo
            if data_products:
                location._cron_email_stock_location(data_products)

    user_id = fields.Many2one('res.users', 'Responsable', track_visibility='onchange',
                              default=lambda self: self.env.user,
                              help="Usuario responsable de bodega (interna). Sirve para envío de correos y procesos ("
                                   "p.e abastecimiento).")
    code = fields.Char('Código de bodega', size=5)
    area_ids = fields.One2many('stock.location.area.line', 'location_id', string='Áreas')
