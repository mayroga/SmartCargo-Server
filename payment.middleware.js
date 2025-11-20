// payment.middleware.js
import { PAYMENT_ENABLED, PRICES } from "./payment.config.js";

export function requirePayment(level) {
  return function (req, res, next) {
    if (!PAYMENT_ENABLED) return next(); // Gratis por ahora

    const price = PRICES[level];
    if (!req.body.paymentIntentId || !price) {
      return res.status(402).json({ error: "Payment required for this level." });
    }

    next();
  };
}
