// src/controllers/transactionController.ts
import { Request, Response } from "express";
import { Transaction } from "../models/Transactions";
import { Customer } from "../models/Customer";
import { LineItem } from "../models/LineItem";
import { Payment } from "../models/payments";
import { Branch } from "../models/Branch";
import { generatePaymentId } from "../utils/generatePaymentId";
import mongoose from "mongoose";
import { safeEmit } from "../utils/socketEmitter";

// use centralized generatePaymentId

export const getTransactionById = async (req: Request, res: Response) => {
  try {
    const { transaction_id } = req.params;

    if (!transaction_id) {
      return res.status(400).json({ error: "transaction_id required" });
    }

    // Find transaction by transaction_id only
    const transaction = await Transaction.findOne({ transaction_id });
    if (!transaction) {
      return res.status(404).json({ error: "Transaction not found" });
    }

    // Find customer
    const customer = await Customer.findOne({ cust_id: transaction.cust_id });

    // Find line items
    const lineItems = await LineItem.find({ transaction_id });

    return res.status(200).json({ transaction, customer, lineItems });
  } catch (err) {
    console.error("Error fetching transaction by ID:", err);
    let message = "Unknown error";
    if (err instanceof Error) message = err.message;
    return res.status(500).json({ error: "Server error", message });
  }
};

// Apply a payment to a transaction. If markPickedUp is true, also mark the specified line item as Picked Up
// Request body expected: { dueNow: number, customerPaid: number, modeOfPayment?: string, lineItemId?: string, markPickedUp?: boolean }
export const applyPayment = async (req: Request, res: Response) => {
  const session = await mongoose.startSession();
  session.startTransaction();
  try {
    const { transaction_id } = req.params;
    const { dueNow, customerPaid, modeOfPayment, lineItemId, markPickedUp, payment_status, provided_payment_id } = req.body as {
        dueNow: number;
        customerPaid: number;
        modeOfPayment?: string;
        lineItemId?: string;
        markPickedUp?: boolean;
        payment_status?: string;
        provided_payment_id?: string;
      };

    if (!transaction_id) return res.status(400).json({ error: "transaction_id required" });
    if (dueNow == null || customerPaid == null) return res.status(400).json({ error: "dueNow and customerPaid are required" });

    const transaction = await Transaction.findOne({ transaction_id }).session(session);
    if (!transaction) {
      await session.abortTransaction();
      session.endSession();
      return res.status(404).json({ error: "Transaction not found" });
    }

    // 1) Update transaction: no_released, amount_paid, payment_status, payment_mode
    // increment no_released by 1 only when marking picked up
    if (markPickedUp) {
      transaction.no_released = (transaction.no_released || 0) + 1;
    }

  // Add the dueNow to amount_paid, but clamp to total_amount (no overpay recorded on transaction)
  const prevPaid = Number(transaction.amount_paid || 0)
  const dueNum = Number(dueNow || 0)
  const totalAmt = Number(transaction.total_amount || 0)
  const newPaid = prevPaid + dueNum
  transaction.amount_paid = newPaid > totalAmt ? totalAmt : newPaid

    // If frontend provided payment_status, validate and persist it. Do NOT recompute here.
    const VALID = ["NP", "PARTIAL", "PAID"];
    if (payment_status !== undefined) {
      if (!VALID.includes(payment_status)) {
        await session.abortTransaction();
        session.endSession();
        return res.status(400).json({ error: `Invalid payment_status. Must be one of ${VALID.join(", ")}` });
      }
      transaction.payment_status = payment_status as any;
    }

    // Update payment_mode: if provided and different, append separated by comma
    if (modeOfPayment) {
      const existing = (transaction.payment_mode as any) || "";
      if (!existing) (transaction.payment_mode as any) = modeOfPayment;
      else if (!existing.split(",").map((s: string) => s.trim()).includes(modeOfPayment)) {
        (transaction.payment_mode as any) = `${existing},${modeOfPayment}`;
      }
    }

    // Create a Payment document for the applied amount (dueNow) and attach its id
    try {
      if (provided_payment_id) {
        // If frontend pre-created a payment, ensure it exists and attach it to the transaction
        try {
          const existing = await Payment.findOne({ payment_id: provided_payment_id }).session(session);
          if (existing) {
            transaction.payments = Array.isArray(transaction.payments) ? transaction.payments : [];
            if (!transaction.payments.includes(provided_payment_id)) transaction.payments.push(provided_payment_id);
          } else {
            console.debug('Provided payment id not found on server:', provided_payment_id);
          }
        } catch (e) {
          console.debug('Error attaching provided payment id:', e);
        }
      } else {
        if (dueNum && dueNum > 0) {
          // get branch code from Branch model if available
          let branchCode = String(transaction.branch_id || "");
          try {
            const branch = await Branch.findOne({ branch_id: transaction.branch_id }).session(session);
            if (branch && branch.branch_code) branchCode = branch.branch_code;
          } catch (e) {
            // ignore and fallback to branch_id
          }

          const paymentId = await generatePaymentId(branchCode);
          const payment = new Payment({
            payment_id: paymentId,
            transaction_id: transaction.transaction_id,
            payment_amount: dueNum,
            payment_mode: modeOfPayment || "Other",
            payment_date: new Date(),
          });

          await payment.save({ session });

          // attach to transaction.payments array (ensure uniqueness)
          transaction.payments = Array.isArray(transaction.payments) ? transaction.payments : [];
          if (!transaction.payments.includes(paymentId)) transaction.payments.push(paymentId);
        }
      }
    } catch (err) {
      console.error("Failed to create/attach payment record:", err);
      // don't fail the whole operation; but you may choose to abort instead
    }

    // If this action marks a picked-up item and it causes the transaction to have
    // no remaining pairs (i.e., last pair released), set date_out to now.
    if (markPickedUp && (transaction.no_pairs || 0) - (transaction.no_released || 0) <= 0) {
      transaction.date_out = new Date();
    }

    await transaction.save({ session });

    // 2) If marking picked up, update the specific line item current_status
    let updatedLineItemForEmit: any = null;
    if (markPickedUp && lineItemId) {
      const lineItem = await LineItem.findOne({ line_item_id: lineItemId }).session(session);
      if (!lineItem) {
        await session.abortTransaction();
        session.endSession();
        return res.status(404).json({ error: "Line item not found" });
      }
      lineItem.current_status = "Picked Up";
      await lineItem.save({ session });
      updatedLineItemForEmit = lineItem.toObject();

      // 3) Update customer record totals
      const customer = await Customer.findOne({ cust_id: transaction.cust_id }).session(session);
      if (customer) {
        customer.total_services = (customer.total_services || 0) + 1;
        customer.total_expenditure = (customer.total_expenditure || 0) + (transaction.total_amount || 0);
        await customer.save({ session });
      }
    }

    await session.commitTransaction();
    session.endSession();

    // Emit immediate socket update for selected line item (picked up) so UI can remove row without waiting for change stream
    try {
      if (updatedLineItemForEmit) {
        const remaining_balance = Math.max(Number(transaction.total_amount || 0) - Number(transaction.amount_paid || 0), 0);
        safeEmit('lineItemRowUpdate', {
          type: 'lineItemRowUpdate',
          lineItem: updatedLineItemForEmit,
          transaction_id: transaction.transaction_id,
            remaining_balance,
            storage_fee: updatedLineItemForEmit.storage_fee ?? 0,
            isPickedUp: true,
            // Provide a hint this came from payment path
            source: 'applyPayment'
        });
      }
    } catch (emitErr) {
      console.error('Failed to emit lineItemRowUpdate after applyPayment', emitErr);
    }

    return res.status(200).json({ success: true, transaction });
  } catch (err) {
    await session.abortTransaction();
    session.endSession();
    console.error("Error applying payment:", err);
    let message = "Unknown error";
    if (err instanceof Error) message = err.message;
    return res.status(500).json({ error: message });
  }
};

