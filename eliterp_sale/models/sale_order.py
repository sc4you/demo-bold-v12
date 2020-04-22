# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons import decimal_precision as dp


class OrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id', 'price_unit', 'product_uom', 'product_uom_qty', 'tax_id', 'pricelist_id')
    def _onchange_discount(self):
        if not (self.product_id and self.product_uom and
                self.order_id.partner_id and self.pricelist_id and
                self.pricelist_id.discount_policy == 'without_discount' and
                self.env.user.has_group('sale.group_discount_per_so_line')):
            return

        self.discount = 0.0
        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
            quantity=self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.pricelist_id.id,
            uom=self.product_uom.id,
            fiscal_position=self.env.context.get('fiscal_position')
        )

        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order,
                               uom=self.product_uom.id)

        price, rule_id = self.pricelist_id.with_context(product_context).get_product_price_rule(
            self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id)
        new_list_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id,
                                                                                               self.product_uom_qty,
                                                                                               self.product_uom,
                                                                                               self.pricelist_id.id)

        if new_list_price != 0:
            if self.pricelist_id.currency_id != currency:
                # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                new_list_price = currency._convert(
                    new_list_price, self.pricelist_id.currency_id,
                    self.order_id.company_id, self.order_id.date_order or fields.Date.today())
            discount = (new_list_price - price) / new_list_price * 100
            if discount > 0:
                self.discount = discount

    @api.multi
    def _get_display_price(self, product):
        # TO DO: move me in master/saas-16 on sale.order
        # awa: don't know if it's still the case since we need the "product_no_variant_attribute_value_ids" field now
        # to be able to compute the full price
        if self.product_no_variant_attribute_value_ids:
            product = product.with_context(no_variant_attributes_price_extra=[
                no_variant_attribute_value.price_extra or 0
                for no_variant_attribute_value in self.product_no_variant_attribute_value_ids
            ])

        if self.pricelist_id.discount_policy == 'with_discount':
            return product.with_context(pricelist=self.pricelist_id.id).price
        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order,
                               uom=self.product_uom.id)

        final_price, rule_id = self.pricelist_id.with_context(product_context).get_product_price_rule(
            self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id,
                                                                                           self.product_uom_qty,
                                                                                           self.product_uom,
                                                                                           self.pricelist_id.id)
        if currency != self.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, self.pricelist_id.currency_id,
                self.order_id.company_id, self.order_id.date_order or fields.Date.today())
        # negative discounts (= surcharge) are included in the display price
        return max(base_price, final_price)

    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return {'domain': {'product_uom': []}}

        vals = {}
        domain = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['product_uom_qty'] = self.product_uom_qty or 1.0

        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
            quantity=vals.get('product_uom_qty') or self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.pricelist_id.id,
            uom=self.product_uom.id
        )

        result = {'domain': domain}

        title = False
        message = False
        warning = {}
        if product.sale_line_warn != 'no-message':
            title = _("Warning for %s") % product.name
            message = product.sale_line_warn_msg
            warning['title'] = title
            warning['message'] = message
            result = {'warning': warning}
            if product.sale_line_warn == 'block':
                self.product_id = False
                return result

        name = self.get_sale_order_line_multiline_description_sale(product)

        if self.product_custom_attribute_value_ids or self.product_no_variant_attribute_value_ids:
            name += '\n'

        if self.product_custom_attribute_value_ids:
            for product_custom_attribute_value in self.product_custom_attribute_value_ids:
                if product_custom_attribute_value.custom_value and product_custom_attribute_value.custom_value.strip():
                    name += '\n' + product_custom_attribute_value.attribute_value_id.name + ': ' + product_custom_attribute_value.custom_value.strip()

        if self.product_no_variant_attribute_value_ids:
            for no_variant_attribute_value in self.product_no_variant_attribute_value_ids.filtered(
                    lambda product_attribute_value: not product_attribute_value.is_custom
            ):
                name += '\n' + no_variant_attribute_value.attribute_id.name + ': ' + no_variant_attribute_value.name

        vals.update(name=name)

        self._compute_tax_id()

        if self.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                self._get_display_price(product), product.taxes_id, self.tax_id, self.company_id)
        self.update(vals)

        return result

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        if not self.product_uom or not self.product_id:
            self.price_unit = 0.0
            return
        if self.pricelist_id and self.order_id.partner_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id.id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.pricelist_id.id,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get('fiscal_position')
            )
            self.price_unit = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product),
                                                                                      product.taxes_id, self.tax_id,
                                                                                      self.company_id)

    pricelist_id = fields.Many2one('product.pricelist', string='Lista de precios')


