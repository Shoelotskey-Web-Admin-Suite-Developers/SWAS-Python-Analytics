// src/routes/transactionRoutes.ts
import { Router } from "express";
import { 
  getTransactionById, 
  applyPayment, 
  getAllTransactions, 
  updateTransaction,
  deleteTransaction // Import the deleteTransaction controller
} from "../controllers/transactionController";

const router = Router();

router.get("/:transaction_id", getTransactionById);
router.post("/:transaction_id/apply-payment", applyPayment);
router.put("/:transaction_id", updateTransaction); // New route for updating transactions
router.delete("/:transaction_id", deleteTransaction); // Add this route
router.get("/", getAllTransactions);

export default router;