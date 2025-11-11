// src/models/NotifToken.ts
import mongoose, { Schema, Document } from "mongoose";

export interface INotifToken extends Document {
  token: string;       // Expo push token
  cust_id: string;     // Reference to Customer
  created_at: Date;
}

const NotifTokenSchema: Schema = new Schema<INotifToken>(
  {
    token: { type: String, required: true },
    cust_id: { type: String, required: true, ref: "Customer" },
    created_at: { type: Date, default: Date.now },
  }
);

// Prevent duplicate token per customer
NotifTokenSchema.index({ token: 1, cust_id: 1 }, { unique: true });

export const NotifToken = mongoose.model<INotifToken>(
  "NotifToken",
  NotifTokenSchema,
  "notif_tokens" // Explicit collection name
);
