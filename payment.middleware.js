import { PAYMENT_ENABLED } from "./payment.config.js";

export function requirePayment(serviceName) {
  return function (req, res, next) {
    if (!PAYMENT_ENABLED) return next();

    if (!req.body.paymentIntentId) {
      return res.status(402).json({
        error: "Payment required before using this service."
      });
    }

    next();
  };
}
