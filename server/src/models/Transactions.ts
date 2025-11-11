/// src/models/Transactions.ts
import mongoose, { Schema, Document } from "mongoose";

export interface ITransaction extends Document {
  transaction_id: string; // LOC-BRNCH-T style
  line_item_id: string[]; // FK -> LineItem
  branch_id: string;
  date_in: Date;
  received_by: string;
  date_out?: Date;
  cust_id: string; // FK -> Customer
  no_pairs: number;
  no_released: number;
  total_amount: number;
  discount_amount: number; // New field
  amount_paid: number;
  payment_status: "NP" | "PAID" | "PARTIAL";
  payments: string[]; // FK -> Payment.payment_id
  payment_mode?: string | string[]; // can be a single mode or comma-separated list
}

const TransactionSchema: Schema = new Schema<ITransaction>(
  {
    transaction_id: { type: String, required: true, unique: true },
    line_item_id: [{ type: String, ref: "LineItem", required: true }],
    branch_id: { type: String, required: true, ref: "Branch" },
    date_in: { type: Date, required: true, default: Date.now },
    received_by: { type: String, required: true, maxlength: 50 },
    date_out: { type: Date, default: null },
    cust_id: { type: String, required: true, ref: "Customer" },
    no_pairs: { type: Number, default: 0 },
    no_released: { type: Number, default: 0 },
    total_amount: { type: Number, default: 0.0 },
    discount_amount: { type: Number, default: 0.0 },
    amount_paid: { type: Number, default: 0.0 },
    payment_status: {
      type: String,
      enum: ["NP", "PARTIAL", "PAID"],
      default: "NP",
      required: true,
    },
    payment_mode: { type: String, default: "" },
    payments: [
      {
        type: String,
        ref: "Payment", // links to Payment.payment_id
      },
    ],
  },
  { timestamps: true }
);

export const Transaction = mongoose.model<ITransaction>(
  "Transaction",
  TransactionSchema,
  "transactions"
);