class Order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        if self.filtered(lambda x: not x.order_line):
            raise UserError(_("No puede confirmar venta sin líneas de productos!"))
        return super(Order, self).action_confirm()

    def _validate_name(self, company_id):
        company = self.env['res.company'].browse(company_id)
        sequence = self.env['ir.sequence'].search([('code', '=', 'sale.order'), ('company_id', '=', company_id)])
        if not sequence:
            raise UserError(
                _("No está definida la secuencia con código 'sale.order' para compañía: %s") % company.name)
        return

    @api.multi
    def _prepare_invoice(self):
        """
        ME: Extendemos el método par añadir el punto de impresión
        :return:
        """
        self.ensure_one()
        invoice_vals = super(Order, self)._prepare_invoice()
        invoice_vals['point_printing_id'] = self.point_printing_id.id
        invoice_vals['authorized_voucher_id'] = self.env['sri.authorized.vouchers'].search([('code', '=', '18')])[0].id
        return invoice_vals

    @api.model
    def _get_date_format(self):
        return self.env['res.function']._get_amount_letters(self.amount_total).upper()

    @api.model
    def _default_point_printing(self):
        """
        Defecto de punto de impresión
        :return:
        """
        if self.env.user.my_point_printing:
            return self.env.user.my_point_printing

    @api.model
    def create(self, vals):
        """
        ME: Le colamos el nombre con la secuencia de la empresa
        :param vals:
        :return:
        """
        self._validate_name(vals['company_id'])
        return super(Order, self).create(vals)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """
        ME: Aumentamos descuento (%) de cliente
        :return:
        """
        super(Order, self).onchange_partner_id()
        self.discount = self.partner_id.default_discount or 0.00

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        MM: Aumentamos campos
        :return:
        """
        for order in self:
            amount_untaxed = amount_discount = amount_base_taxed = amount_zero_iva = amount_tax = 0.0
            for line in order.order_line:
                if line.price_tax > 0:
                    amount_base_taxed += line.price_subtotal
                else:
                    amount_zero_iva += line.price_subtotal
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                amount_discount += line.price_unit * line.product_uom_qty * (line.discount / 100)
            order.update({
                'amount_without_discount': amount_untaxed + amount_discount,
                'base_zero_iva': order.pricelist_id.currency_id.round(amount_zero_iva),
                'base_taxed': order.pricelist_id.currency_id.round(amount_base_taxed),
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_discount': order.pricelist_id.currency_id.round(amount_discount),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    point_printing_id = fields.Many2one('sri.point.printing', string='Punto de impresión',
                                        default=_default_point_printing, copy=False)
    discount = fields.Float('Descuento (%)', digits=dp.get_precision('Discount'))
    product_photo = fields.Boolean('Imagen de productos', default=False,
                                   help="Permite imprimir columna con la imagen del producto en líneas de Nota de "
                                        "pedido.")
    amount_without_discount = fields.Monetary('Subtotal sin descuento', compute='_amount_all', store=True)
    amount_discount = fields.Monetary('(-) Total descuento', compute='_amount_all', store=True)
    base_zero_iva = fields.Monetary('Subtotal cero IVA', compute='_amount_all', store=True)
    base_taxed = fields.Monetary('Subtotal IVA', compute='_amount_all', store=True)
