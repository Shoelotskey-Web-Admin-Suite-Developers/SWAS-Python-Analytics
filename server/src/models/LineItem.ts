// src/models/LineItem.ts
import mongoose, { Schema, Document } from "mongoose";

export interface ILineItemService {
  service_id: string;
  quantity: number; // how many of this service
}

export interface ILineItem extends Document {
  line_item_id: string;
  transaction_id: string;
  priority: "Rush" | "Normal";
  cust_id: string;
  services: ILineItemService[];
  storage_fee: number;
  branch_id: string;
  shoes: string;
  current_location: "Hub" | "Branch";
  current_status: string;
  due_date?: Date | null;
  latest_update: Date;
  before_img?: string | null;
  after_img?: string | null;
  pickUpNotice?: Date | null; // <-- added field
}

const LineItemServiceSchema: Schema = new Schema<ILineItemService>(
  {
    service_id: { type: String, ref: "Service", required: true },
    quantity: { type: Number, default: 1, min: 1 },
  },
  { _id: false } // subdocs don't need their own ids
);

const LineItemSchema: Schema = new Schema<ILineItem>(
  {
    line_item_id: { type: String, required: true, unique: true },
    transaction_id: { type: String, required: true, ref: "Transaction" },
    priority: { type: String, enum: ["Rush", "Normal"], default: "Normal" },
    cust_id: { type: String, required: true, ref: "Customer" },
    services: { type: [LineItemServiceSchema], required: true }, // canonical persisted shape
    storage_fee: { type: Number, default: 0 },
    branch_id: { type: String, required: true },
    shoes: { type: String, required: true },
    current_location: { type: String, enum: ["Hub", "Branch"], required: true },
    current_status: { type: String, required: true },
    due_date: { type: Date, default: null },
    latest_update: { type: Date, default: Date.now },
    before_img: { type: String, default: null },
    after_img: { type: String, default: null },
    pickUpNotice: { type: Date, default: null }, // <-- added field, default null
  },
  {
    toJSON: { virtuals: true },
    toObject: { virtuals: true },
  }
);

export const LineItem = mongoose.model<ILineItem>("LineItem", LineItemSchema, "line_items");
