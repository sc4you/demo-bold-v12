odoo.define('eliterp_point_of_sale.pos_screen', function(require) {
"use strict";

    var PosBaseWidget = require('point_of_sale.BaseWidget');
    var gui = require('point_of_sale.gui');
    var models = require('point_of_sale.models');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var utils = require('web.utils');
    var field_utils = require('web.field_utils');
    var BarcodeEvents = require('barcodes.BarcodeEvents').BarcodeEvents;

    var QWeb = core.qweb;
    var _t = core._t;

    var screens = require('point_of_sale.screens');

    screens.ClientListScreenWidget.include({

        //  MM: Función para grabar cliente desde el cliente POS.
        // Se agregaron nueva validaciones del formulario.
        save_client_details: function(partner) {
            var self = this;

            var fields = {};
            this.$('.client-details-contents .detail').each(function(idx,el){
                fields[el.name] = el.value || false;
            });

            if (
                !fields.name ||
                !fields.documentation_number ||
                !fields.street ||
                !fields.email ||
                !fields.phone
                ) {
                this.pos.gui.show_popup("error", {
                    'title': _t("Validación de formulario"),
                    'body':  _t(
                        "Campos en formulario marcados con * son obligatorios."
                    ),
                 });
                return;
            }

            if (this.uploaded_picture) {
                fields.image = this.uploaded_picture;
            }

            fields.id           = partner.id || false;
            // fields.country_id   = fields.country_id || false;
            fields.state_id   = fields.state_id || false
            fields.canton_id   = fields.canton_id || false
            fields.property_stock_carrier = fields.property_stock_carrier || false

            if (fields.property_product_pricelist) {
                fields.property_product_pricelist = parseInt(fields.property_product_pricelist, 10);
            } else {
                fields.property_product_pricelist = false;
            }
            var contents = this.$(".client-details-contents");
            contents.off("click", ".button.save");


            rpc.query({
                    model: 'res.partner',
                    method: 'create_from_ui',
                    args: [fields],
                })
                .then(function(partner_id){
                    self.saved_client_details(partner_id);
                },function(err,ev){
                    ev.preventDefault();
                    var error_body = _t('Tu conexión a Internet probablemente está caída.');
                    if (err.data) {
                        var except = err.data;
                        error_body = except.arguments && except.arguments[0] || except.message || error_body;
                    }
                    self.gui.show_popup('error',{
                        'title': _t('Error: No se pueden guardar cambios.'),
                        'body': error_body,
                    });
                    contents.on('click','.button.save',function(){ self.save_client_details(partner); });
                });
            },

    });

    screens.OrderWidget.include({

        // MM: Función para agregar el Subtotal, IVA, Total
        update_summary: function(){
            var order = this.pos.get_order();
            if (!order.get_orderlines().length) {
                return;
            }

            var subtotal  = order ? order.get_total_without_tax() : 0;

            var total     = order ? order.get_total_with_tax() : 0;
            var taxes     = order ? total - order.get_total_without_tax() : 0;

            this.el.querySelector('.summary .total span:nth-of-type(2).value').textContent = this.format_currency(subtotal);
            this.el.querySelector('.summary .total span:nth-of-type(4).value').textContent = this.format_currency(total);
            this.el.querySelector('.summary .total .subentry .value').textContent = this.format_currency(taxes);
        },

    });

    screens.PaymentScreenWidget.include({
        renderElement: function(){
            var self = this;
            this._super();
            /*Siempre marcado para factura*/
            self.click_invoice()
        },
    });
});

