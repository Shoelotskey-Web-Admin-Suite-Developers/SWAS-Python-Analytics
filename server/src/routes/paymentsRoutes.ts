import { Router } from "express";
import { getPaymentById, getLatestPaymentByTransactionId, createPayment } from "../controllers/paymentsController";

const router = Router();

router.get("/:payment_id", getPaymentById);
router.get("/latest/transaction/:transaction_id", getLatestPaymentByTransactionId);
router.post("/", createPayment);

export default router;
