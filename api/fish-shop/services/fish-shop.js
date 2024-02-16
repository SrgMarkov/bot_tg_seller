'use strict';

/**
 * fish-shop service
 */

const { createCoreService } = require('@strapi/strapi').factories;

module.exports = createCoreService('api::fish-shop.fish-shop');
