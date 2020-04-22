odoo.define('eliterp_point_of_sale.pos_model', function(require) {
"use strict";

    var PosDB = require('point_of_sale.DB');
    var POSModels = require('point_of_sale.models');

    var core = require('web.core')

    var _t = core._t;

    PosDB.include({

        // Búsqueda por No. Identificación en clientes
        _partner_search_string: function(partner){
            var str =  partner.name;
            if(partner.address){
                str += '|' + partner.address;
            }
            if(partner.phone){
                str += '|' + partner.phone.split(' ').join('');
            }
            if(partner.mobile){
                str += '|' + partner.mobile.split(' ').join('');
            }
            if(partner.email){
                str += '|' + partner.email;
            }
            // My fields
            if(partner.documentation_number){
                str += '|' + partner.documentation_number;
            }
            str = '' + partner.id + ':' + str.replace(':','') + '\n';
            return str;
        }

    });

    var pmodels = POSModels.PosModel.prototype.models;
    // Agregar nuevos campos a modelos
    for (var i=0; i<pmodels.length; i++){
        var model = pmodels[i];
        if (model.model === 'res.partner') {
            model.fields.push(
            'type_documentation', 'documentation_number', 'comment',
            'canton_id', 'property_stock_carrier'
            );
        }
    }

    var _super_order = POSModels.Order.prototype;

    // Nuevas funciones
    POSModels.Order = POSModels.Order.extend({
        // ME: Aumentamos el subtotal del pedido
        export_as_JSON: function(){
            var json = _super_order.export_as_JSON.apply(this,arguments);
            json.amount_untaxed = this.get_total_without_tax()
            return json;
        }
    });

    // Nuevos modelos en POS GUI
    POSModels.load_models([
        {
            model: 'res.country.state',
            fields: ['name'],
            domain: function(self) {return [['country_id.code', '=', 'EC'|| false]]},
            loaded: function(self, states){
                self.states = states;
            },
        },
        {
            model: 'res.canton',
            fields: ['name', 'state_id'],
            loaded: function(self, cantons){
                self.cantons = cantons;
            },
         }
	]);

});

