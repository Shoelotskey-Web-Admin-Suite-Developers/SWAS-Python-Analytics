// src/models/MonthlyRevenue.ts
import mongoose, { Schema, Document } from "mongoose";

export interface IMonthlyRevenue extends Document {
  month: string; // e.g. "Jan", "Feb", etc.
  Year: number; // e.g. 2025
  total: number;
  [branchCode: string]: any; // Allow dynamic branch fields like "SMVAL-B-NCR"
}

const MonthlyRevenueSchema: Schema = new Schema<IMonthlyRevenue>(
  {
    month: { type: String, required: true },
    Year: { type: Number, required: true },
    total: { type: Number, required: true },
  },
  {
    strict: false, // allow dynamic fields like "SMVAL-B-NCR"
    toJSON: { virtuals: true },
    toObject: { virtuals: true },
  }
);

export const MonthlyRevenue = mongoose.model<IMonthlyRevenue>(
  "MonthlyRevenue",
  MonthlyRevenueSchema,
  "monthly_growth" // collection name
);