// Update a transaction by ID
export const updateTransaction = async (req: Request, res: Response) => {
  try {
    const { transaction_id } = req.params;
    const updates = req.body;

    if (!transaction_id) {
      return res.status(400).json({ error: "transaction_id required" });
    }

    // Find transaction by transaction_id
    const transaction = await Transaction.findOne({ transaction_id });
    if (!transaction) {
      return res.status(404).json({ error: "Transaction not found" });
    }

    // Fields that should not be directly updated
    const restrictedFields = ['transaction_id', '_id', '__v', 'createdAt', 'updatedAt'];
    
    // Remove restricted fields from updates
    restrictedFields.forEach(field => delete updates[field]);
    
    // Special handling for payment_status to ensure it's valid
    if (updates.payment_status && !['NP', 'PARTIAL', 'PAID'].includes(updates.payment_status)) {
      return res.status(400).json({ error: "Invalid payment_status. Must be NP, PARTIAL, or PAID" });
    }

    // Update the transaction with the filtered updates
    Object.assign(transaction, updates);
    
    // Save the updated transaction
    await transaction.save();

    return res.status(200).json({ success: true, transaction });
  } catch (err) {
    console.error("Error updating transaction:", err);
    let message = "Unknown error";
    if (err instanceof Error) message = err.message;
    return res.status(500).json({ error: "Server error", message });
  }
};

// GET /transactions
export const getAllTransactions = async (_req: Request, res: Response) => {
  try {
    const transactions = await Transaction.find();
    res.status(200).json(transactions);
  } catch (error) {
    console.error("Error fetching all transactions:", error);
    res.status(500).json({ message: "Server error fetching transactions" });
  }
};

// DELETE /transactions/:transaction_id
export const deleteTransaction = async (req: Request, res: Response) => {
  try {
    const { transaction_id } = req.params;

    if (!transaction_id) {
      return res.status(400).json({ error: "transaction_id required" });
    }

    const result = await Transaction.deleteOne({ transaction_id });

    if (result.deletedCount === 0) {
      return res.status(404).json({ error: "Transaction not found" });
    }

    return res.status(200).json({ success: true, message: "Transaction deleted successfully" });
  } catch (err) {
    console.error("Error deleting transaction:", err);
    let message = "Unknown error";
    if (err instanceof Error) message = err.message;
    return res.status(500).json({ error: "Server error", message });
  }
};