/// src/models/Payments.ts
import mongoose, { Schema, Document } from "mongoose";

export interface IPayment extends Document {
  payment_id: string; // Format: BRANCH-1 (branch code + auto increment)
  transaction_id: string; // FK -> Transaction.transaction_id
  payment_amount: number;
  payment_mode: "Cash" | "GCash" | "Bank" | "Other"; // enforce enums
  payment_date: Date;
}

const PaymentSchema: Schema = new Schema<IPayment>(
  {
    payment_id: {
      type: String,
      required: true,
      unique: true, // BRANCH-1 style
    },
    transaction_id: {
      type: String,
      required: true,
      ref: "Transaction",
    },
    payment_amount: {
      type: Number,
      required: true,
      min: [0.01, "Payment amount must be greater than 0"],
    },
    payment_mode: {
      type: String,
      enum: ["Cash", "GCash", "Bank", "Other"],
      required: true,
    },
    payment_date: {
      type: Date,
      required: true,
      default: Date.now,
    },
  },
  { timestamps: true }
);

export const Payment = mongoose.model<IPayment>(
  "Payment",
  PaymentSchema,
  "payments"
);
